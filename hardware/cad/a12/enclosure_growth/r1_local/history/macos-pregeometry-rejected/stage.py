"""Capture frozen CP01 and stage only actual selectedR1 receiving geometry."""

import hashlib
import json
import re
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
CP = REPO / "hardware/cad/a12/thermal/enlarged_base_pot"
R1 = REPO / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-r1"
BASE = R1.parent / "processor-awg18-ear-fanout-j29-central"
OUT = ROOT / "generated"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2) + "\n")


def seal(folder):
    h = json.loads((folder / "handoff.json").read_text())
    assert all(sha(folder / n) == v for n, v in h["files_sha256"].items()), folder
    return h


def closure(entry):
    found = {}
    todo = [entry]
    while todo:
        p = todo.pop().resolve()
        if p in found:
            continue
        found[p] = sha(p)
        if p.suffix != ".scad":
            continue
        for a, b in re.findall(r'(?:include|use)\s*<([^>]+)>|import\(\s*"([^"]+)"', p.read_text()):
            q = Path(a or b)
            todo.append(q if q.is_absolute() else p.parent / q)
    return found


def stage():
    assert not (ROOT / "capture.json").exists() and not (ROOT / "handoff.json").exists(), (
        "Use a newpacket, never recapture sealed or capturedcontext"
    )
    seal(CP)
    seal(R1)
    native = json.loads((R1 / "generated/native.json").read_text())
    assert native["candidate_pcb_sha256"] == sha(R1 / "processor_carrier.kicad_pcb") and not any(
        native["counts"].values()
    )
    assert (
        sha(R1 / "processor_carrier.kicad_pcb")
        == "dc559bd94d0decdb89ee647cde00709f15463304e051497bf8b7dacc719194c8"
    )

    def fps(path):
        return {
            next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
            for f in children(read_sexpr(path.read_text()), "footprint")
        }

    old, new = [fps(p / "processor_carrier.kicad_pcb") for p in [BASE, R1]]
    assert len(old) == len(new) == 88 and all(sexpr(new[n]) == sexpr(f) for n, f in old.items() if n != "R1")
    selected = json.loads((R1 / "component-selections.json").read_text())["parts"]["R1"]
    assert selected["mpn"] == "WSLT2512R4700FEA"
    bb = courtyard(new["R1"], "F.CrtYd")
    row = [
        "new_selected_R1",
        bb[0] - 70,
        bb[1] - 58,
        8.1,
        bb[2] - bb[0],
        bb[3] - bb[1],
        selected["assembled_projection_receiving_requirement_mm"],
    ]
    assert all(abs(a - b) < 1e-7 for a, b in zip(row[1:], [107.91, 78.07, 8.1, 4.18, 7.86, 1.0]))
    entry = CP / "generated/context-derived.scad"
    original = closure(entry)
    mapping = {p: ROOT / "captured" / p.relative_to(REPO) for p in original}
    derived = {}
    removed = []
    for p, h in original.items():
        dst = mapping[p]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".scad":
            text = p.read_text()
            for prefix in ["ui_inherited_envelopes="]:
                for line in text.splitlines():
                    if not line.startswith(prefix):
                        continue
                    rows = json.loads(line.split("=", 1)[1].rstrip(";"))
                    drop = [b for b in rows if b[0] == "e19_R1"]
                    if drop:
                        assert len(drop) == 1
                        remaining = [b for b in rows if b[0] != "e19_R1"]
                        removed.append(
                            dict(
                                original_source=str(p.relative_to(REPO)),
                                old_row=drop[0],
                                all_other_rows_exact=True,
                            )
                        )
                        text = text.replace(line, prefix + json.dumps(remaining) + ";")
            for src, target in mapping.items():
                text = text.replace(str(src), str(target))
            dst.write_text(text)
        else:
            dst.write_bytes(p.read_bytes())
        derived[str(dst.relative_to(ROOT))] = sha(dst)
    assert len(removed) == 1, "Only one active oldR1source row may be excluded"
    assert all(sha(p) == h for p, h in original.items())
    cfg = json.loads((CP / "generated/config.json").read_text())
    write(OUT / "config.json", cfg)
    scad = "include <" + str(mapping[entry]) + ">\n"
    scad += "r1_row=" + json.dumps(row) + ";\nr1_old_row=" + json.dumps(removed[0]["old_row"]) + ";\n"
    scad += r"""
module r1_body(m=0,zsweep=0){translate([r1_row[1]-m,r1_row[2]-m,r1_row[3]-m-zsweep])cube([r1_row[4]+2*m,r1_row[5]+2*m,r1_row[6]+2*m+2*zsweep]);}
module r1_other_electronics(){for(b=ui_native_boards)ui_native_PCB(b);for(b=ui_other_boards)board_reserve(b);tc2_board();ui_components();}
module r1_margin(){r1_body(.25,.2);}
module r1_mounts_tools(){ui_h9_tool();tc2_tool();ui_h9_head();tc2_posts();tc2_heads();eb_lower();eb_foot_screws();}
if(r1_case=="receiving_geometry")r1_body();
if(r1_case=="external_electronics_collision")intersection(){r1_margin();r1_other_electronics();}
if(r1_case=="controls_collision")intersection(){r1_margin();union(){ui_controls();cp_pot_hardware();}}
if(r1_case=="case_base_interfaces_collision")intersection(){r1_margin();union(){eb_case_and_lid();eb_metal();eb_interfaces();eb_lower();eb_foot_screws();}}
if(r1_case=="power_collision")intersection(){r1_margin();ui_power_only();}
if(r1_case=="wire_joints_collision")intersection(){r1_margin();union(){pf_wires(.25);ui_all_joints(.25);}}
if(r1_case=="mount_tool_collision")intersection(){r1_margin();r1_mounts_tools();}
for(i=[0:2])if(r1_case==str("own_PCB_correlated_seat_",i))intersection(){translate([0,0,[-.2,0,.2][i]])r1_body();translate([0,0,[-.2,0,.2][i]])ui_receiver();}
if(r1_case=="new_R1_positive_control")intersection(){r1_body();translate([109.9,81.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="retained_other_component_positive_control")intersection(){r1_other_electronics();translate([99.9,89.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="old_R1_presence_positive_control")intersection(){ui_boxes([r1_old_row]);translate([95.9,86.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="only_old_R1_exclusion_control")intersection(){r1_other_electronics();translate([95.9,86.9,8.3])cube([.2,.2,.2]);}
if(r1_case=="uncorrelated_seat_shift_positive_control")intersection(){translate([0,0,-.2])r1_body();ui_receiver();translate([109.9,81.9,7.9])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    inputs = {str(p.relative_to(REPO)): h for p, h in original.items()}
    for p in [
        CP / "handoff.json",
        CP / "generated/config.json",
        R1 / "handoff.json",
        R1 / "processor_carrier.kicad_pcb",
        R1 / "component-selections.json",
        R1 / "generated/native.json",
        Path(__file__),
        ROOT / "verify.py",
        ROOT / "README.md",
    ]:
        inputs[str(p.relative_to(REPO))] = sha(p)
    write(
        ROOT / "capture.json",
        dict(
            original_source_sha256=inputs,
            derived_context_sha256=derived,
            CP01_handoff_sha256=sha(CP / "handoff.json"),
            R1_handoff_sha256=sha(R1 / "handoff.json"),
            old_R1_only_exclusions=removed,
            all_other87_complete_FP_exact=True,
            R1_selected_part=selected,
            actual_R1_receiving_row=row,
            external_clearance_mm=0.25,
            PCB_Z_receiving_sweep_mm=0.2,
            ownPCB_seat_is_correlated_and_only_own_receiver_excluded_externally=True,
            all_other_native_boards_retained=True,
            part_application_and_assembly_bounds_unaccepted=True,
            physical_qualified=False,
            fabrication_released=False,
        ),
    )
    print("Captured", len(original), "context inputs; onlyoldR1rowexcluded; actualnewrow", row)


if __name__ == "__main__":
    stage()
