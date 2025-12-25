; Inno Setup script template for File-Manager
; Customize `AppId`, `AppName`, `AppVersion`, `DefaultDirName`, and file list as needed.

[Setup]
AppId={{YOUR-GUID-HERE}}
AppName=File-Manager
AppVersion=0.1.0
DefaultDirName={pf}\File-Manager
DisableProgramGroupPage=yes
OutputBaseFilename=File-Manager-Setup
Compression=lzma
SolidCompression=yes

[Files]
; Replace with your built EXE path from PyInstaller `dist\FileManager.exe`
Source: "dist\\FileManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\File-Manager"; Filename: "{app}\FileManager.exe"

[Run]
Filename: "{app}\FileManager.exe"; Description: "Launch File-Manager"; Flags: nowait postinstall skipifsilent
