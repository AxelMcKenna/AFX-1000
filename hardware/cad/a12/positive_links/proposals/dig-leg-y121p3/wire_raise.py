"""Private +1 mm translation of the positive wire curves, with vertical extensions.

All curved pieces and their certified radii/chord bounds remain congruent.
The source and receiver bare/joint geometry stay fixed. Each straight vertical
insulated end extends1mm; the entire wire length therefore grows2mm.
"""

import copy
import hashlib
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
BASE = ROOT / "native"
OUT = ROOT / "wire-raise-1mm"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    assert not OUT.exists(), "Preserve captured trials."
    capture = read(BASE / "inputs.json")
    inputs = {**capture["source_sha256"], **capture["context_sha256"]}
    source = BASE / "context/hardware/cad/a12/harness/generated/receiver-full-route/checks.scad"
    wire = {}
    for name in ["pf_bend", "pf_middle", "pf_stub_start"]:
        line = next(l for l in source.read_text().splitlines() if l.startswith(name + "="))
        wire[name] = json.loads(line.split("=", 1)[1].rstrip(";"))
    old = copy.deepcopy(wire)
    wire["pf_bend"][0][2] += 1
    wire["pf_stub_start"][0][2] += 1
    for p in wire["pf_middle"][0]:
        p[2] += 1
    for name in wire:
        assert wire[name][1] == old[name][1]
    assert all(
        math.dist(a[:2], b[:2]) == 0 and math.isclose(a[2] - b[2], 1, abs_tol=1e-12)
        for a, b in zip(wire["pf_middle"][0], old["pf_middle"][0])
    )
    for key in ["pf_middle", "pf_bend", "pf_stub_start"]:
        if key != "pf_middle":
            assert wire[key][0][:2] == old[key][0][:2]
    for p in [Path(__file__), BASE / "checks.scad", BASE / "gauge-derived.scad", BASE / "inputs.json"]:
        inputs[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in inputs.items())
    OUT.mkdir()
    plan = dict(
        scope=__doc__,
        source_sha256=inputs,
        only_overrides=wire,
        old_values=old,
        curved_segments_translation_mm=[0, 0, 1],
        all_curved_lengths_radii_chord_bounds_congruent=True,
        both_vertical_end_straights_extended_mm=1,
        positive_wire_total_length_increase_mm=2,
        actual_port_bare_joint_endpoints_unchanged=True,
        second_wire_all_geometry_unchanged=True,
        wire_cut_slack_strain_and_new_electrical_resistance_qualified=False,
        native_checks_complete=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    scad = "include <" + str(BASE / "checks.scad") + ">\n"
    scad += """
wr_case="none";
module wr_wire(m=0){pf_wire(0,m);}
if(wr_case=="new_wire_covered_positive_collision")intersection(){wr_wire(.25);pb_expand(.1)pb_all();}
if(wr_case=="new_wire_other_electronics_collision")intersection(){wr_wire(.25);ui_wire_obstacles();}
if(wr_case=="new_wire_PS01_body_collision")intersection(){wr_wire(.25);ps_body();}
if(wr_case=="new_wire_controls_case_collision")intersection(){wr_wire(.25);ui_environment();}
if(wr_case=="new_wire_returns_hardware_collision")intersection(){wr_wire(.25);union(){return_assembly();lower_shell_fasteners();ui_h9_head();tc2_posts();tc2_heads();}}
if(wr_case=="new_wire_pair_collision")intersection(){wr_wire(.25);pf_wire(1);}
if(wr_case=="new_wire_J8_attachment_collision")intersection(){wr_wire();pb_J8();}
if(wr_case=="new_wire_geometry")wr_wire();
if(wr_case=="wire_control")intersection(){wr_wire(.25);translate([160.9,120.4,12])cube([.2,.2,.2]);}
"""
    checks = OUT / "checks.scad"
    checks.write_text(scad)
    for p in [checks, OUT / "plan.json"]:
        inputs[str(p.relative_to(REPO))] = sha(p)
    definitions = capture["definitions"] + ['pb_case="none"']
    definitions += [n + "=" + json.dumps(v) for n, v in wire.items()]
    records = {}
    for name in [
        "new_wire_covered_positive_collision",
        "new_wire_other_electronics_collision",
        "new_wire_PS01_body_collision",
        "new_wire_controls_case_collision",
        "new_wire_returns_hardware_collision",
        "new_wire_pair_collision",
        "new_wire_J8_attachment_collision",
        "new_wire_geometry",
        "wire_control",
    ]:
        target = OUT / (name + ".stl")
        cmd = [
            "/private/tmp/rmx-openscad-mounted/OpenSCAD.app/Contents/MacOS/OpenSCAD",
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
        ]
        for d in definitions + ["wr_case=" + json.dumps(name)]:
            cmd += ["-D", d]
        cmd += ["-o", str(target), str(checks)]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        log = run.stdout + run.stderr
        (OUT / (name + ".log")).write_text(log)
        stats = binary_stl(target) if target.exists() else None
        empty = run.returncode == 1 and "Current top level object is empty." in log and stats is None
        expected = name.endswith("_collision")
        ok = "ERROR" not in log and "WARNING" not in log
        ok &= (
            empty
            if expected
            else run.returncode == 0 and "NoError" in log and stats is not None and stats["volume_mm3"] > 0
        )
        if name.endswith("_control") and stats:
            ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=2e-6)
        records[name] = dict(
            passed=bool(ok),
            expected_empty=expected,
            empty=empty,
            returncode=run.returncode,
            statistics=stats,
            command=cmd,
        )
        print(name, bool(ok), stats and stats["volume_mm3"], flush=True)
        (OUT / "partial-records.json").write_text(json.dumps(records, indent=2) + "\n")
    changed = [n for n, h in inputs.items() if sha(REPO / n) != h]
    result = dict(
        scope=__doc__,
        source_sha256=inputs,
        records=records,
        changed_inputs=changed,
        all_required_native_screens_passed=not changed and all(x["passed"] for x in records.values()),
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        artifact_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
