# ARI's Youtube Songs Downloader

A standalone video/audio downloader with a dark-themed GUI.  
Paste links, click download — that's it.

---

## Features

- Separate input fields for each link (add as many as you want)
- **Audio only (MP3)** toggle
- **Download full playlists** toggle
- Per-download status with error codes and expandable details
- Bundled `yt-dlp` + `ffmpeg` — no extra installs for end users
- Self-extracting installer with desktop shortcut

---

## Project Structure

```
downloader_app/
├── app.py               ← main GUI application
├── setup_gui.py          ← installer GUI (self-extracting)
├── generate_icon.py      ← generates the ARI icon (.ico)
├── build_installer.bat   ← one-click: builds everything into an installer
├── build.bat             ← builds only the app .exe (no installer)
├── installer.iss         ← legacy Inno Setup script (not required)
└── installer/
    ├── icon.ico          ← generated app icon
    ├── app/              ← staging folder (created during build)
    ├── app.zip           ← zipped bundle (created during build)
    └── output/
        └── Setup_ARIs_Downloader.exe  ← final installer
```

---

## Requirements (for building)

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python**  | 3.10+   | Must be on PATH |
| **pip**     | any     | Comes with Python |
| **Internet**| —       | To download yt-dlp and ffmpeg during build |

**No admin rights needed.** Everything installs into user-space.

The build script automatically installs these Python packages:
- `pyinstaller` — bundles Python into a standalone .exe
- `customtkinter` — the GUI framework
- `Pillow` — generates the icon

---

## How to Build the Installer

### Quick version

1. Open a terminal in `downloader_app/`
2. Run:
   ```
   build_installer.bat
   ```
3. Wait for it to finish (~2-5 minutes)
4. Find the installer at:
   ```
   installer\output\Setup_ARIs_Downloader.exe
   ```

### What the build does (step by step)

1. **Installs Python build deps** — PyInstaller, customtkinter, Pillow
2. **Downloads yt-dlp.exe** — standalone binary from GitHub releases
3. **Downloads ffmpeg** — extracts `ffmpeg.exe` and `ffprobe.exe` from the official builds
4. **Generates icon** — creates `installer/icon.ico` with the ARI logo
5. **Builds the app .exe** — PyInstaller bundles `app.py` + Python runtime + customtkinter into a single `ARIsYoutubeSongsDownloader.exe`
6. **Zips everything** — app exe + yt-dlp + ffmpeg + icon → `app.zip`
7. **Builds the installer .exe** — PyInstaller bundles `setup_gui.py` + `app.zip` into `Setup_ARIs_Downloader.exe`

### Build only the app (no installer)

If you just want to run the app locally without building a distributable installer:

```
pip install customtkinter
python app.py
```

This requires `yt-dlp` on your PATH.

---

## How to Distribute

Send **only this one file** to your friend:

```
installer\output\Setup_ARIs_Downloader.exe
```

### What your friend does

1. Double-click `Setup_ARIs_Downloader.exe`
2. Pick an install folder (defaults to `~/ARIs Youtube Songs Downloader`)
3. Check "Create Desktop shortcut" if wanted
4. Click **Install**
5. Done — launch from desktop or install folder

### What's inside the installer

Everything is self-contained:
- Python runtime (embedded by PyInstaller)
- The app GUI
- `yt-dlp.exe` (downloads videos)
- `ffmpeg.exe` + `ffprobe.exe` (merges audio/video streams)

**No Python, no admin rights, no internet** needed on the target machine to install.  
Internet is only needed when actually downloading videos.

---

## How to Use the App

1. **Paste links** — one per field. Click "+ Add link" for more fields.
2. **Choose output folder** — defaults to `~/Downloads/VideoDownloader`
3. **Toggle options:**
   - **Audio only (MP3)** — extracts audio instead of downloading video
   - **Download full playlists** — downloads all videos in a playlist link
4. **Click "Download All"**
5. Watch the progress — each link shows status:
   - ● queued → ● downloading → ✓ done / ✗ failed
6. If a download fails, click **"Show details"** to see the full error and error code

### Common Error Codes

| Code | Meaning |
|------|---------|
| E403 | Forbidden — geo-blocked or age-restricted |
| E404 | Not found — deleted or wrong URL |
| E429 | Rate limited — wait and try again |
| EPRV | Private video |
| EUNA | Video unavailable — removed or region-locked |
| EURL | Invalid or unsupported URL |
| EEXT | Extraction failed — try updating yt-dlp |
| EFMT | Requested format not available |
| ESSL | SSL error — corporate network/proxy issue |
| ECPR | Blocked by copyright |

---

## Troubleshooting

### Build fails at "pip install"
Make sure Python 3.10+ is installed and `python` / `pip` are on your PATH:
```
python --version
pip --version
```

### Build fails downloading yt-dlp or ffmpeg
Check your internet connection. If behind a proxy, set:
```
set HTTPS_PROXY=http://your-proxy:port
```

### App shows "yt-dlp not found"
When running locally (not from installer), install yt-dlp:
```
pip install yt-dlp
```

### All downloads fail with ESSL
You're behind a corporate proxy doing SSL inspection. The app already passes `--no-check-certificates` to handle this.

### Desktop shortcut not created
The installer tries VBScript (`cscript`) to create the shortcut. If it fails, a warning dialog shows the exe path so you can create a shortcut manually.
