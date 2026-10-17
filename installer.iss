; Inno Setup Script for LSDM (Laboratory Sample & Dispatch Management System)
; Supports clean installation, in-place version updates, and desktop shortcuts.

#define MyAppName "LSDM"
#define MyAppFullName "Laboratory Sample & Dispatch Management System"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Lab Operations & Supply Chain Solutions"
#define MyAppURL "https://github.com/your-username/LSDM"
#define MyAppExeName "LSDM.exe"

[Setup]
; AppId uniquely identifies this application. Do not change this in future versions
; so subsequent installer runs will automatically upgrade existing installations!
AppId={{8B2C4F3E-91DA-4A7F-B35F-1C824E6D79A1}}
AppName={#MyAppFullName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppFullName}
AllowNoIcons=yes
; Output location and filename
OutputDir=dist_installer
OutputBaseFilename=LSDM_Setup_v{#MyAppVersion}
SetupIconFile=assets\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; User level install by default (No Admin rights required, instant installation)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=no
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppFullName} Setup
VersionInfoProductName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application binaries and dependencies
Source: "dist\LSDM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Preserve existing database and backups during version updates - NEVER overwrite!
; The flag 'onlyifdoesntexist' ensures user's existing records are 100% safe when upgrading!
[Files]
Source: "APRIL_TEMPLATE.xlsx"; DestDir: "{app}"; Flags: ignoreversion
Source: "MASTER_TEMPLATE.xlsx"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppFullName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\logo.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppFullName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppFullName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up temp files but preserve database backups if needed
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
