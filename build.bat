@echo off
REM ── Build Video Downloader as a standalone .exe ──────────────────
REM Run this from the downloader_app/ folder.
REM Requires:  pip install pyinstaller customtkinter

echo Installing build dependencies...
pip install customtkinter pyinstaller

echo.
echo Building .exe ...

REM Locate the customtkinter package folder for bundling
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i

pyinstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "VideoDownloader" ^
  --add-data "%CTK_PATH%;customtkinter/" ^
  --icon "NONE" ^
  app.py

echo.
echo ✔ Done!  Find your .exe in:  dist\VideoDownloader.exe
pause
