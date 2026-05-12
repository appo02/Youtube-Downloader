#!/usr/bin/env python3
"""
Video Downloader — GUI app built with CustomTkinter.
Paste links in separate fields, hit Download.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

# ── Theme ─────────────────────────────────────────────────────────────
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
CARD_RADIUS = 14


# ── Helpers ───────────────────────────────────────────────────────────
URL_RE = re.compile(r"https?://\S+")


def _app_dir() -> Path:
    """Return the directory the app lives in (works for PyInstaller bundles too)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def find_yt_dlp() -> str | None:
    bundled = _app_dir() / "yt-dlp.exe"
    if bundled.is_file():
        return str(bundled)
    return shutil.which("yt-dlp")


def find_ffmpeg_dir() -> str | None:
    bundled = _app_dir() / "ffmpeg.exe"
    if bundled.is_file():
        return str(_app_dir())
    return None


def extract_url(text: str) -> str | None:
    m = URL_RE.search(text.strip())
    return m.group(0) if m else None


# ── Error classification ──────────────────────────────────────────────
ERROR_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"HTTP Error 403", re.I),           "E403", "Forbidden — video is geo-blocked or age-restricted"),
    (re.compile(r"HTTP Error 404", re.I),           "E404", "Not found — video was deleted or URL is wrong"),
    (re.compile(r"HTTP Error 429", re.I),           "E429", "Rate limited — too many requests, try again later"),
    (re.compile(r"Private video", re.I),            "EPRV", "Private video — not publicly accessible"),
    (re.compile(r"Video unavailable", re.I),        "EUNA", "Video unavailable — removed or region-locked"),
    (re.compile(r"Sign in to confirm", re.I),       "EAGE", "Age-restricted — requires sign-in (use --cookies)"),
    (re.compile(r"is not a valid URL", re.I),       "EURL", "Invalid URL format"),
    (re.compile(r"Unsupported URL", re.I),          "EURL", "Unsupported URL — site not recognized by yt-dlp"),
    (re.compile(r"unable to extract", re.I),        "EEXT", "Extraction failed — site may have changed, try: yt-dlp -U"),
    (re.compile(r"No video formats", re.I),         "EFMT", "No downloadable formats found"),
    (re.compile(r"Requested format.*not available", re.I), "EFMT", "Requested format not available for this video"),
    (re.compile(r"ffmpeg.*not found", re.I),        "EFFM", "ffmpeg not found — install ffmpeg to merge formats"),
    (re.compile(r"login required", re.I),           "ELOG", "Login required — use --cookies to authenticate"),
    (re.compile(r"copyright", re.I),                "ECPR", "Blocked due to copyright claim"),
    (re.compile(r"WinError|PermissionError", re.I), "EPERM", "Permission denied — close the file or run as admin"),
    (re.compile(r"No space left", re.I),            "EDSK", "Disk full — free up space"),
    (re.compile(r"timed? ?out|ConnectTimeout", re.I), "ETIM", "Connection timed out — check your internet"),
    (re.compile(r"getaddrinfo|Name.*resolution", re.I), "EDNS", "DNS resolution failed — check your internet"),
    (re.compile(r"SSL|certificate", re.I),          "ESSL", "SSL/certificate error — network or proxy issue"),
]


def classify_error(output: str, return_code: int) -> tuple[str, str]:
    for pattern, code, desc in ERROR_PATTERNS:
        if pattern.search(output):
            return code, desc
    for line in reversed(output.splitlines()):
        if line.strip().upper().startswith("ERROR"):
            msg = re.sub(r"(?i)^ERROR[:\s]*", "", line.strip())
            return f"E{return_code}", msg[:120] if msg else "Unknown error"
    return f"E{return_code}", "Unknown error — see full output below"


# ── Link input row ────────────────────────────────────────────────────
class LinkRow(ctk.CTkFrame):
    """A single URL input field with a remove button."""

    def __init__(self, master: ctk.CTkBaseClass, index: int, on_remove) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)

        self.num_label = ctk.CTkLabel(
            self,
            text=f"{index}",
            font=("Segoe UI Semibold", 13),
            text_color=ACCENT,
            width=28,
        )
        self.num_label.grid(row=0, column=0, padx=(0, 6))

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text="Paste video URL here…",
            font=("Segoe UI", 13),
            fg_color=SURFACE,
            border_color="#313244",
            text_color=TEXT,
            corner_radius=8,
            height=38,
        )
        self.entry.grid(row=0, column=1, sticky="ew")

        self.remove_btn = ctk.CTkButton(
            self,
            text="✕",
            font=("Segoe UI", 14),
            width=34,
            height=34,
            fg_color="transparent",
            hover_color="#45475A",
            text_color=TEXT_DIM,
            corner_radius=8,
            command=lambda: on_remove(self),
        )
        self.remove_btn.grid(row=0, column=2, padx=(6, 0))

    def get_url(self) -> str:
        return self.entry.get().strip()

    def set_number(self, n: int) -> None:
        self.num_label.configure(text=f"{n}")


# ── Download result card ──────────────────────────────────────────────
class ResultCard(ctk.CTkFrame):
    """Shows download status with expandable error details."""

    def __init__(self, master: ctk.CTkBaseClass, url: str, index: int) -> None:
        super().__init__(master, corner_radius=10, fg_color=SURFACE_ALT)
        self.grid_columnconfigure(1, weight=1)
        self._expanded = False

        self.status_dot = ctk.CTkLabel(
            self, text="●", font=("Segoe UI", 14), text_color=TEXT_DIM, width=24,
        )
        self.status_dot.grid(row=0, column=0, padx=(12, 4), pady=10)

        self.label = ctk.CTkLabel(
            self,
            text=f"{index}. {url}",
            font=("Segoe UI", 13),
            text_color=TEXT,
            anchor="w",
        )
        self.label.grid(row=0, column=1, padx=4, pady=10, sticky="w")

        self.status_label = ctk.CTkLabel(
            self, text="queued", font=("Segoe UI", 12), text_color=TEXT_DIM, width=80,
        )
        self.status_label.grid(row=0, column=2, padx=(4, 14), pady=10)

        self.error_summary = ctk.CTkLabel(
            self, text="", font=("Segoe UI Semibold", 12), text_color=ERROR, anchor="w",
        )
        self.detail_box = ctk.CTkTextbox(
            self, height=100, font=("Cascadia Code", 11), fg_color=SURFACE,
            corner_radius=8, border_width=1, border_color="#45475A",
            text_color="#F38BA8", state="disabled",
        )
        self.toggle_btn = ctk.CTkButton(
            self, text="▶ Show details", font=("Segoe UI", 11), width=110, height=24,
            fg_color="transparent", hover_color="#363649", text_color=TEXT_DIM,
            corner_radius=6, command=self._toggle_details,
        )

    def set_downloading(self) -> None:
        self.status_dot.configure(text_color=ACCENT)
        self.status_label.configure(text="downloading…", text_color=ACCENT)

    def set_done(self) -> None:
        self.status_dot.configure(text_color=SUCCESS)
        self.status_label.configure(text="done ✓", text_color=SUCCESS)

    def set_failed(self, code: str, description: str, full_output: str) -> None:
        self.status_dot.configure(text_color=ERROR)
        self.status_label.configure(text="failed ✗", text_color=ERROR)
        self.error_summary.configure(text=f"  [{code}]  {description}")
        self.error_summary.grid(row=1, column=0, columnspan=3, padx=14, pady=(0, 2), sticky="w")
        self.toggle_btn.grid(row=2, column=0, columnspan=3, padx=14, pady=(0, 8), sticky="w")
        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", full_output.strip())
        self.detail_box.configure(state="disabled")

    def _toggle_details(self) -> None:
        if self._expanded:
            self.detail_box.grid_forget()
            self.toggle_btn.configure(text="▶ Show details")
        else:
            self.detail_box.grid(row=3, column=0, columnspan=3, padx=14, pady=(0, 10), sticky="ew")
            self.toggle_btn.configure(text="▼ Hide details")
        self._expanded = not self._expanded


# ── Main window ───────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("ARI's Youtube Songs Downloader")
        self.geometry("760x780")
        self.minsize(580, 550)
        self.configure(fg_color=SURFACE)

        self._downloading = False
        self._link_rows: list[LinkRow] = []
        self._result_cards: list[ResultCard] = []
        self._build_ui()
        self._set_icon()
        # Start with 3 empty link fields
        for _ in range(3):
            self._add_link_row()

    def _set_icon(self) -> None:
        icon_path = _app_dir() / "installer" / "icon.ico"
        if not icon_path.is_file():
            icon_path = _app_dir() / "icon.ico"
        if icon_path.is_file():
            self.iconbitmap(str(icon_path))

    def _build_ui(self) -> None:
        # ── Header with icon ─────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 0))

        ctk.CTkLabel(
            header, text="ARI", font=("Segoe UI Bold", 32), text_color=ACCENT,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            header, text="ARI's Youtube Songs Downloader",
            font=("Segoe UI Semibold", 22), text_color=TEXT,
        ).pack(side="left")

        ctk.CTkLabel(
            header, text="yt-dlp",
            font=("Segoe UI", 12), text_color=TEXT_DIM,
        ).pack(side="right", pady=(8, 0))

        # ── Links section ────────────────────────────────────────────
        links_header = ctk.CTkFrame(self, fg_color="transparent")
        links_header.pack(fill="x", padx=28, pady=(18, 0))

        ctk.CTkLabel(
            links_header, text="Paste your links",
            font=("Segoe UI Semibold", 15), text_color=TEXT,
        ).pack(side="left")

        self.add_btn = ctk.CTkButton(
            links_header, text="+ Add link", font=("Segoe UI", 13),
            width=100, height=32, fg_color=SURFACE_ALT, hover_color="#363649",
            text_color=ACCENT, corner_radius=8, command=self._add_link_row,
        )
        self.add_btn.pack(side="right")

        # Scrollable area for link inputs
        self.links_frame = ctk.CTkScrollableFrame(
            self, fg_color=SURFACE_ALT, corner_radius=CARD_RADIUS, height=180,
        )
        self.links_frame.pack(fill="x", padx=28, pady=(8, 0))

        # ── Options bar ──────────────────────────────────────────────
        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(fill="x", padx=28, pady=(14, 0))
        opts.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            opts, text="Save to:", font=("Segoe UI", 13), text_color=TEXT_DIM,
        ).grid(row=0, column=0, sticky="w")

        default_out = str(Path.home() / "Downloads" / "VideoDownloader")
        self.out_var = ctk.StringVar(value=default_out)
        ctk.CTkEntry(
            opts, textvariable=self.out_var, font=("Segoe UI", 13),
            fg_color=SURFACE_ALT, border_color="#313244", text_color=TEXT,
            corner_radius=8,
        ).grid(row=0, column=1, padx=8, sticky="ew")

        ctk.CTkButton(
            opts, text="Browse", width=80, font=("Segoe UI", 13),
            fg_color=SURFACE_ALT, hover_color="#363649", corner_radius=8,
            command=self._browse,
        ).grid(row=0, column=2)

        self.audio_only_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            opts, text="Audio only (MP3)", font=("Segoe UI", 13),
            text_color=TEXT_DIM, variable=self.audio_only_var,
            progress_color=ACCENT,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.playlist_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            opts, text="Download full playlists", font=("Segoe UI", 13),
            text_color=TEXT_DIM, variable=self.playlist_var,
            progress_color=ACCENT,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # ── Action buttons ───────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=28, pady=(18, 0))

        self.dl_btn = ctk.CTkButton(
            btn_row, text="⬇  Download All",
            font=("Segoe UI Semibold", 15), height=44, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            command=self._start_download,
        )
        self.dl_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.clear_btn = ctk.CTkButton(
            btn_row, text="Clear All", font=("Segoe UI", 14),
            height=44, width=100, corner_radius=10,
            fg_color=SURFACE_ALT, hover_color="#363649",
            command=self._clear,
        )
        self.clear_btn.pack(side="right")

        # ── Progress ─────────────────────────────────────────────────
        self.progress = ctk.CTkProgressBar(
            self, height=6, corner_radius=3,
            fg_color="#313244", progress_color=ACCENT,
        )
        self.progress.pack(fill="x", padx=28, pady=(16, 0))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            self, text="Ready", font=("Segoe UI", 12), text_color=TEXT_DIM,
        )
        self.status_label.pack(anchor="w", padx=30, pady=(4, 0))

        # ── Results list ─────────────────────────────────────────────
        self.results_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
        )
        self.results_frame.pack(fill="both", expand=True, padx=28, pady=(8, 20))

    # ── link row management ───────────────────────────────────────────
    def _add_link_row(self) -> None:
        idx = len(self._link_rows) + 1
        row = LinkRow(self.links_frame, idx, self._remove_link_row)
        row.pack(fill="x", padx=10, pady=4)
        self._link_rows.append(row)

    def _remove_link_row(self, row: LinkRow) -> None:
        if len(self._link_rows) <= 1:
            return  # keep at least one
        self._link_rows.remove(row)
        row.destroy()
        for i, r in enumerate(self._link_rows, 1):
            r.set_number(i)

    def _collect_urls(self) -> list[str]:
        urls: list[str] = []
        for row in self._link_rows:
            text = row.get_url()
            if not text:
                continue
            url = extract_url(text)
            if url:
                urls.append(url)
        return urls

    # ── callbacks ─────────────────────────────────────────────────────
    def _browse(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.out_var.set(path)

    def _clear(self) -> None:
        if self._downloading:
            return
        for r in self._link_rows:
            r.destroy()
        self._link_rows.clear()
        for c in self._result_cards:
            c.destroy()
        self._result_cards.clear()
        self.progress.set(0)
        self.status_label.configure(text="Ready", text_color=TEXT_DIM)
        for _ in range(3):
            self._add_link_row()

    def _start_download(self) -> None:
        if self._downloading:
            return

        yt_dlp = find_yt_dlp()
        if not yt_dlp:
            self.status_label.configure(
                text="yt-dlp not found!  Install: pip install yt-dlp", text_color=ERROR,
            )
            return

        urls = self._collect_urls()
        if not urls:
            self.status_label.configure(text="No valid URLs entered.", text_color=ERROR)
            return

        out_dir = Path(self.out_var.get()).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        for c in self._result_cards:
            c.destroy()
        self._result_cards.clear()

        for i, url in enumerate(urls, 1):
            card = ResultCard(self.results_frame, url, i)
            card.pack(fill="x", pady=3)
            self._result_cards.append(card)

        self.progress.set(0)
        self._downloading = True
        self.dl_btn.configure(state="disabled", text="Downloading…")

        threading.Thread(
            target=self._worker,
            args=(yt_dlp, urls, out_dir, self.audio_only_var.get(), self.playlist_var.get()),
            daemon=True,
        ).start()

    # ── download worker (background thread) ──────────────────────────
    def _worker(
        self, yt_dlp: str, urls: list[str], out_dir: Path, audio_only: bool, playlist: bool,
    ) -> None:
        ok = 0
        total = len(urls)

        for i, url in enumerate(urls):
            card = self._result_cards[i]
            self.after(0, card.set_downloading)
            self.after(
                0,
                lambda idx=i: self.status_label.configure(
                    text=f"Downloading {idx + 1} / {total}…", text_color=TEXT_DIM,
                ),
            )

            cmd: list[str] = [
                yt_dlp,
                "--no-check-certificates",
                "--restrict-filenames",
                "-o", str(out_dir / "%(title)s_%(id)s.%(ext)s"),
            ]
            if not playlist:
                cmd.append("--no-playlist")
            ffmpeg_dir = find_ffmpeg_dir()
            if ffmpeg_dir:
                cmd += ["--ffmpeg-location", ffmpeg_dir]
            if audio_only:
                cmd += ["-x", "--audio-format", "mp3"]
            else:
                cmd += [
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "--merge-output-format", "mp4",
                ]
            cmd.append(url)

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            output = result.stdout.decode("utf-8", errors="replace")

            if result.returncode == 0:
                ok += 1
                self.after(0, card.set_done)
            else:
                code, desc = classify_error(output, result.returncode)
                self.after(
                    0,
                    lambda c=card, co=code, d=desc, o=output: c.set_failed(co, d, o),
                )

            self.after(0, lambda p=(i + 1) / total: self.progress.set(p))

        failed = total - ok
        summary = f"Done — {ok} succeeded"
        if failed:
            summary += f", {failed} failed"
        color = SUCCESS if failed == 0 else ERROR

        def _finish() -> None:
            self.status_label.configure(text=summary, text_color=color)
            self.dl_btn.configure(state="normal", text="⬇  Download All")
            self._downloading = False

        self.after(0, _finish)

    def _open_folder(self) -> None:
        folder = self.out_var.get()
        if sys.platform == "win32":
            os.startfile(folder)


# ── Entry point ───────────────────────────────────────────────────────
def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
