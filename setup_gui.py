#!/usr/bin/env python3
"""
Self-extracting installer for Video Downloader.
Built with PyInstaller — contains the app + yt-dlp + ffmpeg in a bundled ZIP.
When the user runs this .exe it shows a simple GUI to pick an install folder,
extracts everything, and creates a desktop shortcut.
No admin rights required.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

# ── Theme (matches the main app) ─────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#6C5CE7"
ACCENT_HOVER = "#5A4BD1"
SUCCESS = "#00B894"
ERROR = "#D63031"
SURFACE = "#1E1E2E"
SURFACE_ALT = "#262637"
TEXT = "#CDD6F4"
TEXT_DIM = "#6C7086"


def _bundle_dir() -> Path:
    """Where PyInstaller extracts bundled data at runtime."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _find_bundle_zip() -> Path | None:
    """Locate the bundled app.zip inside the PyInstaller temp dir."""
    candidates = [
        _bundle_dir() / "app.zip",
        Path(__file__).resolve().parent / "installer" / "app.zip",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _get_desktop() -> Path:
    """Get the real Desktop path (handles OneDrive redirects etc.)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        p = result.stdout.strip()
        if p and Path(p).is_dir():
            return Path(p)
    except Exception:
        pass
    return Path.home() / "Desktop"


def _create_shortcut(target: Path, shortcut_path: Path, icon: Path | None = None) -> bool:
    """Create a Windows .lnk shortcut via a temp VBScript (most reliable, no admin)."""
    import tempfile

    # Use VBScript — avoids PowerShell execution policy and quoting issues entirely
    icon_line = ""
    if icon and icon.is_file():
        icon_line = f'oLink.IconLocation = "{icon}"'

    vbs = (
        'Set oWS = WScript.CreateObject("WScript.Shell")\n'
        f'Set oLink = oWS.CreateShortcut("{shortcut_path}")\n'
        f'oLink.TargetPath = "{target}"\n'
        f'oLink.WorkingDirectory = "{target.parent}"\n'
        f'{icon_line}\n'
        'oLink.Save\n'
    )

    tmp = Path(tempfile.gettempdir()) / "_ari_shortcut.vbs"
    tmp.write_text(vbs, encoding="utf-8")

    result = subprocess.run(
        ["cscript", "//Nologo", str(tmp)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    tmp.unlink(missing_ok=True)
    return result.returncode == 0


class InstallerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("ARI's Youtube Songs Downloader — Setup")
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(fg_color=SURFACE)

        self._build_ui()

    def _build_ui(self) -> None:
        # Icon + title
        ctk.CTkLabel(
            self, text="ARI", font=("Segoe UI Bold", 48), text_color=ACCENT,
        ).pack(pady=(30, 0))

        ctk.CTkLabel(
            self, text="ARI's Youtube Songs Downloader",
            font=("Segoe UI Semibold", 20), text_color=TEXT,
        ).pack(pady=(4, 2))

        ctk.CTkLabel(
            self, text="Setup",
            font=("Segoe UI", 14), text_color=TEXT_DIM,
        ).pack()

        # Install location
        loc_frame = ctk.CTkFrame(self, fg_color="transparent")
        loc_frame.pack(fill="x", padx=40, pady=(30, 0))

        ctk.CTkLabel(
            loc_frame, text="Install to:",
            font=("Segoe UI", 13), text_color=TEXT_DIM,
        ).pack(anchor="w")

        entry_row = ctk.CTkFrame(loc_frame, fg_color="transparent")
        entry_row.pack(fill="x", pady=(4, 0))
        entry_row.grid_columnconfigure(0, weight=1)

        default_dir = str(Path.home() / "ARIs Youtube Songs Downloader")
        self.dir_var = ctk.StringVar(value=default_dir)

        ctk.CTkEntry(
            entry_row, textvariable=self.dir_var, font=("Segoe UI", 13),
            fg_color=SURFACE_ALT, border_color="#313244", text_color=TEXT,
            corner_radius=8,
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            entry_row, text="Browse", width=80, font=("Segoe UI", 13),
            fg_color=SURFACE_ALT, hover_color="#363649", corner_radius=8,
            command=self._browse,
        ).grid(row=0, column=1, padx=(8, 0))

        # Options
        self.shortcut_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self, text="Create Desktop shortcut",
            font=("Segoe UI", 13), text_color=TEXT_DIM,
            variable=self.shortcut_var, fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
        ).pack(padx=40, pady=(16, 0), anchor="w")

        # Install button
        self.install_btn = ctk.CTkButton(
            self, text="Install", font=("Segoe UI Semibold", 16),
            height=48, corner_radius=10, fg_color=ACCENT,
            hover_color=ACCENT_HOVER, command=self._install,
        )
        self.install_btn.pack(fill="x", padx=40, pady=(28, 0))

        # Status
        self.status = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 12), text_color=TEXT_DIM,
        )
        self.status.pack(pady=(10, 0))

    def _browse(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.dir_var.set(path)

    def _install(self) -> None:
        zip_path = _find_bundle_zip()
        if not zip_path:
            messagebox.showerror("Error", "Bundle not found. The installer may be corrupted.")
            return

        dest = Path(self.dir_var.get()).resolve()

        self.install_btn.configure(state="disabled", text="Installing…")
        self.status.configure(text="Extracting files…", text_color=TEXT_DIM)
        self.update()

        try:
            dest.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(dest)

            exe_path = dest / "ARIsYoutubeSongsDownloader.exe"

            if not exe_path.is_file():
                raise FileNotFoundError(f"ARIsYoutubeSongsDownloader.exe not found in {dest}")

            # Desktop shortcut
            if self.shortcut_var.get():
                self.status.configure(text="Creating shortcut…")
                self.update()
                desktop = _get_desktop()
                desktop.mkdir(parents=True, exist_ok=True)
                icon_path = dest / "icon.ico"
                ok = _create_shortcut(
                    exe_path,
                    desktop / "ARIs Youtube Songs Downloader.lnk",
                    icon_path if icon_path.is_file() else None,
                )
                if not ok:
                    messagebox.showwarning(
                        "Shortcut",
                        "Could not create desktop shortcut.\n"
                        "You can manually create one from:\n"
                        f"{exe_path}",
                    )

            self.status.configure(text="Installation complete!", text_color=SUCCESS)
            self.install_btn.configure(text="✓ Installed")

            messagebox.showinfo(
                "Done",
                f"ARI's Youtube Songs Downloader installed to:\n{dest}\n\n"
                "You can close this window and launch it from the Desktop shortcut "
                "or directly from the install folder.",
            )

        except Exception as exc:
            self.status.configure(text=f"Error: {exc}", text_color=ERROR)
            self.install_btn.configure(state="normal", text="Retry")


def main() -> None:
    app = InstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
