@echo off
rem Packages the build from build.bat into release files in dist\:
rem   TapeToTranscriptTool-Setup.exe     (installer, requires Inno Setup 6)
rem   TapeToTranscriptTool-Portable.zip  (unzip and run, nothing installed)
setlocal
cd /d "%~dp0"

if not exist "dist\TapeToTranscriptTool\TapeToTranscriptTool.exe" (
    echo Run build.bat first.
    exit /b 1
)

set "ISCC="
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe") do (
    if not defined ISCC if exist %%P set "ISCC=%%~P"
)
if not defined ISCC (
    echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php
    echo or run: winget install JRSoftware.InnoSetup
    exit /b 1
)

echo Building installer...
"%ISCC%" /Q installer.iss || goto :error

echo Creating portable zip...
if exist "dist\TapeToTranscriptTool-Portable.zip" del "dist\TapeToTranscriptTool-Portable.zip"
tar -a -cf "dist\TapeToTranscriptTool-Portable.zip" -C dist TapeToTranscriptTool || goto :error

echo.
echo Release files are in dist\
exit /b 0

:error
echo.
echo Packaging failed. See the messages above.
exit /b 1
