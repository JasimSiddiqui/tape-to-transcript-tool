# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build definition. Run through build.bat, or:
#   pyinstaller --noconfirm --clean TapeToTranscriptTool.spec
# Produces dist\TapeToTranscriptTool\TapeToTranscriptTool.exe (one-folder, windowed).

import os
import sys

from PyInstaller.utils.hooks import collect_all

# The .exe icon is rendered from the same code that draws the in-app logo.
sys.path.insert(0, SPECPATH)
from app.ui.logo import write_ico  # noqa: E402

os.makedirs(os.path.join(SPECPATH, "build"), exist_ok=True)
ICON_PATH = os.path.join(SPECPATH, "build", "TapeToTranscriptTool.ico")
write_ico(ICON_PATH)

datas = []
binaries = []
hiddenimports = []

# These packages ship data files and native DLLs that PyInstaller's import
# analysis would miss:
#   faster_whisper - assets\silero_vad_v6.onnx (the VAD model used by vad_filter)
#   ctranslate2    - ctranslate2.dll, libiomp5md.dll, cudnn64_9.dll
#   av             - the FFmpeg DLLs used to decode video/audio (no separate ffmpeg install)
#   onnxruntime    - runs the Silero VAD model
#   tokenizers     - Whisper's tokenizer (native extension)
for package in ("faster_whisper", "ctranslate2", "av", "onnxruntime", "tokenizers"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# ctranslate2's model converters need torch/transformers and are never used here.
hiddenimports = [name for name in hiddenimports if not name.startswith("ctranslate2.converters")]

a = Analysis(
    ["main.py"],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "torch", "transformers", "tensorflow", "matplotlib", "pandas", "scipy", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TapeToTranscriptTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=ICON_PATH,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="TapeToTranscriptTool",
)
