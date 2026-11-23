"""Renders selected GeneratedContent into a real file (CSV/PDF/PNG) on local disk.

Storage is local for now (see backend/README.md § Export) — swapping to Cloudflare R2
later only touches this file: replace the disk write with an R2 upload and return a
signed URL instead of a local path.
"""

import csv
import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from app.models.content import GeneratedContent

EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "exports"

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_FONT_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def job_dir(clinic_id: str, job_id: str) -> Path:
    directory = EXPORTS_DIR / clinic_id / job_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def render_csv(items: list[GeneratedContent], clinic_id: str, job_id: str) -> Path:
    path = job_dir(clinic_id, job_id) / "export.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Platform", "Tone", "Topic", "Headline", "Body", "Hashtags", "Created At"])
        for item in items:
            writer.writerow(
                [
                    item.platform,
                    item.tone,
                    item.topic,
                    item.headline,
                    item.body,
                    " ".join(f"#{tag}" for tag in item.hashtags),
                    item.created_at.isoformat(),
                ]
            )
    return path


def render_pdf(items: list[GeneratedContent], clinic_id: str, job_id: str) -> Path:
    path = job_dir(clinic_id, job_id) / "export.pdf"
    width, height = LETTER
    margin = 0.75 * inch
    c = canvas.Canvas(str(path), pagesize=LETTER)

    for item in items:
        y = height - margin
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, item.headline[:90])
        y -= 20

        c.setFont("Helvetica-Oblique", 9)
        c.drawString(margin, y, f"{item.platform} · {item.tone} · {item.topic}")
        y -= 28

        c.setFont("Helvetica", 11)
        for line in simpleSplit(item.body, "Helvetica", 11, width - 2 * margin):
            if y < margin + 20:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 11)
            c.drawString(margin, y, line)
            y -= 15

        if item.hashtags:
            y -= 10
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(margin, y, " ".join(f"#{tag}" for tag in item.hashtags))

        c.showPage()

    c.save()
    return path


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _render_single_png(item: GeneratedContent, path: Path) -> None:
    size = 1080
    margin = 72
    img = Image.new("RGB", (size, size), "#0f766e")
    draw = ImageDraw.Draw(img)

    font_meta = _load_font(_FONT_CANDIDATES, 28)
    font_headline = _load_font(_FONT_BOLD_CANDIDATES, 52)
    font_body = _load_font(_FONT_CANDIDATES, 34)
    font_tags = _load_font(_FONT_CANDIDATES, 26)

    y = margin
    draw.text((margin, y), item.platform.upper(), font=font_meta, fill="#ccfbf1")
    y += 56

    for line in _wrap_text(draw, item.headline, font_headline, size - 2 * margin):
        draw.text((margin, y), line, font=font_headline, fill="#ffffff")
        y += 62

    y += 24
    for line in _wrap_text(draw, item.body, font_body, size - 2 * margin)[:10]:
        draw.text((margin, y), line, font=font_body, fill="#f0fdfa")
        y += 44

    if item.hashtags:
        tag_line = " ".join(f"#{tag}" for tag in item.hashtags)
        draw.text((margin, size - margin - 32), tag_line, font=font_tags, fill="#99f6e4")

    img.save(path, "PNG")


def render_png(items: list[GeneratedContent], clinic_id: str, job_id: str) -> Path:
    directory = job_dir(clinic_id, job_id)

    if len(items) == 1:
        path = directory / "export.png"
        _render_single_png(items[0], path)
        return path

    zip_path = directory / "export.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for index, item in enumerate(items, start=1):
            buffer = io.BytesIO()
            single_path = directory / f"_tmp_{index}.png"
            _render_single_png(item, single_path)
            zf.write(single_path, arcname=f"{index:02d}-{item.platform}.png")
            single_path.unlink()
            buffer.close()
    return zip_path


def render(fmt: str, items: list[GeneratedContent], clinic_id: str, job_id: str) -> Path:
    if fmt == "csv":
        return render_csv(items, clinic_id, job_id)
    if fmt == "pdf":
        return render_pdf(items, clinic_id, job_id)
    if fmt == "png":
        return render_png(items, clinic_id, job_id)
    raise ValueError(f"Unknown export format: {fmt}")
