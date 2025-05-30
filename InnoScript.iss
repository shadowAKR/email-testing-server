[Setup]
AppName=Email Testing Server
AppVersion=1.0
AppPublisher=shadowAKR
DefaultDirName={autopf}\Email Testing Server
UninstallDisplayIcon={app}\EmailTestingServer.exe
CreateAppDir=yes
OutputBaseFilename=Email Testing Server Installer
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "C:\Users\AnanthuKrishnan\Documents\MyProjects\email-testing-server\dist\EmailTestingServer.exe"; DestDir: "{app}"; Flags: ignoreversion

; Add any other assets that were NOT bundled by flet/PyInstaller
; Source: "path\to\your\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Icons]
Name: "{group}\Email Testing Server"; Filename: "{app}\EmailTestingServer.exe"
Name: "{autodesktop}\Email Testing Server"; Filename: "{app}\EmailTestingServer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EmailTestingServer.exe"; Description: "Launch Email Testing Server"; Flags: postinstall skipifsilent

[UninstallRun]
; Optional: Add any cleanup commands if necessary