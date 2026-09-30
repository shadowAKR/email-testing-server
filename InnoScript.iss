[Setup]
AppName=Postroom
AppVersion=3.0.0
AppPublisher=shadowAKR
DefaultDirName={autopf}\Postroom
UninstallDisplayIcon={app}\postroom.exe
OutputDir=build\bin
OutputBaseFilename=Postroom-Setup
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible

[Files]
Source: "build\bin\postroom.exe"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Icons]
Name: "{group}\Postroom"; Filename: "{app}\postroom.exe"
Name: "{autodesktop}\Postroom"; Filename: "{app}\postroom.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\postroom.exe"; Description: "Launch Postroom"; Flags: postinstall skipifsilent
