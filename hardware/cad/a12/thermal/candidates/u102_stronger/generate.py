"""Compose an immutable actual-body packet with the real insulated U102 LAND/TIM."""

import argparse
import copy
import json
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr

from .synthesize import METAL, ROOT, TIM

OUT = ROOT / "generated"
CAPTURED = ROOT.parent / "u10/sources/context"
CASES = [
    "geometry",
    "component_collision",
    "link_collision",
    "case_collision",
    "positive_control",
    "source_front_witness",
    "J106_tail_witness",
]


def main():
    import cadquery as cq

    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb-folder", type=Path, default=ROOT / "closed")
    args = parser.parse_args()
    folder = args.pcb_folder.resolve()
    pcb = folder / "power_p03.kicad_pcb"
    parts_path = folder / "components.json"
    body = ROOT / "sources/current-body"
    frame = json.loads((body / "analysis.json").read_text())
    capture = json.loads((body / "capture.json").read_text())
    native = frame["native_packet"]
    other = json.loads((body / "other.json").read_text())
    parts = {r["ref"]: r for r in json.loads(parts_path.read_text())}
    tree = read_sexpr(pcb.read_text())
    fps = {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }
    records = [r for r in native["component_records"] if r["board"] == "P03"]
    assert {r["ref"] for r in records} == set(parts), (
        "Actual body packet needs renewal for selected part count"
    )
    for record in records:
        ref = record["ref"]
        fp = fps[ref]
        assert record["actual_footprint"] == str(fp[1]) == parts[ref]["footprint"]
        assert record["part"] == parts[ref]["part"], "Selected MPN body envelope must be renewed"
        assert record["face"] == first(fp, "layer")[1][0], "Actual PCB face changed; renew body packet"
        assert next(p[2] for p in children(fp, "property") if p[1] == "Value") == parts[ref]["part"]
    if frame["candidate_pcb_sha256"] != sha(pcb):
        # Only identical footprint+terminal geometry can reuse a body packet after routing.
        from hardware.cad.a12.thermal.candidates.u10.candidate import geometry_inventory

        old = ROOT / "sources/native/power_p03.kicad_pcb"
        assert sha(old) == frame["candidate_pcb_sha256"]
        assert (
            geometry_inventory(read_sexpr(old.read_text()))["footprints"]
            == geometry_inventory(tree)["footprints"]
        )
    for ref, required in [("C106", 2.9), ("C113", 1.6), ("C110", 1.0)]:
        if ref in parts and (ref == "C113" or first(fps[ref], "layer")[1] == "F.Cu"):
            row = next(r for r in records if r["ref"] == ref)
            assert row["maximum_projection_allocation_mm"] >= required, (
                "Selected cap maximum projection was clipped"
            )
    proof = capture["immutable_physical_SCAD_proof"]
    assert all(sha(REPO / p) == h for p, h in proof.items()), "Captured physical context changed"
    OUT.mkdir(exist_ok=True)
    (OUT / "obstacles.json").write_text(
        json.dumps(dict(native=native, other=other, body_capture=capture), indent=2) + "\n"
    )
    volumes = {}
    for name, box, z, h in [("LAND", METAL, 0, 5.28), ("TIM", TIM, 5.28, 1.02)]:
        x, y, xx, yy = box
        solid = (
            cq.Workplane("XY")
            .box(xx - x, yy - y, h, centered=(False, False, False))
            .translate((x + 68, y + 8, z))
        )
        assert solid.val().isValid()
        cq.exporters.export(solid, str(OUT / (name + ".step")))
        cq.exporters.export(solid, str(OUT / (name + ".stl")), tolerance=0.01, angularTolerance=0.05)
        volumes[name] = solid.val().Volume()
    boxes = copy.deepcopy(native["boxes"])
    cylinders = copy.deepcopy(native["cylinders"])
    for row in boxes:
        row[3] -= 0.2
        row[6] += 0.4
    for row in cylinders:
        row[3] -= 0.2
        row[5] += 0.4
    others = [r for r in other["envelopes"] if not r[0].startswith("disconnect_")] + other["port_envelopes"]
    scad = """include <../../u10/sources/context/hardware/cad/a12/thermal-integration.scad>
trial="geometry";
module candidate(){import("LAND.stl");import("TIM.stl");}
module window(){translate([188.55,124.3,-.01])cube([9.4,7.4,2.82]);}
module components(){
"""
    scad += "for(b=" + json.dumps(boxes + others) + ")translate([b[1],b[2],b[3]])cube([b[4],b[5],b[6]]);\n"
    scad += (
        "for(b="
        + json.dumps([b for b in other["boards"] if b[0] != "disconnect_carrier"])
        + ")board_reserve(b);\n"
    )
    for board in native["boards"]:
        if board["id"] == "P03":
            continue
        scad += (
            "translate("
            + json.dumps([board["datum"][0], board["datum"][1], board["datum"][2] - 0.2])
            + ")linear_extrude("
            + str(board["thickness_range_allocation_mm"][1] + 0.4)
            + ")polygon("
            + json.dumps(board["outline_relative_mm"])
            + ");\n"
        )
    scad += (
        "for(c=" + json.dumps(cylinders) + ")translate([c[1],c[2],c[3]])cylinder(d=c[4],h=c[5],$fn=128);}\n"
    )
    scad += """module links(){import("../../u10/sources/context/hardware/cad/a12/positive_links/generated/positive-links.stl");return_assembly();}
module modified_case(){difference(){retained_thermal_shell();window();}thermal_controls();lower_shell_fasteners();thermal_metal_base();}
if(trial=="geometry")candidate();
if(trial=="component_collision")intersection(){candidate();components();}
if(trial=="link_collision")intersection(){candidate();links();}
if(trial=="case_collision")intersection(){intersection(){candidate();translate([0,0,.00001])cube([334,157,40]);}modified_case();}
if(trial=="positive_control")intersection(){candidate();translate([193,127,4])cube([.2,.2,.2]);}
if(trial=="source_front_witness")intersection(){components();translate([194.25,128,8.3])cube([.2,.2,.2]);}
if(trial=="J106_tail_witness")intersection(){components();translate([187,129.5,5.2])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    paths = [
        Path(__file__).resolve(),
        pcb,
        parts_path,
        folder / "construction.json",
        body / "analysis.json",
        body / "capture.json",
        body / "components.scad",
        body / "other.json",
        REPO / "hardware/electronics/common/sexpr.py",
    ]
    (OUT / "geometry.json").write_text(
        json.dumps(
            dict(
                revision="U102-actual-current-body-thermal-envelope",
                candidate_pcb_sha256=sha(pcb),
                selected_pcb_folder=str(folder.relative_to(REPO)),
                source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
                reference_shared_source_sha256=proof,
                actual_component_count=len(native["component_records"]),
                metal_native_mm=METAL,
                tim_native_mm=TIM,
                volumes_mm3=volumes,
                proposed_floor_window_housing_mm=[188.55, 124.3, 197.95, 131.7],
                metal_top_z=5.28,
                tim_collision_top_z=6.3,
                nominal_J106_tail_gap_mm=0.35,
                physical_fit_verified=False,
                thermal_path_qualified=False,
                fabrication_released=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
