#define AppName "ProTech Marble & Porcelain Manager"
#define AppVersion "2.0.0"
#define AppExeName "ProTechStoneManager.exe"
[Setup]
AppId={{DDA3B099-8B91-42A5-93B5-832641790B85}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Abu Omar - ProTech
LicenseFile=LICENSE
#ifdef PROTECH_SIGNED_BUILD
SignTool=ProTechSigner
SignedUninstaller=yes
#endif
AppPublisherURL=https://github.com/Abdealmalk007
DefaultDirName={localappdata}\Programs\ProTechStoneManager
DefaultGroupName={#AppName}
UsePreviousAppDir=yes
UsePreviousGroup=yes
CloseApplications=no
RestartApplications=no
PrivilegesRequired=lowest
OutputDir=Release
OutputBaseFilename=Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=src\Assets\PorcelainManager.ico
UninstallDisplayIcon={app}\{#AppExeName}
DisableWelcomePage=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
[Files]
Source: "Releases\ProTechStoneManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch ProTech Marble & Porcelain Manager"; Flags: nowait postinstall skipifsilent
