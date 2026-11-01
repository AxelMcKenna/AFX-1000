"""NEW AP03 rear-approach/meter variant, copied from immutable AP02."""

import json
import shutil
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_pot.stage import closure
from hardware.cad.a12.thermal.interior_airpath.stage import sha, write

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "interior_airpath"
OUT = ROOT / "generated"
MODEL = ROOT / "model"


def require_parent():
    h = json.loads((PARENT / "handoff.json").read_text())
    if not all(sha(PARENT / p) == v for p, v in h["files_sha256"].items()):
        raise RuntimeError("Immutable AP02 source changed")
    return h


def capture():
    if MODEL.exists() or (ROOT / "capture.json").exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("NEW capture only; never recapture an existing packet")
    require_parent()
    old = json.loads((PARENT / "generated/analysis.json").read_text())
    bays = [[36, 137, 112, 188.4], [229.5, 137, 278.5, 188.4]]
    gates = [[69.75, 131.15, 90.25, 139.25], [243.75, 131.15, 264.25, 139.25]]

    def overlaps(p, b):
        return p[0] + 1.75 > b[0] and p[0] - 1.75 < b[2] and p[1] + 1.75 > b[1] and p[1] - 1.75 < b[3]

    pins = old["pins"]["kept_centres"]
    removed = [p for p in pins if any(overlaps(p, b) for b in bays + gates)]
    kept = [p for p in pins if p not in removed]
    shutil.copytree(PARENT / "model", MODEL)
    for p in MODEL.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(PARENT), str(ROOT)))
    for p, prefix in [(MODEL / "parts.scad", "eb_part_pins="),
                      (MODEL / "context/hardware/cad/a12/thermal/generated/thermal-base.scad", "thermal_pins=")]:
        s = p.read_text()
        line = next(l for l in s.splitlines() if l.startswith(prefix))
        p.write_text(s.replace(line, prefix + json.dumps(kept) + ";"))
    OUT.mkdir()
    for name in ["source-tray.scad", "nominal-frame-land.stl", "nominal-common-land.stl"]:
        shutil.copyfile(PARENT / "generated" / name, OUT / name)
    source = (PARENT / "geometry.scad").read_text()
    replacements = {
        "ap_bays=[[36,142,112,188.4],[229.5,142,278.5,188.4]];":
            "ap_bays=[[36,137,112,188.4],[229.5,137,278.5,188.4]];",
        "module ap_meter_orifices(w=6.25){for(p=ap_fans)translate([p[0]-w/2,136,-18.2])cube([w,11,10]);}":
            "module ap_meter_orifices(w=16){for(p=ap_fans)translate([p[0],142,-22])rotate([90,0,0])linear_extrude(11)translate([-w/2,0])ap_round(w,10,1);}",
        "ap_meter_orifices(10)": "ap_meter_orifices(16)",
        "141.99,-8.9": "136.99,-8.9", "141.99,-10": "136.99,-10",
        "139.5,-24.2": "134.5,-24.2", "139.49,-8.9": "134.49,-8.9",
        "141.5,-24.2": "136.5,-24.2", "141.49,-8.9": "136.49,-8.9",
        "139,-8.9": "134,-8.9", "[x,142,-10]": "[x,137,-10]",
        "[83.9,140,-15]": "[83.9,135,-15]",
        "[45.9,142.9,-10.1]": "[45.9,137.9,-10.1]",
        "[39.9,137.9,-12]": "[39.9,130.9,-12]",
    }
    for a, b in replacements.items():
        if a not in source:
            raise RuntimeError("Missing exact parent construction: " + a)
        source = source.replace(a, b)
    # Same original rounded rectangular prototype parts, only the rear wall,
    # its co-moving meter/FIP interfaces and the aperture profile change.
    (OUT / "checks.scad").write_text("include <" + str(MODEL / "ht-checks.scad") + ">\ninclude <source-tray.scad>\n" + source + "\n" + (ROOT / "extra.scad").read_text())
    for p in closure(OUT / "checks.scad"):
        if not p.is_relative_to(ROOT):
            raise RuntimeError("Uncaptured literal dependency: " + str(p))
    data = dict(revision="AP03", parent_handoff_sha256=sha(PARENT / "handoff.json"),
                parent_files=736, parent_geometry_unchanged=True,
                bay_outer_XY=bays, rear_wall_Y=[137,139],
                rear_wall_translation_Y_mm=-5, translated_meter_feedthrough_assemblies_mm=[0,-5,0],
                rounded_meter_mm=dict(width=16,height=10,radius=1,Z=[-22,-12]),
                nominal_meter_net_each_mm2=160-(4-3.141592653589793),
                nominal_meter_net_total_mm2=2*(160-(4-3.141592653589793)),
                nominal_upper_meter_to_bolt_hex_envelope_mm=.37,
                process_minimum_aperture_and_wall_webs_approved=False,
                parent_pins=918, additional_whole_removed=removed, additional_count=len(removed),
                kept_pins=kept, kept_count=len(kept), pin_removal_footprint_clearance_mm=.25,
                receiving_fan_Y_registration_mm=.3, approach_gap_nominal_mm=6.25,
                approach_gap_min_requirement_mm=5.95,
                floor_case_guard_fan_feet_thermal_lands_and_wire_poses_unchanged=True,
                actual_flow_split_verified=False, physical_qualified=False, thermal_qualified=False,
                fabrication_released=False, adopted=False)
    write(OUT / "analysis.json", data)
    files = [p for p in MODEL.rglob("*") if p.is_file()]
    files += [OUT / n for n in ["checks.scad","source-tray.scad","nominal-frame-land.stl","nominal-common-land.stl","analysis.json"]]
    files += [ROOT / "stage.py",ROOT / "extra.scad"]
    write(ROOT / "capture.json",dict(parent_handoff_sha256=sha(PARENT/"handoff.json"),
         source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files},
         modified_parent_originals=False))
    print(json.dumps(dict(additional_pins=len(removed),kept=len(kept),meter_net=data["nominal_meter_net_total_mm2"])))


if __name__ == "__main__":
    capture()
