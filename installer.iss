; Inno Setup script for the Windows installer.
; Built by package.bat after build.bat has produced dist\TapeToTranscriptTool\.
; Installs per-user (no admin prompt) and adds a desktop shortcut.

#define AppName "Tape to Transcript Tool"
#define AppVersion "1.0.0"
#define AppExe "TapeToTranscriptTool.exe"

[Setup]
AppId={{6B3E8F2A-4C1D-4E7B-9A5F-2D8C1E0B7A64}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Jasim Siddiqui
AppPublisherURL=https://github.com/JasimSiddiqui/tape-to-transcript-tool
DefaultDirName={localappdata}\Programs\TapeToTranscriptTool
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=TapeToTranscriptTool-Setup
SetupIconFile=build\TapeToTranscriptTool.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "dist\TapeToTranscriptTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
