"""Source-derived front/rear receiving layout review, not a fabrication drawing."""

import json

from .capture import ROOT


def build():
    from PIL import Image, ImageDraw, ImageFont

    target = ROOT / "generated/receiving-layout.png"
    if target.exists():
        raise RuntimeError("New drawing required")
    d = json.loads((ROOT / "generated/model.json").read_text())
    im = Image.new("RGB", (1200, 1060), "#f4f5f7")
    draw = ImageDraw.Draw(im)

    def font(size):
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)

    draw.text((34, 20), "NF265 + FPC91 · actual receiving layout", fill="#15253b", font=font(28))
    draw.text(
        (35, 58),
        "356 electrical parts / 358 native footprints · local failures retained · not production geometry",
        fill="#43536a",
        font=font(16),
    )
    panels = [
        ("NF265", "F", 35, 115, 7, [149, 39]),
        ("NF265", "B", 35, 440, 7, [149, 39]),
        ("FPC91", "F", 35, 785, 5, [66, 38]),
        ("FPC91", "B", 440, 785, 5, [66, 38]),
    ]
    labels = {
        "J1",
        "J2",
        "J3",
        "J4",
        "J5",
        "J6",
        "U17",
        "U22",
        "U55",
        "U58",
        "C4",
        "C5",
        "C31",
        "C32",
        "U401",
        "C401",
        "C402",
        "C403",
        "C404",
    }
    for ident, side, x, y, s, dims in panels:
        draw.text(
            (x, y - 28),
            ident + " " + ("component front" if side == "F" else "rear; same native U/V frame"),
            fill="#15253b",
            font=font(18),
        )
        draw.rectangle((x, y, x + dims[0] * s, y + dims[1] * s), fill="white", outline="#1a6863", width=2)
        for r in d["component_records"]:
            if not r["id"].startswith(ident + "_") or r["native_side"] != side:
                continue
            a, b, c, e = r["native_courtyard"]
            rect = (x + a * s, y + (dims[1] - e) * s, x + c * s, y + (dims[1] - b) * s)
            fill = "#e3e9ef"
            if r["ref"].startswith("J"):
                fill = "#bfded7"
            elif r["ref"] in {"C4", "C5", "C31", "C32", "U55", "U58"} and ident == "NF265":
                fill = "#f7c9b1"
            elif ident == "FPC91" and r["ref"] in {"U401", "R401", "J401", "C401", "C402", "C403", "C404"}:
                fill = "#d7c8e8"
            draw.rectangle(rect, fill=fill, outline="#687b90", width=1)
            if r["ref"] in labels or c - a > 9:
                draw.text((rect[0] + 2, rect[1] + 1), r["ref"], fill="#142639", font=font(10))
        for b in d["boards"]:
            if b["id"] != ident:
                continue
            for hole in b["holes"]:
                u, v, diam = hole[:3]
                qx, qy = x + u * s, y + (dims[1] - v) * s
                draw.ellipse(
                    (qx - diam * s / 2, qy - diam * s / 2, qx + diam * s / 2, qy + diam * s / 2),
                    fill="white",
                    outline="#455b73",
                )
        draw.text(
            (x, y + dims[1] * s + 5),
            f"U +X →  {dims[0]} mm     V +world Z ↑  {dims[1]} mm",
            fill="#4b5d71",
            font=font(12),
        )
    draw.text((835, 791), "Receiving scope", fill="#15253b", font=font(20))
    lines = [
        "FR4 max 1.76 mm",
        "14 named NF rear caps: 1.9 mm",
        "Other rear SMD: 1.2 mm",
        "Trim + rear solder: 1.5 mm",
        "Strain fastener rear: 2.07 mm",
        "Green: ports; orange: NF local holds",
        "Purple: seven new FPC parts",
    ]
    for i, t in enumerate(lines):
        draw.text((835, 824 + i * 23), t, fill="#43536a", font=font(14))
    draw.text(
        (35, 1020),
        "Source captured: NF 2b64a150 · FPC f8ecaee7 · no latest E28/routing/harness or thermal qualification inherited",
        fill="#43536a",
        font=font(14),
    )
    im.save(target)


if __name__ == "__main__":
    build()
