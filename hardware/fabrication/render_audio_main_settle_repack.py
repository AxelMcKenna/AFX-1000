"""Plot current native lands and copper after the bounded settling-supervisor rework."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_audio_main_settle_repack import OUT, check
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

REPO = Path(__file__).resolve().parents[2]


def run():
    proof = check()
    board = read_sexpr((OUT / "audio_core.kicad_pcb").read_text())
    captured = json.loads((OUT / "current-native-pads.json").read_text())
    construction = json.loads((OUT / "distribution-construction.json").read_text())
    new_tracks = {row["uuid"] for row in construction["additions"] if row["kind"] == "segment" and row["purpose"] in ("reserved_control_escape", "completed_control_connection")}
    plot_dir = OUT / "plots"
    plot_dir.mkdir(exist_ok=False)
    artifacts = {}
    font = ImageFont.load_default(size=18)
    large = ImageFont.load_default(size=25)
    small = ImageFont.load_default(size=12)
    for name, layer, mirror in (("top", "F.Cu", False), ("bottom", "B.Cu", True),
                                ("supplies", "In2.Cu", False), ("ground", "In1.Cu", False)):
        im = Image.new("RGB", (1510, 850), "#101923")
        draw = ImageDraw.Draw(im)

        def xy(point):
            x, y = map(float, point)
            return 70+9*(150-x if mirror else x), 140+9*y

        def polygon(geometry, color):
            geometries = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
            for part in geometries:
                if part.is_empty:
                    continue
                draw.polygon([xy(p) for p in part.exterior.coords], fill=color)
                for ring in part.interiors:
                    draw.polygon([xy(p) for p in ring.coords], fill="#1b2b35")

        title = layer+(" / VIEW FROM BELOW" if mirror else "")
        draw.text((60, 25), "AC04 AUDIO MAIN / "+title, fill="#e5edf4", font=large)
        draw.text((60, 67), "150 x 63 mm | 52 verified control joins | 161/161 placed rails | 200/200 grounds", fill="#c4d0dc", font=font)
        draw.text((60, 97), "Actual copper and native pad polygons. Cyan: new control traces. Amber: other copper/lands.", fill="#c4d0dc", font=font)
        draw.rectangle((70, 140, 1420, 707), fill="#1b2b35", outline="#d0d9df", width=2)
        for zone in children(board, "zone"):
            for fill in children(zone, "filled_polygon"):
                if first(fill, "layer")[1] == layer:
                    points = [tuple(map(float, p[1:3])) for p in children(first(fill, "pts"), "xy")]
                    polygon(Polygon(points).buffer(0), "#3f927b")
        for track in children(board, "segment"):
            if first(track, "layer")[1] == layer:
                points = [xy(first(track, k)[1:3]) for k in ("start", "end")]
                color = "#7ed7f1" if first(track, "uuid")[1] in new_tracks else "#dc9c59"
                draw.line(points, fill=color, width=max(1, round(9*float(first(track, "width")[1]))))
        for obj in captured["objects"]:
            if obj["kind"] == "PAD" and obj["layers"].get(layer):
                polygon(shape(obj["layers"][layer]), "#75bba6" if obj["net"] == "AGND" else "#d9ad62")
            if obj.get("npth") or obj["kind"] == "PAD" and any(obj.get("drill_mm", [])):
                x, y = xy(obj["position_mm"])
                radius = max(obj["drill_mm"])*4.5
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill="#0b1118")
        for via in children(board, "via"):
            x, y = xy(first(via, "at")[1:3])
            for key, color in (("size", "#d9ad62"), ("drill", "#0b1118")):
                radius = float(first(via, key)[1])*4.5
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
        # The empty allocation is deliberately visible; no generic codec land
        # or guessed package dimensions are drawn as approved geometry.
        plan = json.loads((OUT / "plan.json").read_text())
        left, top, right, bottom = plan["codec_missing_land_reserve_mm"]
        a, b = xy((left, top)), xy((right, bottom))
        box = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        draw.rectangle(box, fill="#472c34", outline="#f49b95", width=2)
        draw.multiline_text(((box[0]+box[2])/2, (box[1]+box[3])/2), "U201\nUNPLACED\nLAND DATA HOLD",
                            fill="#f8c0b8", font=small, anchor="mm", align="center")
        for tick in range(0, 151, 10):
            x, y = xy((tick, 0))
            draw.text((x, y-18), str(tick), font=small, fill="#b9c7d2", anchor="mm")
        draw.text((60, 737), "Native geometry: 0 | ERC: 0 | Parity: 1 missing codec | Opens: "+str(proof["uncapped_open_connections"]),
                  fill="#c4d0dc", font=font)
        draw.text((60, 775), "Retained analog copper and amplifier positions. Settling supervisor, capacitors and pull-up relocated; receiving rechecked.", fill="#c4d0dc", font=font)
        draw.text((60, 812), "PARTIAL ROUTING / NOT FOR ORDER. Codec land, remaining routing and installed qualification are open.", fill="#f1b6a9", font=font)
        path = plot_dir / (name+".png")
        im.save(path, optimize=True)
        artifacts[path.name] = sha(path)
    inputs = [Path(__file__), OUT / "audio_core.kicad_pcb", OUT / "current-native-pads.json", OUT / "plan.json",
              OUT / "distribution-construction.json", OUT / "routing-handoff.json"]
    (plot_dir / "render-receipt.json").write_text(json.dumps(dict(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs}, artifact_sha256=artifacts,
        images_show_actual_native_lands_tracks_vias_and_fill=True,
        CAM_mask_stencil_and_assembly_qualification_inferred=False, fabrication_released=False), indent=2)+"\n")
    print("Rendered all four actual copper layers;", proof["uncapped_open_connections"], "opens")


if __name__ == "__main__":
    run()
