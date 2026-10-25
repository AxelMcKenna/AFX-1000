"""Compose native CAD renders into the README overview; no invented geometry."""

from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


def compose(folder):
    folder = Path(folder)
    background = Image.open(folder / "assembled.png").convert("RGB").getpixel((0, 0))
    result = Image.new("RGB", (3200, 2360), background)
    draw = ImageDraw.Draw(result)
    candidates = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    face = next((p for p in candidates if Path(p).exists()), None)

    def font(size):
        return (
            ImageFont.truetype(face, size)
            if face
            else ImageFont.load_default(size=size)
        )

    ink, muted = "#20272a", "#596368"
    draw.text((100, 65), "RMX / A09 mechanical design", font=font(70), fill=ink)
    draw.text(
        (103, 161),
        "334 × 157 × 38 mm chassis  /  29 guided buttons · 10 shaft-mount knobs · selectors and optics",
        font=font(31),
        fill=muted,
    )
    draw.line((100, 225, 3100, 225), fill="#cbd2d3", width=2)
    scenes = [
        (
            "assembled",
            "01  Assembled housing",
            "Printable controls, engraved keycaps, optical inserts and release lever.",
        ),
        (
            "exploded",
            "02  Integrated mechanism",
            "Actual supply PCB and individual components fit beneath the controls.",
        ),
        (
            "parts",
            "03  Print part families",
            "The 3MF and parts.csv contain the complete quantity schedule.",
        ),
        (
            "button",
            "04  Button mechanism cutaway",
            "Guided stem, retaining clip, switch carrier, spring and compliant contact.",
        ),
    ]
    for i, (name, title, caption) in enumerate(scenes):
        x, y = 100 + (i % 2) * 1550, 275 + (i // 2) * 960
        draw.text((x, y), title, font=font(43), fill=ink)
        draw.text((x, y + 65), caption, font=font(26), fill=muted)
        picture = Image.open(folder / (name + ".png")).convert("RGB")
        difference = ImageChops.difference(
            picture, Image.new("RGB", picture.size, background)
        )
        bounds = difference.convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
        if bounds:
            left, top, right, bottom = bounds
            picture = picture.crop(
                (
                    max(0, left - 35),
                    max(0, top - 35),
                    min(picture.width, right + 35),
                    min(picture.height, bottom + 35),
                )
            )
        picture = ImageOps.contain(picture, (1450, 780), Image.Resampling.LANCZOS)
        result.paste(
            picture,
            (x + (1450 - picture.width) // 2, y + 135 + (780 - picture.height) // 2),
        )
    draw.line((100, 2210, 3100, 2210), fill="#cbd2d3", width=2)
    draw.text(
        (103, 2245),
        "A09 actual supply-board integration • 0.25 mm power-reserve clearance check; physical fit and electrical completion remain open.",
        font=font(28),
        fill=muted,
    )
    draw.text(
        (103, 2290),
        "Purchased hardware is shown for context. Grey blocks are electronics reserves. Colours are illustrative; views use different scales.",
        font=font(27),
        fill=muted,
    )
    result.save(folder / "overview.png", optimize=True)
