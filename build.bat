@echo off
rem Builds dist\TapeToTranscriptTool\TapeToTranscriptTool.exe
rem Creates a virtual environment in .venv, installs requirements, runs PyInstaller.
setlocal
cd /d "%~dp0"

rem Prefer Python 3.12/3.13/3.11 through the "py" launcher; fall back to "python" (3.11+).
set "PY="
for %%V in (3.12 3.13 3.11) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo Python 3.11 or newer was not found. Install it from https://www.python.org/downloads/
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment with %PY% ...
    %PY% -m venv .venv || goto :error
)

echo Installing requirements...
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error

echo Building with PyInstaller...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean TapeToTranscriptTool.spec || goto :error

echo.
echo Build complete: dist\TapeToTranscriptTool\TapeToTranscriptTool.exe
exit /b 0

:error
echo.
echo Build failed. See the messages above.
exit /b 1
