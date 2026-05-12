; ── VideoDownloader Inno Setup Script ──────────────────────────────
; Produces a single Setup_VideoDownloader.exe that installs:
;   - VideoDownloader.exe  (PyInstaller bundle — Python included)
;   - yt-dlp.exe           (standalone)
;   - ffmpeg.exe / ffprobe.exe (standalone)
;
; Prerequisites (placed by build_installer.bat):
;   installer\app\VideoDownloader.exe
;   installer\app\yt-dlp.exe
;   installer\app\ffmpeg.exe
;   installer\app\ffprobe.exe

#define MyAppName "Video Downloader"
#define MyAppVersion "1.0"
#define MyAppPublisher "VideoDownloader"
#define MyAppExeName "VideoDownloader.exe"

[Setup]
AppId={{8A3F5B2E-7C91-4D6A-B8E0-1F2A3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer\output
OutputBaseFilename=Setup_VideoDownloader
SetupIconFile=installer\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "installer\app\VideoDownloader.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\app\yt-dlp.exe";          DestDir: "{app}"; Flags: ignoreversion
Source: "installer\app\ffmpeg.exe";          DestDir: "{app}"; Flags: ignoreversion
Source: "installer\app\ffprobe.exe";         DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";         Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}";   Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
