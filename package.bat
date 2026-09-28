@echo off
rem Builds the Windows installer, dist\TapeToTranscriptTool-Setup.exe,
rem from the build made by build.bat. Requires Inno Setup 6.
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

echo.
echo Installer created: dist\TapeToTranscriptTool-Setup.exe
exit /b 0

:error
echo.
echo Packaging failed. See the messages above.
exit /b 1
