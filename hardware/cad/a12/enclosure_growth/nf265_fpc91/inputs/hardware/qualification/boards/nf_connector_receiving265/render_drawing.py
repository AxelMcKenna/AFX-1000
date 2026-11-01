"""Render this bounded SVG subset for visual review; reject unknown graphics."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    source = ROOT / "mechanical-v2/BREP/NC265-strain-drawing.svg"
    target = source.with_suffix(".png")
    if target.exists():
        raise RuntimeError("Fresh review image required")
    tree = ET.parse(source).getroot()
    image = Image.new("RGB", (int(tree.attrib["width"]), int(tree.attrib["height"])), "white")
    draw = ImageDraw.Draw(image)
    directory = Path(matplotlib.get_data_path()) / "fonts/ttf"
    fonts = {}
    for size, bold in [(19, False), (28, True), (16, False)]:
        fonts[(size, bold)] = ImageFont.truetype(
            str(directory / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size
        )
    for item in tree:
        name = item.tag.split("}")[-1]
        a = item.attrib
        if name == "style":
            continue
        if name == "rect":
            x, y, w, h = [float(a.get(k, 0)) for k in ["x", "y", "width", "height"]]
            draw.rectangle([x, y, x + w, y + h], fill=a.get("fill"), outline=a.get("stroke"))
        elif name == "path":
            numbers = [float(x) for x in re.findall(r"[-+]?\d+(?:\.\d+)?", a["d"])]
            if len(numbers) != 4 or not a["d"].startswith("M") or "L" not in a["d"]:
                raise ValueError("Unsupported path")
            draw.line(numbers, fill="#174e73", width=1)
        elif name == "text":
            kind = a.get("class", "")
            size = 28 if kind == "title" else 16 if kind == "small" else 19
            draw.text(
                (float(a["x"]), float(a["y"])),
                "".join(item.itertext()),
                font=fonts[(size, kind == "title")],
                fill="#142c3d",
                anchor="ls",
            )
        else:
            raise ValueError("Unknown SVG graphics: " + name)
    image.save(target)
    report = dict(
        SVG_sha256=sha(source),
        PNG_sha256=sha(target),
        source_sha256=sha(Path(__file__)),
        renderer="Bounded rect/M-L/text SVG subset; no geometry altered",
        fonts={str(p): sha(p) for p in [directory / "DejaVuSans.ttf", directory / "DejaVuSans-Bold.ttf"]},
    )
    target.with_suffix(".render.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    run()
