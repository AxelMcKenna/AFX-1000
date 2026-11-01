"""Private J8 receiving-gauge study; the gauge is NOT manufacturer part CAD.

The dimensioned Phoenix drawing leaves the crimp envelope unspecified. This
study asks whether an explicitly inspectable maximum envelope could fit; it
does not establish that any delivered or crimped lug satisfies that envelope.
No PCB, BOM, other agent's CAD, or sealed predecessor is changed.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from hardware.cad.a12.repaired import packet
from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
OUT = ROOT / "generated/direct-j8-gauge-study"
U14 = ROOT / "generated/p9-u14-input-escape-work"
PCB_SHA = "28c86cea474e46e9b857c11c059f304b8e61f46444d87b8aabcfc50f2b81c945"
PDF = Path("/private/tmp/afx-e28-lug-review/phoenix3240070-allied.pdf")
PDF_SHA = "298dfeae7e889b60ebda6a0f73a22e4d1c8088fc0e80fec8865d1b0492276f9e"
CASES = (
    "gauge", "electronics_collision", "positive_hardware_collision",
    "other_returns_collision", "own_bar_solid_interference",
    "washer_head_barrel_collision", "screw_bore_collision",
    "positive_control", "oversize_barrel_negative_control",
)
COLLISIONS = CASES[1:7]
CONTROLS = CASES[7:]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirements():
    return dict(
        identity="PROJECT RECEIVING GAUGE ONLY: not Phoenix guaranteed dimensions",
        selected_part_candidate="Phoenix Contact 3240070 C-RC 1/M3 DIN",
        drawing_nominal_mm=dict(a=6, b=14, c=5, d=1.6, e=6, f=3.2, g=0.8),
        drawing_does_not_bound_post_crimp_body=True,
        all_limits_below_are_unaccepted_incoming_and_assembly_requirements=True,
        ring_width_max_mm=6.3,
        ring_bore_min_mm=3.1,
        flat_stock_min_mm=0.8,
        flat_stock_max_mm=1.0,
        flat_underside_may_not_project_below_contact_plane=True,
        transition_and_barrel_outer_body_x_min_mm=5.5,
        transition_and_barrel_outer_body_x_max_mm=11.3,
        transition_and_barrel_outer_body_width_max_mm=5.0,
        transition_and_barrel_outer_body_height_max_mm=5.0,
        flat_tongue_envelope_end_mm=6.3,
        uninsulated_crimp_requires_separate_insulation_and_strain_relief=True,
        wire_bore_exit_center_and_new_full_wire_path_not_defined=True,
        combined_relative_position_allocation_xy_and_z_mm=0.65,
        free_neighbor_clearance_mm=0.25,
        free_neighbor_gauge_inflation_per_axis_mm=0.9,
        intended_contact="Whole lug lower receiving plane seats on existing DIG bar upper plane",
        independent_float_not_applied_twice_to_intended_bolted_contact=True,
        bar_lug_contact_geometry_does_not_establish_contact_resistance=True,
        physical_fit_verified=False,
        electrical_joint_qualified=False,
        manufacturer_drawing_and_process_accepted=False,
    )


def capture(angle):
    assert sha(U14 / "rail_disconnect.kicad_pcb") == PCB_SHA
    assert sha(PDF) == PDF_SHA
    OUT.mkdir(exist_ok=True)
    native = packet({"E28": U14})
    (OUT / "actual-components.json").write_text(json.dumps(native, indent=2) + "\n")
    source_hashes = dict(native["source_sha256"])
    source_hashes[str(Path(__file__).relative_to(REPO))] = sha(Path(__file__))
    assets = OUT / "native-inputs"
    assets.mkdir(exist_ok=True)
    returns = REPO / "hardware/cad/a12/returns/generated"
    positive = REPO / "hardware/cad/a12/positive_links/generated"
    # These are newly checked solids, not inherited acceptance receipts.
    inputs = [returns / ("AFX-A12-R01-" + n + ".stl") for n in (
        "ANA-BAR", "DIG-BAR", "ANA-POST", "DIG-POST", "ANA-CAP", "DIG-CAP",
        "ANA-BASE-SCREW", "DIG-BASE-SCREW", "ANA-CAP-SCREW0", "ANA-CAP-SCREW1",
        "DIG-CAP-SCREW0", "DIG-CAP-SCREW1", "ANA-END0-SCREW", "ANA-END1-SCREW",
        "ANA-END0-WASHER", "ANA-END1-WASHER", "DIG-END1-SCREW", "DIG-END1-WASHER",
    )]
    inputs += [positive / (n + ".stl") for n in (
        "ANA-COVERED-ENVELOPE", "DIG-COVERED-ENVELOPE", "SUPPORT-ENVELOPE", "BONDED-PEDESTAL",
        "ANA-FASTENER0", "ANA-FASTENER1", "DIG-FASTENER0", "DIG-FASTENER1",
    )]
    for path in inputs:
        source_hashes[str(path.relative_to(REPO))] = sha(path)
        shutil.copyfile(path, assets / path.name)
    for path in (REPO / "hardware/cad/a12/returns/design.json",
                 REPO / "hardware/cad/a12/returns/generated/geometry.json",
                 REPO / "hardware/cad/a12/positive_links/design.json"):
        source_hashes[str(path.relative_to(REPO))] = sha(path)
    design = json.loads((REPO / "hardware/cad/a12/returns/design.json").read_text())
    assert design["paths"]["DIG"]["xy"][0] == [132, 129.5]
    geometry = json.loads((returns / "geometry.json").read_text())
    assert geometry["bars"]["DIG"]["points_mm"][0] == [132, 129.5, 11.6]
    req = requirements()
    (OUT / "receiving-requirements.json").write_text(json.dumps(req, indent=2) + "\n")
    boxes = [r for r in native["boxes"] if r[0] != "E28_J8"]
    # Only the matching physical stud is removed from the generic courtyard
    # packet. Its real bar, bore and new washer/head have separate checks.
    cylinders = native["cylinders"]
    other_names = [p.name for p in inputs if p.parent == returns and "DIG-BAR" not in p.name]
    positive_names = [p.name for p in inputs if p.parent == positive]
    def imports(names):
        return "\n".join('import("native-inputs/' + n + '");' for n in names)
    source = """// Conditional receiving gauge; NOT manufacturer-maximum lug geometry.
$fn=96;
part="gauge";
angle=__ANGLE__;
module local_flat(){difference(){linear_extrude(1)hull(){circle(d=6.3);translate([5.5,-2.5])square([.8,5]);}translate([0,0,-.01])cylinder(d=3.1,h=1.02);}}
module local_barrel(extended=false){translate([5.5,-2.5,0])cube([extended?30:5.8,5,5]);}
module located(){translate([132,129.5,15.1])rotate([0,0,angle])children();}
module lug(){located(){local_flat();local_barrel();}}
module barrel(){located()local_barrel();}
module expanded(){minkowski(){children();cube([1.8,1.8,1.8],center=true);}}
module electronics(){
for(r=__BOXES__)translate([r[1],r[2],r[3]])cube([r[4],r[5],r[6]]);
for(r=__CYLINDERS__)translate([r[1],r[2],r[3]])cylinder(d=r[4],h=r[5]);
}
module positive_hardware(){__POSITIVE__}
module other_returns(){__RETURNS__}
module own_bar(){import("native-inputs/AFX-A12-R01-DIG-BAR.stl");}
// Maximum-stock example: washer/underhead sit above 1.0 mm flat tongue.
// Nominal 8 mm length is not a guaranteed minimum engagement specification.
module washer_head(){translate([132,129.5,16.1])difference(){cylinder(d=7,h=.55);translate([0,0,-.01])cylinder(d=3.2,h=.57);}translate([132,129.5,16.65])cylinder(d=6,h=2.52);}
module shaft(){translate([132,129.5,8.65])cylinder(d=3,h=8);}
if(part=="gauge")lug();
if(part=="electronics_collision")intersection(){expanded()lug();electronics();}
if(part=="positive_hardware_collision")intersection(){expanded()lug();positive_hardware();}
if(part=="other_returns_collision")intersection(){expanded()lug();other_returns();}
if(part=="own_bar_solid_interference")intersection(){lug();own_bar();}
if(part=="washer_head_barrel_collision")intersection(){minkowski(){washer_head();cube([.5,.5,.5],center=true);}barrel();}
if(part=="screw_bore_collision")intersection(){lug();shaft();}
if(part=="positive_control")intersection(){lug();located()translate([7,-.1,.1])cube([.2,.2,.2]);}
if(part=="oversize_barrel_negative_control")intersection(){located()local_barrel(true);electronics();}
"""
    for key, value in {"__ANGLE__": str(angle), "__BOXES__": json.dumps(boxes),
                       "__CYLINDERS__": json.dumps(cylinders), "__POSITIVE__": imports(positive_names),
                       "__RETURNS__": imports(other_names)}.items():
        source = source.replace(key, value)
    (OUT / "gauge.scad").write_text(source)
    metadata = dict(
        scope="NEW conditional J8 receiving-gauge fit; no inherited wire or topology acceptance",
        source_sha256=source_hashes,
        external_unmodified_manufacturer_drawing=dict(path=str(PDF), sha256=PDF_SHA),
        native_pcb_sha256=PCB_SHA,
        native_pcb_counts=dict(opens=43, hard_DRC=0, parity=0, ERC=0, warnings=66),
        source_J8_world_xy_mm=[132, 129.5],
        source_J4_positive_world_xy_mm=[161, 120.5],
        source_J4_unused_ground_pad_world_xy_mm=[161, 129.5],
        old_EI02_ground_world_xy_mm=[161, 126.5],
        lug_clock_deg=angle,
        z_contact_plane_mm=15.1,
        nominal_max_stock_head_top_z_mm=19.17,
        max_stock_min_engagement_example_mm=8-3.57-1-.55,
        screw_length_tolerance_and_usable_thread_depth_missing=True,
        requirements=req,
        copied_meshes_are_new_obstacles_not_previous_passes=True,
        PCB_BOM_other_agent_sources_changed=False,
        no_complete_wire_route_or_bore_exit_height_proof=True,
        physical_electrical_thermal_startup_PDN_fabrication_qualified=False,
    )
    (OUT / "capture.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def verify(executable):
    capture_data = json.loads((OUT / "capture.json").read_text())
    # Derived reviews and past failure archives are evidence, not solver
    # inputs. Including them would create circular freshness dependencies.
    evidence = [OUT / name for name in (
        "actual-components.json", "receiving-requirements.json", "capture.json", "gauge.scad",
    )] + sorted((OUT / "native-inputs").glob("*.stl"))
    evidence_hashes = {str(p.relative_to(REPO)): sha(p) for p in evidence}
    def stale():
        return [p for p, h in capture_data["source_sha256"].items() if sha(REPO / p) != h]
    assert not stale(), "Capture sources changed before native run"
    rows = {}
    for name in CASES:
        target = OUT / ("native-" + name + ".stl")
        target.unlink(missing_ok=True)
        command = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl",
                   "-D", 'part="' + name + '"', "-o", str(target), str(OUT / "gauge.scad")]
        run = subprocess.run(command, capture_output=True, text=True, timeout=120)
        log = run.stdout + run.stderr
        (OUT / ("native-" + name + ".log")).write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, (name, log)
        if run.returncode == 1 and "Current top level object is empty." in log:
            target.unlink(missing_ok=True)
            rows[name] = dict(result="empty", volume_mm3=0, returncode=run.returncode, command=command)
        else:
            assert run.returncode == 0 and "NoError" in log and target.exists(), (name, log)
            rows[name] = dict(result="valid native manifold", returncode=0, command=command, **binary_stl(target))
        print(name, rows[name]["volume_mm3"], flush=True)
    changed = [p for p, h in evidence_hashes.items() if sha(REPO / p) != h]
    failures = [name for name in COLLISIONS if rows[name]["volume_mm3"] > 1e-6]
    controls_pass = all(rows[name]["volume_mm3"] > 1e-6 for name in CONTROLS)
    assert rows["gauge"]["volume_mm3"] > 10
    report = dict(
        capture=capture_data, native_checks=rows,
        input_sha256=evidence_hashes, stale_sources=stale(), changed_inputs=changed,
        collision_failures=failures, both_controls_detected=controls_pass,
        conditional_receiving_gauge_screen_passed=not failures and controls_pass and not stale() and not changed,
        no_manufacturer_maximum_or_crimp_recipe_approval=True,
        physical_electrical_thermal_startup_PDN_fabrication_qualified=False,
    )
    report["native_evidence_sha256"] = {
        str(p.relative_to(REPO)): sha(p) for p in OUT.glob("native-*") if p.suffix in (".stl", ".log")
    }
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    assert not stale() and not changed
    assert controls_pass, "Actual-object negative/positive controls failed"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture", action="store_true")
    p.add_argument("--angle", type=float, default=-20)
    p.add_argument("--openscad", type=Path)
    args = p.parse_args()
    if args.capture:
        capture(args.angle)
    if args.openscad:
        verify(args.openscad)


if __name__ == "__main__":
    main()
