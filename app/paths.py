"""Where the app keeps its files, plus logging setup.

Everything lives in %APPDATA%\\TapeToTranscriptTool\\. For testing, the
TAPE_TO_TRANSCRIPT_DATA_DIR environment variable can point somewhere else.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DATA_FOLDER_NAME = "TapeToTranscriptTool"


def data_dir() -> Path:
    override = os.environ.get("TAPE_TO_TRANSCRIPT_DATA_DIR")
    if override:
        path = Path(override)
    else:
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(appdata) / DATA_FOLDER_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "transcripts.db"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def models_dir() -> Path:
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return data_dir() / "app.log"


def setup_logging() -> None:
    handler = RotatingFileHandler(log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # These libraries are chatty at INFO level; only keep their warnings.
    for noisy in ("httpx", "httpcore", "urllib3", "huggingface_hub", "filelock"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
