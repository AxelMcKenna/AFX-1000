"""Separate current-source U102 landing trial; never modifies T01 or canonical PCB."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
METAL = [121, 119.25, 126.7, 122.2]
TIM = [120, 118.25, 127.7, 123.2]


def main():
    import cadquery as cq

    OUT.mkdir(exist_ok=True)
    volumes = {}
    for name, box, z, height in [("LAND", METAL, 0, 5.28), ("TIM", TIM, 5.28, 1.02)]:
        x, y, xx, yy = box
        solid = (
            cq.Workplane("XY")
            .box(xx - x, yy - y, height, centered=(False, False, False))
            .translate((x + 68, y + 8, z))
        )
        assert solid.val().isValid()
        cq.exporters.export(solid, str(OUT / (name + ".step")))
        cq.exporters.export(solid, str(OUT / (name + ".stl")), tolerance=0.01, angularTolerance=0.05)
        volumes[name] = solid.val().Volume()
    # Read-only source capture already contains the exact shared packet tuple.
    native, data, hashes = json.loads((ROOT / "sources/obstacles.json").read_text())
    assert native["source_sha256"]["hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"] == sha(
        ROOT / "sources/power_p03.kicad_pcb"
    )
    boxes = [r[:] for r in native["boxes"]]
    cylinders = [r[:] for r in native["cylinders"]]
    for r in boxes:
        r[3] -= 0.2
        r[6] += 0.4
    for r in cylinders:
        r[3] -= 0.2
        r[5] += 0.4
    source = """include <../../../../positive_links/generated/collisions.scad>
positive_part="u102only";
trial="geometry";
module candidate(){import("LAND.stl");import("TIM.stl");}
module volume_above_seating(){intersection(){candidate();translate([0,0,.00001])cube([334,157,40]);}}
module window(){translate([187.8,126.05,-.01])cube([8.1,5.35,2.82]);}
module components(){
"""
    source += "for(b=" + json.dumps(boxes) + ")translate([b[1],b[2],b[3]])cube([b[4],b[5],b[6]]);\n"
    source += (
        "for(c=" + json.dumps(cylinders) + ")translate([c[1],c[2],c[3]])cylinder(d=c[4],h=c[5],$fn=128);}\n"
    )
    source += """if(trial=="geometry")candidate();
if(trial=="component_collision")intersection(){candidate();components();}
if(trial=="link_collision")intersection(){candidate();positive_hardware();return_assembly();}
if(trial=="case_collision")intersection(){volume_above_seating();union(){difference(){retained_thermal_shell();window();}thermal_controls();lower_shell_fasteners();thermal_metal_base();}}
if(trial=="positive_control")intersection(){candidate();translate([190,128,4])cube([.2,.2,.2]);}
"""
    # The link case must intersect with a UNION of both assemblies.
    source = source.replace(
        "intersection(){candidate();positive_hardware();return_assembly();}",
        "intersection(){candidate();union(){positive_hardware();return_assembly();}}",
    )
    (OUT / "checks.scad").write_text(source)
    report = dict(
        revision="U102-local-current-source-baseline",
        metal_native_mm=METAL,
        tim_native_mm=TIM,
        native_to_housing_translation_mm=[68, 8],
        metal_top_z=5.28,
        tim_collision_top_z=6.3,
        tim_collision_top_basis="Lowest matched PCBbottom plane. Other heights follow PCB/shim assembly; no rigid1.02mm received-pad claim.",
        candidate_floor_window_housing_mm=[187.8, 126.05, 195.9, 131.4],
        volumes_mm3=volumes,
        source_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in [
                ROOT / "baseline.py",
                ROOT / "sources/obstacles.json",
                ROOT / "sources/power_p03.kicad_pcb",
            ]
        },
        reference_shared_source_sha256=hashes,
        base_modified=False,
        pcb_modified=False,
        physical_fit_verified=False,
        thermal_path_qualified=False,
        pressure_support_validated=False,
        fabrication_released=False,
    )
    (OUT / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
