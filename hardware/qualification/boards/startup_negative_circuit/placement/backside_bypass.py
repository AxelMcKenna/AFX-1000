"""Place source-assigned AUX bypasses behind their actual IC power pins.

The selected0603 maximum0.95mm body fits the proposed1mm rear assembly envelope.
This is still a receiving stack requirement, not an installed fit or PDN pass.
"""

import json
import math
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

from .place import ROOT, intersects
from .refine import rotate, transformed_bbox


def main():
    parts = json.loads((ROOT / "sources/components.json").read_text())
    plan = json.loads((ROOT / "generated/placement.json").read_text())
    inventory = {r["ref"]: r for r in json.loads((ROOT / "sources/footprint-area.json").read_text())["rows"]}
    owners = [c for c in parts if c["ref"].startswith("U") and any(p["kind"] == "power_in" and p["net"] == "AUX2V6" for p in c["pins"])]
    caps = [c for c in parts if c.get("note") == "Actual local front bypass required in PCB implementation."]
    assert len(owners) == len(caps)
    assignments = []
    placed_boxes = []
    for ic, cap in zip(owners, caps):
        assert cap["footprint"] == "Capacitor_SMD:C_0603_1608Metric"
        assert cap["pins"][0]["net"] == "AUX2V6" and cap["pins"][1]["net"] == "AGND"
        library = ROOT / "sources/footprints" / (ic["footprint"].replace(":", "__") + ".kicad_mod")
        if ic["footprint"] == "Package_SO:VSSOP-8_2.3x2mm_P0.5mm":
            library = ROOT / "NF03P_Manufacturer.pretty/TI_DCU0008A.kicad_mod"
        fp = read_sexpr(library.read_text())
        number = next(p["number"] for p in ic["pins"] if p["kind"] == "power_in" and p["net"] == "AUX2V6")
        power = next(p for p in children(fp, "pad") if str(p[1]) == number)
        local = tuple(map(float, first(power, "at")[1:3]))
        owner = plan["placements"][ic["ref"]]
        dx, dy = rotate(local, owner["rotation_deg"])
        px, py = owner["anchor_mm"][0] + dx, owner["anchor_mm"][1] + dy
        capfp = read_sexpr((ROOT / "sources/footprints" / (cap["footprint"].replace(":", "__") + ".kicad_mod")).read_text())
        p1 = next(p for p in children(capfp, "pad") if str(p[1]) == "1")
        pad_local = tuple(map(float, first(p1, "at")[1:3]))
        assert pad_local[1] == 0  # Bottom-side mirror leaves this pinY unchanged.
        x, y, w, h = owner["courtyard_rect_mm"]
        choices = []
        for angle in [0, 90]:
            cb = transformed_bbox(inventory[cap["ref"]]["courtyard_bbox_mm"], [0, 0], angle)
            ox, oy = rotate(pad_local, angle)
            left, bottom = max(2, x - .1), max(2, y - .1)
            right, top = min(147, x + w + .1), min(37, y + h + .1)
            if cb[2] > right - left + 1e-9 or cb[3] > top - bottom + 1e-9:
                continue
            for desired_x, desired_y in [(px - ox, py - oy), (x + w / 2, y + h / 2)]:
                cx = min(max(desired_x, left - cb[0]), right - cb[0] - cb[2])
                cy = min(max(desired_y, bottom - cb[1]), top - cb[1] - cb[3])
                rectangle = [cx + cb[0], cy + cb[1], cb[2], cb[3]]
                if not any(intersects(rectangle, old) for old in placed_boxes):
                    choices.append((math.hypot(cx + ox - px, cy + oy - py), angle, cx, cy, cb, ox, oy))
        assert choices, (ic["ref"], cap["ref"], "No contained actual courtyard")
        distance, angle, cx, cy, cb, ox, oy = min(choices)
        rectangle = [cx + cb[0], cy + cb[1], cb[2], cb[3]]
        assert rectangle[0] >= x - .1 - 1e-9 and rectangle[1] >= y - .1 - 1e-9
        assert rectangle[0] + rectangle[2] <= x + w + .1 + 1e-9 and rectangle[1] + rectangle[3] <= y + h + .1 + 1e-9
        placed_boxes.append(rectangle)
        plan["placements"][cap["ref"]] = dict(side="B", rotation_deg=angle,
            anchor_mm=[cx, cy], courtyard_rect_mm=rectangle)
        assignments.append(dict(ic=ic["ref"], power_pin=number, capacitor=cap["ref"],
            power_pad_world_PCB_mm=[px, py], capacitor_VCC_pad_PCB_mm=[cx + ox, cy + oy],
            projected_pad_distance_mm=distance,
            actual_copper_route_and_via_inductance_verified=False))
    for side in ["F", "B"]:
        boxes = [p["courtyard_rect_mm"] for p in plan["placements"].values() if p.get("side", "F") == side]
        for i, box in enumerate(boxes):
            assert not any(intersects(box, b) for b in boxes[i + 1:]), side
    history = ROOT / "history/before-backside-bypass"
    history.mkdir(parents=True, exist_ok=True)
    for name in ["generated/placement.json", "generated/native-pcb.json", "generated/drc.json", "negative_startup_placement.kicad_pcb"]:
        target = history / Path(name).name
        if not target.exists():
            shutil.copyfile(ROOT / name, target)
    plan["AUX_backside_bypass_assignments"] = assignments
    plan["maximum_AUX_projected_pad_to_bypass_pad_mm"] = max(a["projected_pad_distance_mm"] for a in assignments)
    plan["backside_bypass_body_max_receiving_mm"] = .95
    plan["backside_assembled_height_receiving_mm"] = 1.0
    plan["backside_cap_courtyard_may_extend_beyond_front_owner_courtyard_mm"] = .1
    plan["pending_backside_bypass_refs"] = []
    (ROOT / "generated/placement.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(len(assignments), "actual AUX bypass capacitors placed behind their ICs")
    print("Maximum projected VCC-pad separation", plan["maximum_AUX_projected_pad_to_bypass_pad_mm"], "mm; actual routes pending")


if __name__ == "__main__":
    main()
