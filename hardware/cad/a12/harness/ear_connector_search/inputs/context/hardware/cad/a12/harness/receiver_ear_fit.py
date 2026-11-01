"""Actual E19 ear/J13 addition checked against the current native assembly.

All original complete footprints must match the prior receiver byte-for-byte
as parsed nodes before reusing their body packet. The new material, terminal,
minimum bores and deliberately colliding witnesses are checked explicitly.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.repaired import outline, packet
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

from ..generate import REPO, sha
from .receiver_review import footprints

ROOT = Path(__file__).resolve().parent
EAR = ROOT / "proposals/processor-awg18-ear"
OUT = ROOT / "generated/receiver-ear"


def generate():
    proof_file = EAR / "generated/native.json"
    proof = json.loads(proof_file.read_text())
    pcb = EAR / "processor_carrier.kicad_pcb"
    hashes = {}
    assert proof["candidate_pcb_sha256"] == sha(pcb) and not any(proof["counts"].values())
    for key in ["source_sha256", "artifact_sha256"]:
        hashes.update(proof[key])
    drc = json.loads((EAR / "generated/drc.json").read_text())
    erc = json.loads((EAR / "generated/erc.json").read_text())
    assert all(not drc[k] for k in ["violations", "unconnected_items", "schematic_parity"])
    assert erc["sheets"] and all(not s["violations"] for s in erc["sheets"])
    old_pcb = ROOT / "proposals/processor-awg18/processor_carrier.kicad_pcb"
    old = footprints(read_sexpr(old_pcb.read_text()))
    tree = read_sexpr(pcb.read_text())
    new = footprints(tree)
    assert set(new) - set(old) == {"J13"} and not set(old) - set(new)
    assert all(new[ref] == fp for ref, fp in old.items()), "Original physical footprint changed"
    assert len([r for r in new if not r.startswith("H")]) == 77
    shape = outline(tree)
    assert set(map(tuple, shape)) == {(0, 0), (150, 0), (150, 53), (164, 53), (164, 65), (0, 65)}
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    j13 = new["J13"]
    assert first(j13, "layer")[1] == "F.Cu"
    x0, y0, x1, y1 = courtyard(j13, "F.CrtYd")
    joints = [["e19_J13", x0 - 70 - 0.5, y0 - 58 - 0.5, 8.1, x1 - x0 + 1, y1 - y0 + 1, 11.31]]
    pads = []
    for p in children(j13, "pad"):
        xy = transform(j13, first(p, "at")[1:3])
        point = [xy[0] - 70, xy[1] - 58, 8.1]
        assert float(first(p, "drill")[1]) == 2.2 and list(map(float, first(p, "size")[1:3])) == [3.4, 3.4]
        assert point == ([188, 100, 8.1] if str(p[1]) == "1" else [188, 104, 8.1])
        assert str(first(p, "net")[-1]).lstrip("/") == ("5V_DIG" if str(p[1]) == "1" else "AGND")
        pads.append(point)
        joints.append(["e19_J13_tail_" + str(p[1]), point[0] - 1.7, point[1] - 1.7, 5, 3.4, 3.4, 1.5])
    native, other, fresh = snapshot()
    hashes.update(fresh)
    physical = packet(
        {
            "P03": REPO / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined",
            "E28": REPO / "hardware/electronics/rail_disconnect/revision28/generated/r58-joint-work",
        }
    )
    native.update(physical)
    hashes.update(physical["source_sha256"])
    inherited_h4 = next(m for m in other["board_mounts"] if m[:3] == ["dsp_carrier", 176, 103])
    assert inherited_h4 == ["dsp_carrier", 176, 103, 6.5, 3.2]
    base_packet = ROOT / "generated/receiver-awg18/analysis.json"
    base = json.loads(base_packet.read_text())
    assert base["candidate_pcb_sha256"] == sha(old_pcb)
    hashes.update(base["source_sha256"])
    boxes = (
        native["boxes"] + native["switch_diagnostic_boxes"] + base["current_E19_component_packet"]["bodies"]
    )
    boxes += [b for b in other["envelopes"] if not b[0].startswith(("e19_", "disconnect_"))] + other[
        "port_envelopes"
    ]
    for p in [
        Path(__file__),
        proof_file,
        pcb,
        old_pcb,
        base_packet,
        EAR / "handoff.json",
        EAR / "generated/package-review.json",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    OUT.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(ROOT.parent / "thermal-integration.scad") + '>\ntrial="geometry";\n'
    for key, val in dict(
        joints=joints,
        pads=pads,
        boxes=boxes,
        cylinders=native["cylinders"],
        source_outline=shape,
        inherited_h4=inherited_h4,
    ).items():
        scad += key + "=" + json.dumps(val) + ";\n"
    scad += """module joint(m=0){for(b=joints)translate([b[1]-m,b[2]-m,b[3]-m])cube([b[4]+2*m,b[5]+2*m,b[6]+2*m]);}
module ear(){difference(){translate([30,42,6.5])linear_extrude(1.6)polygon(source_outline);translate([29,41,6.49])cube([151,67,1.62]);for(p=pads)translate([p[0],p[1],6.49])cylinder(d=2.2,h=1.62,$fn=128);}}
module expanded_ear(){translate([179.55,94.55,6.05])cube([14.9,12.9,2.5]);}
module subject(){expanded_ear();joint(.45);}
module electronics(){for(b=boxes)translate([b[1],b[2],b[3]-.2])cube([b[4],b[5],b[6]+.4]);for(c=cylinders)translate([c[1],c[2],c[3]-.2])cylinder(d=c[4]/cos(180/128),h=c[5]+.4,$fn=128);
"""
    for b in native["boards"]:
        scad += (
            "translate("
            + json.dumps([*b["datum"][:2], b["datum"][2] - 0.2])
            + ")linear_extrude("
            + str(b["thickness_range_allocation_mm"][1] + 0.4)
            + ")polygon("
            + json.dumps(b["outline_relative_mm"])
            + ");\n"
        )
    for b in other["boards"]:
        if b[0] not in ("dsp_carrier", "disconnect_carrier"):
            scad += "board_reserve(" + json.dumps(b) + ");\n"
    scad += (
        """}
module hardware(){return_assembly();import("""
        + json.dumps(str(ROOT.parent / "positive_links/generated/positive-links.stl"))
        + """);}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
// The actual inherited H4 boss seats the existing board. Only clearance
// expansion entering that old seating interface is excluded, never new material.
module inherited_support(){intersection(){translate([inherited_h4[1],inherited_h4[2],floor_thickness])cylinder(d=mount_diameter(inherited_h4),h=inherited_h4[3]-floor_thickness);translate([30,42,-1])cube([150,65,7.5]);}}
// Two binary-STL coordinate ulps at this scale are ~0.00003 mm. A fixed
// 0.00002 mm Boolean-only guard removes the archived coplanar facet residual.
// It remains ~0.4 mm away from real added material; that is checked below.
module guarded_inherited_support(){intersection(){translate([inherited_h4[1],inherited_h4[2],floor_thickness-.00002])cylinder(d=mount_diameter(inherited_h4)+.00004,h=inherited_h4[3]-floor_thickness+.00004);translate([30,42,-1])cube([150,65,100]);}}
module nonseating_case_subject(){difference(){expanded_ear();guarded_inherited_support();}joint(.45);}
module source_PCB(){translate([30,42,6.3])difference(){linear_extrude(2)polygon(source_outline);for(p=pads)translate([p[0]-30,p[1]-42,-.01])cylinder(d=2.1,h=2.02,$fn=64);}}
module relative_wire(){for(p=pads){translate([p[0],p[1],5])cylinder(r=1.005/cos(180/64),h=6.505,$fn=64);translate([p[0],p[1],10.895])cylinder(r=1.1813/cos(180/64),h=3.305,$fn=64);}}
if(trial=="geometry"){ear();joint();}
if(trial=="ear_material")ear();
if(trial=="case_collision")intersection(){nonseating_case_subject();case_parts();}
if(trial=="nominal_case_collision")intersection(){union(){ear();joint();}case_parts();}
if(trial=="actual_ear_support_exclusion_collision")intersection(){ear();guarded_inherited_support();}
if(trial=="inherited_support_witness")intersection(){expanded_ear();case_parts();inherited_support();}
if(trial=="electronics_collision")intersection(){subject();electronics();}
if(trial=="hardware_collision")intersection(){subject();hardware();}
if(trial=="source_PCB_geometry")source_PCB();
if(trial=="wirefit_geometry")relative_wire();
if(trial=="source_wirefit_collision")intersection(){relative_wire();source_PCB();}
if(trial=="ear_positive_control")intersection(){ear();translate([182.9,96.9,7])cube([.2,.2,.2]);}
if(trial=="joint_positive_control")intersection(){joint();translate([187.9,99.9,8.5])cube([.2,.2,.2]);}
if(trial=="bare_positive_control")intersection(){relative_wire();translate([187.9,99.9,9])cube([.2,.2,.2]);}
if(trial=="insulated_positive_control")intersection(){relative_wire();translate([187.9,99.9,12.5])cube([.2,.2,.2]);}
"""
    )
    (OUT / "checks.scad").write_text(scad)
    expected = 14 * 12 * 1.6 - 2 * math.pi * 1.1**2 * 1.6
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        candidate_pcb_sha256=sha(pcb),
        original_complete_footprints_unchanged=len(old),
        component_count=77,
        actual_outline_relative_mm=shape,
        actual_J13_pad_centers_mm=pads,
        expected_ear_material_mm3=expected,
        expected_joint_reserve_mm3=sum(math.prod(b[4:7]) for b in joints),
        positional_and_clearance_expansion_mm=0.45,
        old_whole_PCB_excluded_only_at_intended_ear_connection=True,
        inherited_support_exclusion_only_for_clearance_expansion=True,
        inherited_support_parameters=inherited_h4,
        inherited_support_actual_diameter_function="mount_diameter(inherited_h4), inherited housing source",
        actual_new_ear_material_must_not_enter_exclusion=True,
        original_unrelieved_overlap_witness_expected_mm3=0.016364628241670214,
        intended_support_boolean_guard_mm=0.00002,
        archived_exact_support_subtraction_residual_mm3=6.54835901059414e-8,
        exact_subtraction_review_manifest="hardware/cad/a12/harness/generated/ear-H4-exact-seat-fb190888c81758c4.json",
        support_seating_flatness_and_warpage_qualified=False,
        minimum_bore_requirement_mm=2.1,
        maximum_pretinned_core_requirement_mm=1.4,
        relative_centering_allocation_mm=0.3,
        maximum_solder_tail_square_requirement_mm=3.4,
        source_native_all_findings_zero=True,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Inputchanged"
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify(executable):
    r = json.loads((OUT / "analysis.json").read_text())
    cases = {}
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [OUT / "analysis.json", OUT / "checks.scad"]}
    (OUT / "verification.json").unlink(missing_ok=True)
    for name in [
        "geometry",
        "ear_material",
        "case_collision",
        "nominal_case_collision",
        "actual_ear_support_exclusion_collision",
        "inherited_support_witness",
        "electronics_collision",
        "hardware_collision",
        "source_PCB_geometry",
        "wirefit_geometry",
        "source_wirefit_collision",
        "ear_positive_control",
        "joint_positive_control",
        "bare_positive_control",
        "insulated_positive_control",
    ]:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="ear_only"']
        cmd += ["-D", 'trial="' + name + '"', "-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(s in log for s in ["WARNING", "ERROR"])
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        if name.endswith("collision") and empty and clean:
            row = dict(clear=True, empty=True)
        elif p.returncode == 0 and target.exists() and "NoError" in log and clean:
            stats = binary_stl(target)
            ok = not name.endswith("collision") and stats["volume_mm3"] > 0.001
            if name in ("geometry", "ear_material"):
                expected = r["expected_ear_material_mm3"] + (
                    r["expected_joint_reserve_mm3"] if name == "geometry" else 0
                )
                ok = math.isclose(stats["volume_mm3"], expected, abs_tol=0.02)
            if name.endswith("positive_control"):
                ok = math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            if name == "inherited_support_witness":
                ok = math.isclose(
                    stats["volume_mm3"], r["original_unrelieved_overlap_witness_expected_mm3"], abs_tol=1e-6
                )
            row = dict(clear=ok, **stats)
        else:
            row = dict(clear=False, returncode=p.returncode)
        cases[name] = row
        print(name, row, flush=True)
    changed = [n for n, h in {**r["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        all_local_ear_checks_clear=not changed and all(c["clear"] for c in cases.values()),
        source_sha256=r["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in (".log", ".stl")
        },
        full_wire_route_verified=False,
        complete_input_distribution_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args()
    generate()
    raise SystemExit(0 if verify(args.openscad)["all_local_ear_checks_clear"] else 1)
