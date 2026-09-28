# Tape to Transcript Tool

A Windows desktop app that turns lecture videos into plain-text transcripts, entirely
offline, using a local [Whisper](https://github.com/openai/whisper) model via
[faster-whisper](https://github.com/SYSTRAN/faster-whisper).

- Add videos or audio (mp4, mkv, mov, webm, avi, m4a, mp3, wav) with **Add Videos**,
  by dropping them onto the window, or by dropping them onto the `.exe`.
- Files are transcribed one at a time in the background; you can cancel the current
  file or remove queued ones.
- Finished transcripts are saved automatically and are searchable by title and text.
- **Copy**, **Copy with Prompt** (adds a "summarize the key concepts…" request in front,
  ready to paste into an AI chat), **Download .txt**, **Rename**, **Delete**.
- **Include timestamps** switches between plain paragraphs and `[HH:MM:SS]` lines at
  any time, for existing transcripts too.

No separate FFmpeg install is needed: audio is decoded with PyAV, which bundles FFmpeg.

## Running the app

Run `dist\TapeToTranscriptTool\TapeToTranscriptTool.exe`. The whole
`dist\TapeToTranscriptTool` folder is the app. Copy the entire folder if you move it,
not just the `.exe`.

The first time you use a model size, it is downloaded (Small, the default, is about
485 MB). After that the app works fully offline. Choose the model size, language and
device in **Settings**:

| Model    | Download | Notes                                  |
|----------|----------|----------------------------------------|
| tiny     | ~75 MB   | Fastest, least accurate                |
| base     | ~145 MB  |                                        |
| small    | ~485 MB  | Default; good balance                  |
| medium   | ~1.5 GB  | Slower, more accurate                  |
| large-v3 | ~3 GB    | Slowest, most accurate (GPU recommended)|

Speed depends on your CPU and the model size. As a reference point, on the machine
this was built on, *small* on the CPU transcribed a 46-second clip in about 6 seconds.
Larger models are several times slower.

## Building the .exe

Requirements: Windows 10/11 and Python 3.11, 3.12 or 3.13 (from python.org, with the
`py` launcher). Then run:

```bat
build.bat
```

This creates a virtual environment in `.venv`, installs `requirements.txt`, and runs
PyInstaller with `TapeToTranscriptTool.spec`. The result is
`dist\TapeToTranscriptTool\TapeToTranscriptTool.exe` (one-folder, windowed build).

To run from source instead:

```bat
.venv\Scripts\python.exe main.py
```

## Where data is stored

Everything lives in `%APPDATA%\TapeToTranscriptTool\` (Settings has an
**Open data folder** link):

| Path              | Contents                                        |
|-------------------|-------------------------------------------------|
| `transcripts.db`  | SQLite database of transcripts and timestamped segments |
| `settings.json`   | Your settings                                   |
| `models\`         | Downloaded Whisper models, one folder per size  |
| `app.log`         | Rotating log file (errors and details)          |

To start over, close the app and delete the folder. To free disk space, delete model
folders you no longer use; they are downloaded again if needed.

## Enabling the GPU (NVIDIA only)

With **Device** set to *Auto*, the app uses an NVIDIA GPU when one is found **and** the
CUDA libraries are available. Otherwise it uses the CPU. If the GPU fails for any
reason, the app switches to the CPU automatically and shows a notice; it never crashes
over this.

The GPU needs:

1. A recent NVIDIA driver (one that supports CUDA 12).
2. **cuBLAS for CUDA 12**: `cublas64_12.dll`, `cublasLt64_12.dll`
3. **cuDNN 9 for CUDA 12**: `cudnn_ops64_9.dll`, `cudnn_cnn64_9.dll` and the other
   `cudnn*64_9.dll` files

Easiest ways to get them:

- Install the [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads) and
  [cuDNN 9](https://developer.nvidia.com/cudnn-downloads) for CUDA 12, and make sure
  their `bin` folders are on your `PATH`. Or:
- Download the prebuilt DLLs from
  [Purfview/whisper-standalone-win](https://github.com/Purfview/whisper-standalone-win/releases/tag/libs)
  (the cuBLAS + cuDNN archive for CUDA 12) and put the DLLs next to
  `TapeToTranscriptTool.exe`.

Restart the app afterwards. The Settings dialog shows whether a GPU was detected.

## Project layout

```
main.py                     entry point
app/transcriber.py          background worker: model download, CPU/GPU choice, transcription
app/database.py             SQLite storage
app/settings.py             settings.json load/save
app/formatting.py           plain / timestamped text, the summary prompt
app/paths.py                data folder locations and logging
app/ui/main_window.py       main window (header, queue, dashboard)
app/ui/queue_panel.py       queue rows
app/ui/settings_dialog.py   settings dialog
app/ui/widgets.py           toggle switch, elided label
app/ui/logo.py              the logo, drawn in code (also generates the .exe icon)
app/ui/style.py             colors and Qt stylesheet
```

## Known limitations

- Cancelling takes effect between chunks of audio (usually within a few seconds). While
  a long file is first being decoded, cancel waits until decoding finishes.
- Cancelling during a model download stops the job, but the download keeps going in the
  background so it doesn't have to start over.
- Plain-text paragraphs are split about once a minute at sentence ends, not by topic.
- Very long files are decoded into memory in full (about 230 MB of RAM per hour of audio).
- The GPU path could not be tested on the build machine (no NVIDIA GPU); the automatic
  fallback to the CPU was tested.
