@echo off
setlocal enabledelayedexpansion
title Video Downloader — Installer Builder
echo.
echo ============================================================
echo   Video Downloader — Full Installer Builder
echo   (No admin rights required — pure Python)
echo ============================================================
echo.
echo This script will:
echo   1. Install build tools (PyInstaller, customtkinter, Pillow)
echo   2. Download yt-dlp.exe (standalone)
echo   3. Download ffmpeg.exe + ffprobe.exe (standalone)
echo   4. Build VideoDownloader.exe (the app)
echo   5. Pack everything into a ZIP
echo   6. Build Setup_VideoDownloader.exe (self-extracting installer)
echo.
echo Prerequisites:  Python 3.10+ on PATH.  Nothing else.
echo.
pause

cd /d "%~dp0"

REM ── 1. Install Python deps ────────────────────────────────────────
echo.
echo [1/6] Installing Python build dependencies...
pip install pyinstaller customtkinter Pillow
if errorlevel 1 (
    echo FAILED: pip install. Make sure Python is on PATH.
    pause & exit /b 1
)

REM ── 2. Prepare staging folder ─────────────────────────────────────
echo.
echo [2/6] Preparing staging folder...
if exist installer\app rmdir /s /q installer\app
mkdir installer\app

REM ── 3. Download yt-dlp.exe ────────────────────────────────────────
echo.
echo [3/6] Downloading yt-dlp.exe ...
if not exist installer\app\yt-dlp.exe (
    curl -L -o installer\app\yt-dlp.exe https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
    if errorlevel 1 (
        echo FAILED: Could not download yt-dlp.exe
        pause & exit /b 1
    )
)
echo   OK: yt-dlp.exe

REM ── 4. Download ffmpeg ────────────────────────────────────────────
echo.
echo [4/6] Downloading ffmpeg...
if not exist installer\app\ffmpeg.exe (
    echo   Downloading ffmpeg release zip...
    curl -L -o installer\ffmpeg.zip https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
    if errorlevel 1 (
        echo FAILED: Could not download ffmpeg.
        pause & exit /b 1
    )

    echo   Extracting ffmpeg.exe and ffprobe.exe...
    powershell -NoProfile -Command ^
        "$zip = 'installer\ffmpeg.zip'; " ^
        "$tmp = 'installer\_ffmpeg_tmp'; " ^
        "Expand-Archive -Path $zip -DestinationPath $tmp -Force; " ^
        "$bin = Get-ChildItem -Path $tmp -Recurse -Filter 'ffmpeg.exe' | Select-Object -First 1; " ^
        "Copy-Item $bin.FullName 'installer\app\ffmpeg.exe'; " ^
        "$probe = Get-ChildItem -Path $tmp -Recurse -Filter 'ffprobe.exe' | Select-Object -First 1; " ^
        "Copy-Item $probe.FullName 'installer\app\ffprobe.exe'; " ^
        "Remove-Item -Recurse -Force $tmp; " ^
        "Remove-Item -Force $zip"
    if not exist installer\app\ffmpeg.exe (
        echo FAILED: ffmpeg extraction failed.
        pause & exit /b 1
    )
)
echo   OK: ffmpeg.exe + ffprobe.exe

REM ── 5. Generate icon ──────────────────────────────────────────────
echo.
echo [5/6] Generating icon...
if not exist installer\icon.ico (
    python generate_icon.py
)

REM Copy icon into app bundle
if exist installer\icon.ico copy /y installer\icon.ico installer\app\icon.ico >nul

REM ── 6. Build VideoDownloader.exe ──────────────────────────────────
echo.
echo [6/6] Building VideoDownloader.exe ...
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i

pyinstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "ARIsYoutubeSongsDownloader" ^
  --add-data "%CTK_PATH%;customtkinter/" ^
  --icon "installer\icon.ico" ^
  app.py

if errorlevel 1 (
    echo FAILED: PyInstaller build for app failed.
    pause & exit /b 1
)

copy /y dist\ARIsYoutubeSongsDownloader.exe installer\app\ARIsYoutubeSongsDownloader.exe >nul
echo   OK: ARIsYoutubeSongsDownloader.exe

REM ── 7. Create app.zip from staging ────────────────────────────────
echo.
echo [PACK] Creating app.zip ...
if exist installer\app.zip del installer\app.zip
powershell -NoProfile -Command "Compress-Archive -Path 'installer\app\*' -DestinationPath 'installer\app.zip' -Force"
echo   OK: app.zip

REM ── 8. Build Setup_VideoDownloader.exe (self-extracting) ──────────
echo.
echo [SETUP] Building Setup_VideoDownloader.exe ...

pyinstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "Setup_ARIs_Downloader" ^
  --add-data "%CTK_PATH%;customtkinter/" ^
  --add-data "installer\app.zip;." ^
  --icon "installer\icon.ico" ^
  setup_gui.py

if errorlevel 1 (
    echo FAILED: PyInstaller build for installer failed.
    pause & exit /b 1
)

REM Move to output folder
if not exist installer\output mkdir installer\output
move /y dist\Setup_ARIs_Downloader.exe installer\output\Setup_ARIs_Downloader.exe >nul

echo.
echo ============================================================
echo   SUCCESS!
echo.
echo   Installer:  installer\output\Setup_ARIs_Downloader.exe
echo.
echo   Send this single file to anyone. They double-click,
echo   pick a folder, click Install — done.
echo   No Python, no admin, no extra downloads.
echo ============================================================
echo.
pause
