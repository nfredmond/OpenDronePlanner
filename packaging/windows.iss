[Setup]
AppId=OpenDronePlanner
AppName=OpenDronePlanner
AppVersion=2.0.0
DefaultDirName={localappdata}\Programs\OpenDronePlanner
DefaultGroupName=OpenDronePlanner
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=OpenDronePlanner-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
UninstallDisplayIcon={app}\OpenDronePlanner.exe
[Files]
Source: "..\dist\OpenDronePlanner\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\OpenDronePlanner"; Filename: "{app}\OpenDronePlanner.exe"
Name: "{autodesktop}\OpenDronePlanner"; Filename: "{app}\OpenDronePlanner.exe"
[Run]
Filename: "{app}\OpenDronePlanner.exe"; Description: "Open OpenDronePlanner"; Flags: nowait postinstall skipifsilent
