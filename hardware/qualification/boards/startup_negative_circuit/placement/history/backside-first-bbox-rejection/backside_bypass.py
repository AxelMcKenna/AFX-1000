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
from .refine import rotate


def main():
    parts = json.loads((ROOT / "sources/components.json").read_text())
    plan = json.loads((ROOT / "generated/placement.json").read_text())
    owners = [c for c in parts if c["ref"].startswith("U") and any(p["kind"] == "power_in" and p["net"] == "AUX2V6" for p in c["pins"])]
    caps = [c for c in parts if c.get("note") == "Actual local front bypass required in PCB implementation."]
    assert len(owners) == len(caps)
    assignments = []
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
        offset = float(first(p1, "at")[1])
        # Symmetric0603 courtyard2.1x1.3; B-side orientation0 preserves pin1X.
        x, y, w, h = owner["courtyard_rect_mm"]
        cx = min(max(px - offset, x + 1.05), x + w - 1.05)
        cy = min(max(py, y + .65), y + h - .65)
        rectangle = [cx - 1.05, cy - .65, 2.1, 1.3]
        assert rectangle[0] >= x - 1e-9 and rectangle[1] >= y - 1e-9
        assert rectangle[0] + 2.1 <= x + w + 1e-9 and rectangle[1] + 1.3 <= y + h + 1e-9
        plan["placements"][cap["ref"]] = dict(side="B", rotation_deg=0,
            anchor_mm=[cx, cy], courtyard_rect_mm=rectangle)
        assignments.append(dict(ic=ic["ref"], power_pin=number, capacitor=cap["ref"],
            power_pad_world_PCB_mm=[px, py], capacitor_VCC_pad_PCB_mm=[cx + offset, cy],
            projected_pad_distance_mm=math.hypot(cx + offset - px, cy - py),
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
    (ROOT / "generated/placement.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(len(assignments), "actual AUX bypass capacitors placed behind their ICs")
    print("Maximum projected VCC-pad separation", plan["maximum_AUX_projected_pad_to_bypass_pad_mm"], "mm; actual routes pending")


if __name__ == "__main__":
    main()
