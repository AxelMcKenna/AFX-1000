"""Render captured native copper into a compact, factual receiver review image."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication/staging"
CAPTURE = ROOT / "dac-receiver-closed-inputs-01/capture.json"
SOURCE = ROOT / "dac-receiver-closed-native-01"


def run():
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(Path(p)) == digest for p, digest in capture["source_sha256"].items())
    pcb = SOURCE / "dac_receiver.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    image = Image.new("RGB", (1440, 1250), "#f8fafc")
    draw = ImageDraw.Draw(image)
    scale, left, top = 15, 90, 165
    title = ImageFont.load_default(size=30)
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=14)

    def xy(p):
        return left + scale * p[0], top + scale * p[1]

    draw.text((70, 30), "E08 / DAC RECEIVER ROUTING CANDIDATE", fill="#0f172a", font=title)
    draw.text((70, 78), "60 electrical parts | 84 x 64 mm planning envelope | 4 layers", fill="#334155", font=font)
    draw.text((70, 108), "Teal: F.Cu   Violet: B.Cu shown through   Gold: lands/vias   Inner AGND fills omitted", fill="#475569", font=font)
    outline = [xy(p) for p in capture["outline"][0]["outer"]]
    draw.polygon(outline, fill="white", outline="#334155", width=2)
    for face, color in (("B.Cu", "#c4b5fd"), ("F.Cu", "#0d9488")):
        for obj in capture["objects"]:
            if obj["kind"] != "PCB_TRACK":
                continue
            for polygon in obj["layers"].get(face, []):
                draw.polygon([xy(p) for p in polygon["outer"]], fill=color)
    for obj in capture["objects"]:
        if obj["kind"] == "PCB_TRACK":
            continue
        for polygon in obj["layers"].get("F.Cu", []):
            draw.polygon([xy(p) for p in polygon["outer"]], fill="#d5a442")
        drill = obj.get("drill_mm", [0, 0])
        if obj["kind"] == "PCB_VIA":
            drill = [.3, .3]
        if any(drill):
            x, y = xy(obj["position_mm"])
            rx, ry = [d * scale / 2 for d in drill]
            draw.ellipse((x-rx, y-ry, x+rx, y+ry), fill="#f8fafc", outline="#475569")
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        pos = list(map(float, first(fp, "at")[1:3]))
        x, y = xy(pos)
        # Annotation labels use actual footprint origins, not predicted bodies.
        box = draw.textbbox((x, y), ref, font=small, anchor="mm")
        draw.rectangle((box[0]-2, box[1]-1, box[2]+2, box[3]+1), fill="white")
        draw.text((x, y), ref, fill="#0f172a", font=small, anchor="mm")
    for tick in range(0, 85, 10):
        draw.text((left + tick*scale, top-25), str(tick), fill="#475569", font=small, anchor="mm")
    for tick in range(0, 65, 10):
        draw.text((left-30, top + tick*scale), str(tick), fill="#475569", font=small, anchor="mm")
    draw.text((70, 1160), "Zero native DRC / opens / parity / ERC findings. Actual saved copper; not a manufacturing release.", fill="#0f172a", font=font)
    draw.text((70, 1194), "ESS gain, codec co-location, final housing fit, parts/process and analog qualification remain open.", fill="#475569", font=font)
    output = SOURCE / "plots/routing-review.png"
    with output.open("xb") as stream:
        image.save(stream, format="PNG", optimize=True)
    receipt = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in (CAPTURE, pcb, Path(__file__))},
                   image_sha256=sha(output), actual_native_copper_polygons=True,
                   B_Cu_shown_unmirrored_through_board=True, fabrication_released=False)
    with output.with_suffix(".json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(output)


if __name__ == "__main__":
    run()
