"""Render the actual E13 power geometry and its worst modeled path, without CAD."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from hardware.fabrication.evidence_paths import recorded_path
from hardware.fabrication.rail_monitor_dc_paths import CAPTURE, NET, PLANES, REPO, sha


def render(output):
    root = REPO / CAPTURE.parent
    report_path = root / "dc-paths.json"
    report = json.loads(report_path.read_text())
    for name, digest in report["source_sha256"].items():
        if sha(recorded_path(name)) != digest:
            raise ValueError("Stale path model: "+name)
    capture = json.loads((REPO / CAPTURE).read_text())
    planes = json.loads((REPO / PLANES).read_text())
    nominal, hot = report["scenarios"]
    canvas = Image.new("RGB", (1240, 1200), "white")
    draw = ImageDraw.Draw(canvas)
    scale, left, top = 13, 100, 180
    font = ImageFont.load_default(size=17)
    title = ImageFont.load_default(size=31)
    small = ImageFont.load_default(size=13)

    def xy(point):
        return left + scale * point[0], top + scale * point[1]

    draw.text((70, 35), "E13 / 3.3 V DISTRIBUTION", fill="#172554", font=title)
    draw.text((70, 80), f"Actual routed copper; orange = worst modeled trace/barrel path to {hot['worst_pad']}", fill="#334155", font=font)
    draw.text((70, 110), "F.Cu: teal   |   In2.Cu: violet   |   Power-plane copper: pale blue", fill="#334155", font=font)
    for zone in planes["zones"]:
        if zone["net"] != NET:
            continue
        for polygon in zone["polygons"]:
            draw.polygon([xy(p) for p in polygon["outer"]], fill="#e0e7ff")
            for hole in polygon["holes"]:
                draw.polygon([xy(p) for p in hole], fill="white")
    for polygon in capture["outline"]:
        points = [xy(p) for p in polygon["outer"]]
        draw.line(points+[points[0]], fill="#334155", width=2)
    objects = {o["uuid"]: o for o in capture["objects"] if o["net"] == NET}
    for obj in objects.values():
        if obj["kind"] == "PCB_TRACK":
            layer = next(iter(obj["layers"]))
            color = "#0891b2" if layer == "F.Cu" else "#6366f1"
            draw.line([xy(obj["position_mm"]), xy(obj["end_mm"])], fill=color,
                      width=max(2, round(obj["width_mm"]*scale)))
        else:
            x, y = xy(obj["position_mm"])
            radius = 3 if obj["kind"] == "PCB_VIA" else 4
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill="#334155")
    worst = next(p for p in hot["paths"] if p["pad"] == hot["worst_pad"])
    for step in worst["steps"]:
        if step["kind"] == "track":
            draw.line([xy(step["start_mm"]), xy(step["end_mm"])], fill="#f97316", width=4)
    labels = {}
    for obj in objects.values():
        if obj["kind"] == "PAD" and (obj["ref"].startswith(("U", "J")) or f"{obj['ref']}.{obj['pin']}" == hot["worst_pad"]):
            labels.setdefault(obj["ref"], obj["position_mm"])
    for ref, position in labels.items():
        x, y = xy(position)
        box = draw.textbbox((x+8, y-18), ref, font=small)
        draw.rectangle((box[0]-2, box[1]-2, box[2]+2, box[3]+2), fill="white")
        draw.text((x+8, y-18), ref, fill="#172554", font=small)
    for tick in range(0, 81, 10):
        draw.text((left+scale*tick-6, top-25), str(tick), fill="#64748b", font=small)
    for tick in range(0, 71, 10):
        draw.text((left-35, top+scale*tick-6), str(tick), fill="#64748b", font=small)
    draw.text((70, 1120), f"Sensitivity model: {nominal['maximum_path_ohm']:.3f} ohm nominal; {hot['maximum_path_ohm']:.3f} ohm thin/hot. 20 mA is illustrative.", fill="#172554", font=font)
    draw.text((70, 1155), "Excludes finite plane/pad spreading, connectors, return paths and switching impedance.", fill="#475569", font=font)
    with output.open("xb") as stream:
        canvas.save(stream, format="PNG", optimize=True)
    receipt = output.with_suffix(".json")
    with receipt.open("x") as stream:
        json.dump(dict(source_sha256={str(report_path.relative_to(REPO)): sha(report_path),
                                      str(Path(__file__).relative_to(REPO)): sha(Path(__file__))},
                       image_sha256=sha(output), fabrication_approved=False), stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    render(parser.parse_args().output)
