"""Background transcription with faster-whisper.

A single TranscriptionWorker lives in its own QThread and handles one file at a
time. It downloads models on first use, picks CPU or GPU, falls back to the CPU
if the GPU doesn't work, and reports progress through Qt signals. It never
touches the database; results are sent back to the UI thread.
"""

import ctypes
import fnmatch
import gc
import logging
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

log = logging.getLogger(__name__)

CPU = ("cpu", "int8")
GPU = ("cuda", "float16")
CPU_THREADS = max(4, (os.cpu_count() or 4) // 2)

# Files faster-whisper needs from the Hugging Face model repo.
MODEL_FILE_PATTERNS = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]
DOWNLOAD_COMPLETE_MARKER = ".download_complete"

# CUDA 12 / cuDNN 9 libraries that CTranslate2 loads at runtime for GPU inference.
CUDA_LIBRARIES = ["cublas64_12.dll", "cublasLt64_12.dll", "cudnn_ops64_9.dll", "cudnn_cnn64_9.dll"]

GPU_FAILED_NOTICE = (
    "The GPU couldn't be used (CUDA libraries may be missing), so transcription "
    "switched to the CPU. It will be slower but still works. See the README to enable GPU."
)


class Cancelled(Exception):
    pass


class FriendlyError(Exception):
    """An error whose message can be shown to the user as-is."""


# ---------------------------------------------------------------------------
# Hardware detection


def cuda_device_count():
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count()
    except Exception:
        log.exception("Could not query CUDA devices")
        return 0


def missing_cuda_libraries():
    """Names of required CUDA DLLs that can't be loaded (empty list = all present)."""
    if sys.platform != "win32":
        return []
    missing = []
    for name in CUDA_LIBRARIES:
        try:
            # winmode=0 uses the standard Windows search order, which includes PATH.
            ctypes.WinDLL(name, winmode=0)
        except OSError:
            missing.append(name)
    return missing


# ---------------------------------------------------------------------------
# Model download


def model_path(models_dir, size):
    return Path(models_dir) / size


def is_model_downloaded(models_dir, size):
    path = model_path(models_dir, size)
    return (path / DOWNLOAD_COMPLETE_MARKER).exists() and (path / "model.bin").exists()


def _folder_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


class _ModelDownload(threading.Thread):
    """Downloads one model size in the background.

    Runs in its own thread so that cancelling a job doesn't have to wait for a
    multi-gigabyte download; the download simply keeps going and the next job
    that needs the same model picks it up.
    """

    def __init__(self, size, path):
        super().__init__(name=f"download-{size}", daemon=True)
        self.size = size
        self.path = path
        self.total_bytes = None
        self.error = None

    def run(self):
        from faster_whisper import download_model

        try:
            self.total_bytes = self._expected_size()
            log.info("Downloading model '%s' (%s bytes) to %s", self.size, self.total_bytes, self.path)
            download_model(self.size, output_dir=str(self.path))
            (self.path / DOWNLOAD_COMPLETE_MARKER).write_text("ok", encoding="utf-8")
            log.info("Model '%s' downloaded", self.size)
        except Exception as exc:
            log.exception("Downloading model '%s' failed", self.size)
            self.error = exc

    def _expected_size(self):
        try:
            from huggingface_hub import HfApi

            info = HfApi().model_info(f"Systran/faster-whisper-{self.size}", files_metadata=True)
            total = sum(
                sibling.size or 0
                for sibling in info.siblings
                if any(fnmatch.fnmatch(sibling.rfilename, pattern) for pattern in MODEL_FILE_PATTERNS)
            )
            return total or None
        except Exception:
            log.warning("Could not look up the size of model '%s'", self.size, exc_info=True)
            return None


_downloads = {}
_downloads_lock = threading.Lock()


def _start_download(size, path):
    with _downloads_lock:
        download = _downloads.get(size)
        if download is None or not download.is_alive():
            download = _ModelDownload(size, path)
            _downloads[size] = download
            download.start()
        return download


# ---------------------------------------------------------------------------
# Helpers


def probe_media(path):
    """Checks the file can be read and has audio. Returns its duration in seconds (0 if unknown)."""
    if not os.path.isfile(path):
        raise FriendlyError("The file no longer exists or can't be accessed.")

    import av

    try:
        with av.open(path, metadata_errors="ignore") as container:
            if not container.streams.audio:
                raise FriendlyError("This file has no audio track, so there is nothing to transcribe.")
            if container.duration:
                return container.duration / av.time_base
            stream = container.streams.audio[0]
            if stream.duration and stream.time_base:
                return float(stream.duration * stream.time_base)
            return 0.0
    except FriendlyError:
        raise
    except Exception as exc:
        log.warning("Could not open %s: %s", path, exc)
        raise FriendlyError("This file couldn't be opened. It may be damaged or in an unsupported format.")


def describe_error(exc):
    message = str(exc).strip()
    if isinstance(exc, MemoryError) or "out of memory" in message.lower() or "bad_alloc" in message:
        return "Ran out of memory. Try a smaller model size in Settings."
    first_line = message.splitlines()[0] if message else type(exc).__name__
    if len(first_line) > 200:
        first_line = first_line[:200] + "…"
    return f"Transcription failed: {first_line}"


# ---------------------------------------------------------------------------
# Worker


class TranscriptionWorker(QObject):
    status = Signal(int, str)  # job id, short status text
    progress = Signal(int, int)  # job id, percent 0-100, or -1 for "busy"
    finished = Signal(int, object)  # job id, result dict
    failed = Signal(int, str)  # job id, readable error message
    cancelled = Signal(int)  # job id
    notice = Signal(str)  # non-blocking message for the user

    def __init__(self, models_dir):
        super().__init__()
        self.models_dir = Path(models_dir)
        # Set from the UI thread to cancel the current job.
        self.cancel_event = threading.Event()
        self._model = None
        self._model_key = None
        self._gpu_failed = False
        self._notices_shown = set()

    @Slot(int, str, object)
    def run_job(self, job_id, path, settings):
        log.info("Job %s: transcribing %s with %s", job_id, path, settings)
        try:
            result = self._transcribe(job_id, path, settings)
        except Cancelled:
            log.info("Job %s: cancelled", job_id)
            self.cancelled.emit(job_id)
        except FriendlyError as exc:
            log.warning("Job %s: %s", job_id, exc)
            self.failed.emit(job_id, str(exc))
        except BaseException as exc:  # noqa: BLE001 - the worker thread must never die
            log.exception("Job %s: transcription failed for %s", job_id, path)
            self.failed.emit(job_id, describe_error(exc))
        else:
            log.info("Job %s: done, %d segments", job_id, len(result["segments"]))
            self.finished.emit(job_id, result)

    def _check_cancel(self):
        if self.cancel_event.is_set():
            raise Cancelled()

    def _notice_once(self, message):
        if message not in self._notices_shown:
            self._notices_shown.add(message)
            self.notice.emit(message)

    def _transcribe(self, job_id, path, settings):
        self.status.emit(job_id, "Checking file…")
        self.progress.emit(job_id, -1)
        duration = probe_media(path)
        self._check_cancel()

        size = settings["model_size"]
        language = None if settings["language"] == "auto" else settings["language"]
        model = self._load_model(job_id, size, *self._choose_device(settings["device"]))

        try:
            return self._run_model(job_id, model, path, language, duration, size)
        except (Cancelled, FriendlyError):
            raise
        except Exception:
            if self._model_key[1] != "cuda":
                raise
            # CUDA problems often only show up once inference starts.
            log.exception("GPU transcription failed; retrying on CPU")
            self._gpu_failed = True
            self._notice_once(GPU_FAILED_NOTICE)
            model = self._load_model(job_id, size, *CPU)
            return self._run_model(job_id, model, path, language, duration, size)

    def _choose_device(self, requested):
        """Returns (device, compute_type) for the requested setting (auto/cpu/gpu)."""
        if requested == "cpu" or self._gpu_failed:
            return CPU
        if cuda_device_count() == 0:
            if requested == "gpu":
                self._notice_once("No NVIDIA GPU with CUDA support was found, so the CPU is being used instead.")
            return CPU
        missing = missing_cuda_libraries()
        if missing:
            log.warning("CUDA GPU found but libraries are missing: %s", ", ".join(missing))
            self._gpu_failed = True
            self._notice_once(
                "An NVIDIA GPU was found, but the CUDA/cuDNN libraries it needs are missing "
                f"({', '.join(missing)}). Using the CPU instead. See the README to enable GPU."
            )
            return CPU
        return GPU

    def _load_model(self, job_id, size, device, compute_type):
        key = (size, device, compute_type)
        if self._model is not None and self._model_key == key:
            return self._model

        path = self._ensure_downloaded(job_id, size)

        self.status.emit(job_id, "Loading model…")
        self.progress.emit(job_id, -1)
        self._model = None
        self._model_key = None
        gc.collect()

        from faster_whisper import WhisperModel

        try:
            model = WhisperModel(str(path), device=device, compute_type=compute_type, cpu_threads=CPU_THREADS)
        except Exception as exc:
            if device == "cuda":
                log.exception("Loading model on GPU failed; falling back to CPU")
                self._gpu_failed = True
                self._notice_once(GPU_FAILED_NOTICE)
                return self._load_model(job_id, size, *CPU)
            log.exception("Loading model '%s' failed", size)
            raise FriendlyError(
                f"The '{size}' model couldn't be loaded ({describe_error(exc)}). If this keeps happening, "
                f"delete the folder {path} so it is downloaded again."
            )

        log.info("Loaded model '%s' on %s (%s)", size, device, compute_type)
        self._model = model
        self._model_key = key
        return model

    def _ensure_downloaded(self, job_id, size):
        path = model_path(self.models_dir, size)
        if is_model_downloaded(self.models_dir, size):
            return path

        path.mkdir(parents=True, exist_ok=True)
        download = _start_download(size, path)
        while download.is_alive():
            self._report_download(job_id, path, download.total_bytes)
            self._check_cancel()  # the download itself keeps going in the background
            download.join(0.5)

        if download.error is not None or not is_model_downloaded(self.models_dir, size):
            raise FriendlyError(
                f"Couldn't download the '{size}' model. Check your internet connection and try again. "
                "An internet connection is only needed the first time each model size is used."
            )
        return path

    def _report_download(self, job_id, path, total_bytes):
        done_mb = _folder_size(path) / 1_000_000
        if total_bytes:
            total_mb = total_bytes / 1_000_000
            self.status.emit(job_id, f"Downloading model… {done_mb:.0f} / {total_mb:.0f} MB")
            self.progress.emit(job_id, min(99, int(done_mb * 100 / total_mb)))
        else:
            self.status.emit(job_id, f"Downloading model… {done_mb:.0f} MB")
            self.progress.emit(job_id, -1)

    def _run_model(self, job_id, model, path, language, duration, size):
        self.status.emit(job_id, "Reading audio…")
        self.progress.emit(job_id, -1)
        segments_iter, info = model.transcribe(path, language=language, vad_filter=True, beam_size=5)
        self._check_cancel()

        total = info.duration or duration
        self.status.emit(job_id, "Transcribing")
        self.progress.emit(job_id, 0)

        segments = []
        for segment in segments_iter:  # lazy: each step decodes the next chunk of audio
            self._check_cancel()
            text = segment.text.strip()
            if text:
                segments.append((segment.start, segment.end, text))
            if total > 0:
                self.progress.emit(job_id, int(min(segment.end / total, 1.0) * 100))
        self._check_cancel()

        if not segments:
            raise FriendlyError("No speech was detected in this file.")
        return {"segments": segments, "duration": total, "language": info.language, "model": size}
