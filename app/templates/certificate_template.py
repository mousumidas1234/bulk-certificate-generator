from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


def _register_fonts() -> tuple[str, str]:
    """Discover a system Unicode font, falling back to standard PDF fonts."""
    fc_match = shutil.which("fc-match")
    if fc_match:
        try:
            font_paths = []
            for font_query in ("DejaVu Sans", "DejaVu Sans:style=Bold"):
                result = subprocess.run(
                    [fc_match, "-f", "%{file}", font_query],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                font_path = Path(result.stdout.strip())
                if font_path.is_file():
                    font_paths.append(font_path)
            if len(font_paths) == 2:
                pdfmetrics.registerFont(TTFont("CertificateSans", str(font_paths[0])))
                pdfmetrics.registerFont(TTFont("CertificateSans-Bold", str(font_paths[1])))
                return "CertificateSans", "CertificateSans-Bold"
        except (OSError, subprocess.SubprocessError):
            pass
    return "Helvetica", "Helvetica-Bold"


REGULAR_FONT, BOLD_FONT = _register_fonts()


def _centered(canvas: Canvas, text: str, y: float, font: str, size: int) -> None:
    canvas.setFont(font, size)
    canvas.drawString((landscape(letter)[0] - stringWidth(text, font, size)) / 2, y, text)


def create_certificate_pdf(output_path: Path, recipient_name: str, event_name: str, event_date: date) -> None:
    width, height = landscape(letter)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(output_path), pagesize=(width, height))
    canvas.setTitle(f"Certificate - {recipient_name}")

    canvas.setFillColor(colors.HexColor("#F7F3E8"))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#1F4E5F"))
    canvas.setLineWidth(4)
    canvas.rect(28, 28, width - 56, height - 56, fill=0, stroke=1)
    canvas.setStrokeColor(colors.HexColor("#D4A72C"))
    canvas.setLineWidth(1)
    canvas.rect(40, 40, width - 80, height - 80, fill=0, stroke=1)
    canvas.setFillColor(colors.HexColor("#1F2937"))

    _centered(canvas, "CERTIFICATE OF PARTICIPATION", height - 150, BOLD_FONT, 27)
    _centered(canvas, "This certificate is proudly presented to", height - 205, REGULAR_FONT, 14)
    _centered(canvas, recipient_name, height - 275, BOLD_FONT, 30)
    _centered(canvas, f"for participating in {event_name}", height - 330, REGULAR_FONT, 16)
    _centered(canvas, f"Event date: {event_date.isoformat()}", height - 375, REGULAR_FONT, 13)

    canvas.setStrokeColor(colors.HexColor("#1F4E5F"))
    canvas.line(width / 2 - 90, 92, width / 2 + 90, 92)
    _centered(canvas, "Program Coordinator", 72, REGULAR_FONT, 11)
    canvas.save()
