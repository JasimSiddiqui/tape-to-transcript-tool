"""Entry point for Tape to Transcript Tool.

Usage: python main.py [video files...]
Files given on the command line (or dropped onto the .exe) are added to the queue.
"""

import os
import sys

# A windowed (no console) build has no stdout/stderr, and libraries that print
# progress would crash writing to None. Send that output nowhere instead.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Hugging Face Hub (used only to download models): plain HTTP downloads so
# progress can be measured on disk, no console progress bars, no telemetry.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from app.ui.main_window import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
