"""Source-frozen PB02 screens; distinct EI02/fed and U14 contexts stay distinct."""

import argparse
import hashlib
import json
import math
import re
import subprocess
import tarfile
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
OUT = ROOT / "native"
PS = REPO / "hardware/cad/a12/pot_stack"
JG = REPO / "hardware/electronics/rail_disconnect/revision28/generated/direct-j8-gauge-study"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def stage():
    assert not OUT.exists(), "Preserve existing captures; use a new trial."
    ps = read(PS / "generated/verification.json")
    jg = read(JG / "current-study.json")
    pb = read(ROOT / "generated/geometry.json")
    psh = read(PS / "handoff.json")
    assert all(sha(PS / n) == h for n, h in psh["files_sha256"].items())
    inputs = {}
    for receipt in [ps, jg, pb]:
        for k in ["source_sha256", "artifact_sha256"]:
            for n, h in receipt[k].items():
                assert sha(REPO / n) == h, n
                assert n not in inputs or inputs[n] == h, n
                inputs[n] = h
    for p in [
        Path(__file__),
        PS / "handoff.json",
        PS / "generated/verification.json",
        JG / "current-study.json",
        ROOT / "generated/geometry.json",
    ]:
        inputs[str(p.relative_to(REPO))] = sha(p)
    archive = jg["archive"]
    assert sha(REPO / archive["path"]) == archive["sha256"]
    # An independent byte audit, without extracting or trusting member paths.
    with tarfile.open(REPO / archive["path"], "r:gz") as tf:
        members = tf.getmembers()
        assert len(members) == archive["members"]
        for m in members:
            assert m.isfile() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts
            data = tf.extractfile(m).read()
            p = REPO / m.name
            if not p.is_file():
                p = JG / m.name
            assert p.is_file() and p.read_bytes() == data, m.name
    inputs[archive["path"]] = archive["sha256"]
    # Close the actual literal SCAD dependency graph. Historical receipts may
    # bind a library through a nested handoff rather than the flat input map.
    pending = [REPO / n for n in inputs if Path(n).suffix == ".scad"]
    seen = set()
    extra_dependencies = {}
    dependency = re.compile(r'(?:include|use)\s*<([^>]+)>|import\(\s*"([^"]+)"')
    while pending:
        p = pending.pop()
        if p in seen:
            continue
        seen.add(p)
        for match in dependency.finditer(p.read_text()):
            name = match.group(1) or match.group(2)
            q = (p.parent / name).resolve()
            assert q.is_relative_to(REPO) and q.is_file(), (p, name)
            n = str(q.relative_to(REPO))
            if n not in inputs:
                inputs[n] = sha(q)
                extra_dependencies[n] = sha(q)
            if q.suffix == ".scad":
                pending.append(q)
    context = OUT / "context"
    derived = {}
    for n, h in inputs.items():
        p = REPO / n
        q = context / n
        q.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()
        if p.suffix == ".scad":
            data = data.decode().replace(str(REPO) + "/", str(context) + "/").encode()
        q.write_bytes(data)
        derived[str(q.relative_to(REPO))] = sha(q)
    gauge = (context / JG.relative_to(REPO) / "gauge.scad").read_text()
    native_inputs = context / JG.relative_to(REPO) / "native-inputs"
    gauge = gauge.replace('"native-inputs/', '"' + str(native_inputs) + "/")
    (OUT / "gauge-derived.scad").write_text(gauge)
    u14 = gauge[gauge.index("module electronics()") : gauge.index("module positive_hardware()")]
    assert u14.count("])translate([r[1]") == 2
    u14 = u14.replace("module electronics()", "module pb_U14_components()")
    u14 = u14.replace(
        "])translate([r[1]",
        '])if(!in_list(r[0],["P03_J24","P03_J23","E28_J10","E28_J11"]))translate([r[1]',
    )
    checks = "include <" + str(context / PS.relative_to(REPO) / "generated/checks.scad") + ">\n"
    checks += "include <" + str(OUT / "gauge-derived.scad") + ">\n"
    checks += u14 + "\n"
    parts = context / ROOT.relative_to(REPO) / "generated"
    checks += "pb_parts=" + json.dumps(str(parts) + "/") + ";\n"
    checks += r"""
pb_case="none";
module pb_raw(name){import(str(pb_parts,name,".stl"));}
module pb_links(){pb_raw("ANA-COVERED-ENVELOPE");pb_raw("DIG-COVERED-ENVELOPE");}
module pb_support(){pb_raw("SUPPORT-ENVELOPE");}
module pb_all(){pb_links();pb_support();}
module pb_expand(m){minkowski(){children();cube([2*m,2*m,2*m],center=true);}}
module pb_J8(){let($fn=96)expanded(){lug();washer_head();}}
module pb_nominal_J8(){let($fn=96){lug();washer_head();shaft();}}
// Only the four positive terminal bodies are intended electrical contacts.
// The four negative-terminal bodies remain full collision obstacles.
module pb_components(){ui_boxes([for(b=ui_native_boxes)if(!in_list(b[0],["P03_J24","P03_J23","E28_J10","E28_J11"]))b]);ui_cylinders();ui_boxes(ui_inherited_envelopes);ui_rear_bodies();tc2_components();ps_body();}
module pb_board_obstacles(){ui_PCBS();pb_components();}
module pb_others(){ui_controls();ui_lid();tc2_posts();tc2_heads();ui_h9_head();lower_shell_fasteners();}
module pb_returns(){return_assembly();}
module pb_case_obstacles(){ui_shell_rear();}
if(pb_case=="old_J8_positive_failure")intersection(){pb_J8();let($fn=96)positive_hardware();}
if(pb_case=="new_J8_positive_collision")intersection(){pb_J8();pb_expand(.1)pb_all();}
if(pb_case=="new_positive_electronics_fed_collision")intersection(){pb_expand(.35)pb_all();pb_board_obstacles();}
if(pb_case=="new_positive_controls_hardware_collision")intersection(){pb_expand(.35)pb_all();pb_others();}
if(pb_case=="new_positive_returns_collision")intersection(){pb_expand(.35)pb_all();pb_returns();}
if(pb_case=="new_positive_case_collision")intersection(){union(){pb_expand(.35)pb_links();intersection(){pb_expand(.35)pb_support();translate([-100,-100,2.80002])cube([600,600,200]);}}pb_case_obstacles();}
if(pb_case=="new_positive_old_fed_wire_collision")intersection(){pb_expand(.1)pb_all();union(){pf_wires(.25);ui_all_joints(.25);}}
// U14 source geometry is intentionally a separate context: this does not
// claim the old fed/J4 wire endpoints are valid on U14/P9.
if(pb_case=="new_positive_U14_component_collision")intersection(){pb_expand(.35)pb_all();let($fn=96)hull(){translate([0,0,-.2])electronics();translate([0,0,.2])electronics();}}
if(pb_case=="new_J8_controls_case_collision")intersection(){pb_J8();union(){pb_others();pb_case_obstacles();ps_body();}}
if(pb_case=="new_J8_old_fed_wire_collision")intersection(){pb_J8();union(){pf_wires();ui_all_joints();}}
if(pb_case=="positive_bar_control")intersection(){pb_raw("DIG-CU");translate([119.9,121.2,18])cube([.2,.2,.2]);}
if(pb_case=="positive_support_control")intersection(){pb_support();translate([165.9,123.4,3])cube([.2,.2,.2]);}
if(pb_case=="J8_control")intersection(){let($fn=96)lug();located()translate([7,-.1,.1])cube([.2,.2,.2]);}
if(pb_case=="candidate_DIG_geometry")pb_raw("DIG-CU");
if(pb_case=="candidate_support_geometry")pb_support();
"""
    # Per-object Z sweep, not a hull across the entire component population.
    checks = checks.replace(
        "let($fn=96)hull(){translate([0,0,-.2])electronics();translate([0,0,.2])electronics();}",
        "let($fn=96)minkowski(){pb_U14_components();cube([.00000002,.00000002,.4],center=true);}",
    )
    (OUT / "checks.scad").write_text(checks)
    command = next(iter(ps["cases"].values()))["command"]
    definitions = [command[i + 1] for i, x in enumerate(command[:-1]) if x == "-D"]
    definitions = [
        x.split("=", 1)[0] + '="pb_disabled"' if x.split("=", 1)[0] in ["part", "ps_case", "ui_case"] else x
        for x in definitions
    ]
    definitions += ["angle=90", "$fn=48"]
    result = dict(
        scope=__doc__,
        source_sha256=inputs,
        context_sha256=derived,
        original_PS01_handoff_files=len(psh["files_sha256"]),
        original_J8_archive_members=len(members),
        allowed_coordinate_changes=pb["changed_coordinates_mm"],
        definitions=definitions,
        gauge_only_relative_import_rebased=True,
        additional_transitive_dependencies_sha256=extra_dependencies,
        J8_sweep_each_axis_mm=0.9,
        new_positive_position_only_for_J8_mm=0.1,
        new_positive_position_plus_external_for_other_obstacles_mm=0.35,
        intended_bonding_seat_only_guard_Z_mm=2.80002,
        combined_coherent_U14_wire_unit_verified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "inputs.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def verify(executable):
    a = read(OUT / "inputs.json")
    inputs = {**a["source_sha256"], **a["context_sha256"]}
    for p in [OUT / "inputs.json", OUT / "checks.scad", OUT / "gauge-derived.scad"]:
        inputs[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in inputs.items())
    names = [
        "old_J8_positive_failure",
        "new_J8_positive_collision",
        "new_positive_electronics_fed_collision",
        "new_positive_controls_hardware_collision",
        "new_positive_returns_collision",
        "new_positive_case_collision",
        "new_positive_old_fed_wire_collision",
        "new_positive_U14_component_collision",
        "new_J8_controls_case_collision",
        "new_J8_old_fed_wire_collision",
        "positive_bar_control",
        "positive_support_control",
        "J8_control",
        "candidate_DIG_geometry",
        "candidate_support_geometry",
    ]
    records = {}
    for name in names:
        target = OUT / (name + ".stl")
        assert not target.exists()
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for d in a["definitions"] + ["pb_case=" + json.dumps(name)]:
            cmd += ["-D", d]
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        expected_empty = name.endswith("_collision")
        stats = binary_stl(target) if target.exists() else None
        ok = "ERROR" not in log and "WARNING" not in log
        ok &= (
            empty
            if expected_empty
            else p.returncode == 0 and "NoError" in log and stats is not None and stats["volume_mm3"] > 0
        )
        if name.endswith("_control") and stats:
            ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=2e-6)
        if name == "old_J8_positive_failure" and stats:
            ok &= math.isclose(stats["volume_mm3"], 2.1002543527357744, abs_tol=2e-5)
        records[name] = dict(
            passed=bool(ok),
            expected_empty=expected_empty,
            empty=empty,
            returncode=p.returncode,
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
        conditional_native_screens_passed=not changed and all(x["passed"] for x in records.values()),
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        artifact_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--openscad", type=Path)
    args = parser.parse_args()
    if args.stage:
        a = stage()
        print("staged", len(a["source_sha256"]), "inputs")
    if args.openscad:
        raise SystemExit(0 if verify(args.openscad)["conditional_native_screens_passed"] else 1)
