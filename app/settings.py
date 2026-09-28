"""User settings, persisted as JSON in the app data folder."""

import json
import logging

from .paths import settings_path

log = logging.getLogger(__name__)

# (value, label) pairs shown in the settings dialog.
MODEL_SIZES = [
    ("tiny", "Tiny (~75 MB, fastest, least accurate)"),
    ("base", "Base (~145 MB)"),
    ("small", "Small (~485 MB, recommended)"),
    ("medium", "Medium (~1.5 GB, slower, more accurate)"),
    ("large-v3", "Large v3 (~3 GB, slowest, most accurate)"),
]
LANGUAGES = [("auto", "Auto-detect"), ("en", "English")]
DEVICES = [("auto", "Auto"), ("cpu", "CPU"), ("gpu", "GPU (NVIDIA CUDA)")]

DEFAULTS = {
    "model_size": "small",
    "language": "auto",
    "device": "auto",
    "include_timestamps": False,
}

_CHOICES = {
    "model_size": [value for value, _ in MODEL_SIZES],
    "language": [value for value, _ in LANGUAGES],
    "device": [value for value, _ in DEVICES],
}


def load_settings() -> dict:
    settings = dict(DEFAULTS)
    path = settings_path()
    if not path.exists():
        return settings
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.exception("Could not read settings file; using defaults")
        return settings
    if not isinstance(data, dict):
        return settings

    for key, default in DEFAULTS.items():
        value = data.get(key)
        if type(value) is not type(default):
            continue
        if key in _CHOICES and value not in _CHOICES[key]:
            continue
        settings[key] = value
    return settings


def save_settings(settings: dict) -> None:
    path = settings_path()
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception:
        log.exception("Could not save settings")
