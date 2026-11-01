"""Pack the actual AUX ICs with their source-assigned local bypass capacitors."""

import json
import math
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

from .place import ROOT, dimensions, intersects, pack


def rotate(point, angle):
    x, y = point
    return {0: (x, y), 90: (y, -x), 180: (-x, -y), 270: (-y, x)}[angle]


def transformed_bbox(box, anchor, angle):
    points = [rotate((x, y), angle) for x in (box[0], box[2]) for y in (box[1], box[3])]
    xs, ys = zip(*points)
    return [min(xs) + anchor[0], min(ys) + anchor[1], max(xs) - min(xs), max(ys) - min(ys)]


def group(ic, cap, rows):
    ir, cr = rows[ic["ref"]], rows[cap["ref"]]
    library = ROOT / "sources/footprints" / (ic["footprint"].replace(":", "__") + ".kicad_mod")
    if ic["footprint"] == "Package_SO:VSSOP-8_2.3x2mm_P0.5mm":
        library = ROOT / "NF03P_Manufacturer.pretty/TI_DCU0008A.kicad_mod"
    fp = read_sexpr(library.read_text())
    power_number = next(p["number"] for p in ic["pins"] if p["kind"] == "power_in" and p["net"] == "AUX2V6")
    power = next(p for p in children(fp, "pad") if str(p[1]) == power_number)
    px, py = map(float, first(power, "at")[1:3])
    cfp = read_sexpr((ROOT / "sources/footprints" / (cap["footprint"].replace(":", "__") + ".kicad_mod")).read_text())
    cp = next(p for p in children(cfp, "pad") if str(p[1]) == "1")
    cpower = list(map(float, first(cp, "at")[1:3]))
    assert cap["pins"][0]["net"] == "AUX2V6"
    ib = ir["courtyard_bbox_mm"]
    choices = []
    for side, angle in [("top", 90), ("bottom", 270), ("left", 180), ("right", 0)]:
        cb = transformed_bbox(cr["courtyard_bbox_mm"], [0, 0], angle)
        w, h = cb[2:]
        if side in ("top", "bottom"):
            x = min(max(px - w / 2, ib[0]), ib[2] - w)
            y = ib[1] - .2 - h if side == "top" else ib[3] + .2
        else:
            x = ib[0] - .2 - w if side == "left" else ib[2] + .2
            y = min(max(py - h / 2, ib[1]), ib[3] - h)
        anchor = [x - cb[0], y - cb[1]]
        pcx, pcy = rotate(cpower, angle)
        distance = math.hypot(anchor[0] + pcx - px, anchor[1] + pcy - py)
        rectangle = [x, y, w, h]
        assert not intersects(rectangle, [ib[0], ib[1], ib[2] - ib[0], ib[3] - ib[1]])
        outer = [min(ib[0], x), min(ib[1], y), max(ib[2], x + w), max(ib[3], y + h)]
        choices.append((distance, side, angle, anchor, outer))
    distance, side, angle, anchor, outer = min(choices)
    virtual = dict(ref="GROUP_" + ic["ref"], courtyard_bbox_mm=outer,
                   courtyard_area_mm2=(outer[2] - outer[0]) * (outer[3] - outer[1]))
    return virtual, dict(ic=ic["ref"], cap=cap["ref"], cap_rotation=angle,
                         cap_anchor=anchor, cap_side=side, VCC_pad_distance_mm=distance)


def main():
    parts = json.loads((ROOT / "sources/components.json").read_text())
    rows = json.loads((ROOT / "sources/footprint-area.json").read_text())["rows"]
    by_ref = {r["ref"]: r for r in rows}
    owners = [c for c in parts if c["ref"].startswith("U") and any(p["kind"] == "power_in" and p["net"] == "AUX2V6" for p in c["pins"])]
    caps = [c for c in parts if c.get("note") == "Actual local front bypass required in PCB implementation."]
    assert len(owners) == len(caps)
    grouped, assignments = [], {}
    members = set()
    for ic, cap in zip(owners, caps):
        row, assignment = group(ic, cap, by_ref)
        grouped.append(row)
        assignments[row["ref"]] = assignment
        members.update([ic["ref"], cap["ref"]])
    combined = [r for r in rows if r["ref"] not in members] + grouped
    attempts = []
    result = None
    for n, order in enumerate([lambda r: r["courtyard_area_mm2"], lambda r: max(dimensions(r, 0)),
                               lambda r: sum(dimensions(r, 0)), lambda r: min(dimensions(r, 0))]):
        candidate, failed = pack(combined, order)
        attempts.append(dict(order=n, first_unplaced=failed))
        if candidate is not None:
            result = candidate
            break
    (ROOT / "generated/local-bypass-attempts.json").write_text(json.dumps(attempts, indent=2) + "\n")
    if result is None:
        raise SystemExit("Grouped placement did not fit; original PCB/placement unchanged")
    expanded = {}
    for row in combined:
        ref = row["ref"]
        p = result[ref]
        x, y, _, _ = p["courtyard_rect_mm"]
        angle = p["rotation_deg"]
        rb = transformed_bbox(row["courtyard_bbox_mm"], [0, 0], angle)
        anchor = [x - rb[0], y - rb[1]]
        if ref not in assignments:
            expanded[ref] = dict(rotation_deg=angle, anchor_mm=anchor, courtyard_rect_mm=p["courtyard_rect_mm"])
            continue
        a = assignments[ref]
        ca = rotate(a["cap_anchor"], angle)
        cap_anchor = [anchor[0] + ca[0], anchor[1] + ca[1]]
        cap_angle = (a["cap_rotation"] + angle) % 360
        expanded[a["ic"]] = dict(rotation_deg=angle, anchor_mm=anchor,
            courtyard_rect_mm=transformed_bbox(by_ref[a["ic"]]["courtyard_bbox_mm"], anchor, angle))
        expanded[a["cap"]] = dict(rotation_deg=cap_angle, anchor_mm=cap_anchor,
            courtyard_rect_mm=transformed_bbox(by_ref[a["cap"]]["courtyard_bbox_mm"], cap_anchor, cap_angle))
    assert set(expanded) == set(by_ref)
    boxes = [p["courtyard_rect_mm"] for p in expanded.values()]
    for i, box in enumerate(boxes):
        assert not any(intersects(box, b) for b in boxes[i + 1:])
        x, y, w, h = box
        assert x >= 2 - 1e-8 and y >= 2 - 1e-8 and x + w <= 147 + 1e-8 and y + h <= 37 + 1e-8
    history = ROOT / "history/before-local-bypass-cells"
    history.mkdir(parents=True, exist_ok=True)
    for name in ["generated/placement.json", "generated/native-pcb.json", "generated/drc.json", "negative_startup_placement.kicad_pcb"]:
        target = history / Path(name).name
        if not target.exists():
            shutil.copyfile(ROOT / name, target)
    plan = json.loads((ROOT / "generated/placement.json").read_text())
    plan["placements"] = expanded
    plan["AUX_local_bypass_assignments"] = list(assignments.values())
    plan["maximum_AUX_VCC_pad_to_bypass_pad_distance_mm"] = max(a["VCC_pad_distance_mm"] for a in assignments.values())
    (ROOT / "generated/placement.json").write_text(json.dumps(plan, indent=2) + "\n")
    print("Packed", len(expanded), "parts including", len(assignments), "local AUX bypass cells")
    print("Maximum direct VCC-to-cap pad-centre distance:", plan["maximum_AUX_VCC_pad_to_bypass_pad_distance_mm"], "mm; actual routes pending")


if __name__ == "__main__":
    main()
