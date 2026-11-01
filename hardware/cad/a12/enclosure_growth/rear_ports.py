"""Private raised audio-jack row, retaining the original cassette window.

Uses the existing behind-panel class envelopes and apertures, not a selected
manufacturer jack model. Exact threads, plug/washer/nut stack, wiring and
physical fit remain unqualified. Rear DC, switch, SD and USB positions stay fixed.
"""

import argparse
import copy
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.generate import REPO, sha
from hardware.cad.a12.thermal.verify import binary_stl

from .generate import FASTENERS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rear-ports"
BASE = ROOT.parent / "panel_mount_audit/baseline-other.json"
AUDIO = {
    side + "_" + kind + "_" + channel
    for side in ["input", "output"]
    for kind in ["rca", "ts"]
    for channel in ["l", "r"]
}


def generate():
    old = json.loads(BASE.read_text())
    candidate = copy.deepcopy(old)
    changed = {}
    for collection in ["rear_ports", "port_envelopes"]:
        changed[collection] = []
        for i, row in enumerate(candidate[collection]):
            if row[0] in AUDIO:
                row[3] += 0.8
                changed[collection].append(row[0])
                assert all(row[j] == old[collection][i][j] for j in range(len(row)) if j != 3)
            else:
                assert row == old[collection][i]
        assert set(changed[collection]) == AUDIO
    ports = {p[0]: p for p in candidate["rear_ports"]}
    for b in candidate["port_envelopes"]:
        if b[0] in AUDIO:
            assert math.isclose(b[3] + b[6] / 2, ports[b[0]][3], abs_tol=1e-9)
            assert math.isclose(ports[b[0]][3], 14, abs_tol=1e-9)
            assert b[2] == 0
    # Inherit exact native-CAD sources, including the original opening and wall.
    prior_path = ROOT / "generated/verification.json"
    prior = json.loads(prior_path.read_text())
    assert prior["native_enclosure_blank_checks_clear"] and not prior["changed_inputs"]
    hashes = dict(prior["source_sha256"])
    for p in [BASE, Path(__file__), prior_path, Path(__file__).with_name("generate.py")]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    OUT.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(ROOT.parent / "thermal-integration.scad") + ">\n"
    for k, v in dict(rp_old=old["port_envelopes"], rp_new=candidate["port_envelopes"]).items():
        scad += k + "=" + json.dumps(v) + ";\n"
    scad += """
rear_case="plate";
function rp_audio_id(id)=id=="input_rca_l"||id=="input_rca_r"||id=="input_ts_l"||id=="input_ts_r"||id=="output_rca_l"||id=="output_rca_r"||id=="output_ts_l"||id=="output_ts_r";
// The mating face is correlated at Y0. The requirement boxes describe the
// body BEHIND that face, not the thread/neck through its own panel aperture.
// A 20nm inward guard removes only the coplanar rear-face STL artifact.
module rp_boxes(rows,m=0){for(b=rows)translate([b[1]-m,.00002,b[3]-.2-m])cube([b[4]+2*m,b[5]+m,b[6]+.4+2*m]);}
module rp_plate(){rear_panel();}
module rp_chassis(){retained_thermal_shell();}
if(rear_case=="plate")rp_plate();
if(rear_case=="bodies")rp_boxes([for(b=rp_new)if(rp_audio_id(b[0]))b]);
if(rear_case=="audio_chassis_collision")intersection(){rp_boxes([for(b=rp_new)if(rp_audio_id(b[0]))b],.25);rp_chassis();}
if(rear_case=="other_ports_chassis_collision")intersection(){rp_boxes([for(b=rp_new)if(!rp_audio_id(b[0]))b],.25);rp_chassis();}
if(rear_case=="old_TS_blocked_witness")intersection(){rp_boxes([for(b=rp_old)if(b[0]=="input_ts_l"||b[0]=="input_ts_r"||b[0]=="output_ts_l"||b[0]=="output_ts_r")b]);rp_chassis();}
if(rear_case=="plate_positive_control")intersection(){rp_plate();translate([15.9,-1,4])cube([.2,.2,.2]);}
if(rear_case=="TS_body_positive_control")intersection(){rp_boxes([for(b=rp_new)if(b[0]=="input_ts_l")b]);translate([73.9,1,4.7])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    plan = dict(
        scope=__doc__,
        source_sha256=hashes,
        source_rear_ports=old["rear_ports"],
        candidate_rear_ports=candidate["rear_ports"],
        source_port_envelopes=old["port_envelopes"],
        candidate_port_envelopes=candidate["port_envelopes"],
        changed_only_audio_row_z_mm=0.8,
        audio_jack_centres_z_mm=14,
        unchanged_cassette_opening_z_mm=[3.8, 31],
        wall_mm=2.8,
        minimum_TS_body_z_after_position_clearance_mm=4.05,
        separate_Z_position_allocation_mm=0.2,
        separate_external_clearance_mm=0.25,
        mating_face_y_mm=0,
        intended_face_boolean_guard_mm=0.00002,
        source_port_classes_or_apertures_reduced=False,
        original_DC_switch_SD_USB_positions_unchanged=True,
        exact_jack_mating_threads_washers_or_harness_qualified=False,
        whole_assembly_integration_verified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def verify(executable):
    plan = json.loads((OUT / "analysis.json").read_text())
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [OUT / "analysis.json", OUT / "checks.scad"]}
    cases = {}
    names = [
        "plate",
        "bodies",
        "audio_chassis_collision",
        "other_ports_chassis_collision",
        "old_TS_blocked_witness",
        "plate_positive_control",
        "TS_body_positive_control",
    ]
    (OUT / "verification.json").unlink(missing_ok=True)
    for name in names:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="rear_candidate_only"']
        values = dict(
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            fasteners=FASTENERS,
            rear_ports=plan["candidate_rear_ports"],
            rear_case=name,
        )
        for key, value in values.items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        if name.endswith("collision") and clean and empty:
            row = dict(clear=True, empty=True)
        elif p.returncode == 0 and target.exists() and "NoError" in log and clean:
            stats = binary_stl(target)
            ok = not name.endswith("collision") and stats["volume_mm3"] > 0.001
            if name.endswith("positive_control"):
                ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            if name == "old_TS_blocked_witness":
                ok &= math.isclose(stats["volume_mm3"], 63.839532766, abs_tol=0.002)
            row = dict(clear=bool(ok), **stats)
        else:
            row = dict(clear=False, returncode=p.returncode)
        cases[name] = row
        print(name, row, flush=True)
    changed = [n for n, h in {**plan["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        rear_body_envelope_native_checks_clear=not changed and all(r["clear"] for r in cases.values()),
        source_sha256=plan["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
        exact_parts_harness_or_physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args()
    generate()
    raise SystemExit(0 if verify(args.openscad)["rear_body_envelope_native_checks_clear"] else 1)
