"""Generate an ARI logo .ico for ARI's Youtube Songs Downloader."""

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont


def generate_icon(out: Path) -> None:
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded square
    pad = 10
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=48, fill="#6C5CE7",
    )

    # Inner subtle border
    inner = 18
    draw.rounded_rectangle(
        [inner, inner, size - inner, size - inner],
        radius=40, fill=None, outline="#5A4BD1", width=3,
    )

    # Draw "ARI" text centered
    # Try system fonts, fall back to default
    font = None
    font_size = 100
    for name in ["arialbd.ttf", "Arial Bold.ttf", "Impact.ttf", "segoeui.ttf"]:
        try:
            font = ImageFont.truetype(name, font_size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    text = "ARI"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1] - 8
    draw.text((tx, ty), text, fill="white", font=font)

    # Small down-arrow below the text
    cx = size // 2
    arrow_top = ty + th + 10
    arrow_w = 24
    arrow_h = 16
    draw.polygon(
        [(cx - arrow_w, arrow_top), (cx + arrow_w, arrow_top), (cx, arrow_top + arrow_h)],
        fill="#CDD6F4",
    )

    # Save as .ico with multiple sizes
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [img.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[0].save(str(out), format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[1:])
    print(f"Icon saved: {out}")


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent / "installer" / "icon.ico"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    generate_icon(out_path)
