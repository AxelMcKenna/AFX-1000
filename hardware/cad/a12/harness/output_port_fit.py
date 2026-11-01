"""Actual copied-board J4-ear fit study; no operating PCB changes.

The native contract receipt permits exactly J4 and Edge.Cuts to change. Its
other 254 footprint contracts, zones and stack must still match the operating
source. Only that proven replacement is applied to the fresh assembly packet.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.positive_links.collisions import snapshot
from hardware.cad.a12.repaired import height, outline
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent
PROPOSAL = ROOT / "proposals/j4-ear"
OUT = ROOT / "generated/output-port-j4-ear"
SOURCE = REPO / "hardware/electronics/rail_disconnect/revision28/rail_disconnect.kicad_pcb"


def candidate_snapshot(proposal=PROPOSAL):
    native, data, hashes = snapshot()
    pcb = proposal / "rail_disconnect.kicad_pcb"
    receipt = proposal / "generated/contracts.json"
    contract = json.loads(receipt.read_text())
    assert contract["original_pcb_sha256"] == sha(SOURCE), "Operating source changed"
    assert contract["candidate_pcb_sha256"] == sha(pcb), "Candidate changed after native comparison"
    for key in (
        "changed_footprint_bodies_or_attributes",
        "changed_pad_contracts",
        "changed_complete_footprints",
    ):
        assert contract[key] == ["J4"], (key, contract[key])
    assert not contract["missing_footprints"] and not contract["extra_footprints"]
    assert contract["zone_contract_equal"] and contract["board_setup_equal"]
    assert not contract["edge_cuts_equal"]
    verifier = SOURCE.parent / "native_contract_compare.py"
    assert contract["verifier_sha256"] == sha(verifier)
    native_receipt = json.loads((proposal / "generated/native-commands.json").read_text())
    assert native_receipt["post_refill_pcb_sha256"] == sha(pcb)
    tree = read_sexpr(pcb.read_text())
    board = next(b for b in native["boards"] if b["id"] == "E28")
    old_outline = board["outline_relative_mm"]
    board["outline_relative_mm"] = outline(tree)
    assert float(first(first(tree, "general"), "thickness")[1]) == board["nominal_thickness_mm"]
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "J4"] for p in children(f, "property"))
    )
    assert first(fp, "layer")[1] == "F.Cu"
    parts = json.loads((proposal / "components.json").read_text())
    part = next(p for p in parts if p["ref"] == "J4")
    assert part["footprint"] == fp[1]
    projection, _ = height(str(fp[1]), "J4", part["part"])
    x0, y0, x1, y1 = courtyard(fp, "F.CrtYd")
    native["boxes"] = [b for b in native["boxes"] if not b[0].startswith("E28_J4")]
    native["boxes"].append(
        [
            "E28_J4",
            board["datum"][0] + x0 - 100,
            board["datum"][1] + y0 - 100,
            board["datum"][2] + board["thickness_range_allocation_mm"][0],
            x1 - x0,
            y1 - y0,
            projection
            + board["thickness_range_allocation_mm"][1]
            - board["thickness_range_allocation_mm"][0],
        ]
    )
    for pad in children(fp, "pad"):
        xy = transform(fp, first(pad, "at")[1:3])
        native["boxes"].append(
            [
                "E28_J4_tail_" + str(pad[1]),
                board["datum"][0] + xy[0] - 101.4,
                board["datum"][1] + xy[1] - 101.4,
                board["datum"][2] - 1.5,
                2.8,
                2.8,
                1.5,
            ]
        )
    for p in [
        Path(__file__),
        pcb,
        verifier,
        receipt,
        proposal / "components.json",
        proposal / "rail_disconnect.kicad_sch",
        proposal / "proposal.json",
        proposal / "generated/native-commands.json",
        proposal / "generated/drc.json",
        proposal / "generated/erc.json",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    return native, data, hashes, old_outline


def generate(offset_retainer=False, out=OUT):
    native, data, hashes, old_outline = candidate_snapshot()
    board = next(b for b in native["boards"] if b["id"] == "E28")
    joints = [b for b in native["boxes"] if b[0].startswith("E28_J4")]
    boxes = [b for b in native["boxes"] if not b[0].startswith("E28_J4")]
    boxes += [b for b in data["envelopes"] if not b[0].startswith("disconnect_")] + data["port_envelopes"]
    out.mkdir(parents=True, exist_ok=True)
    source = 'include <../../../thermal-integration.scad>\ntrial="geometry";\n'
    for key, value in dict(
        boxes=boxes,
        joints=joints,
        cylinders=native["cylinders"],
        old_outline=old_outline,
        new_outline=board["outline_relative_mm"],
        datum=board["datum"],
        thickness=board["thickness_range_allocation_mm"][1],
    ).items():
        source += key + "=" + json.dumps(value) + ";\n"
    source += """
module ear(){translate(datum)linear_extrude(thickness)difference(){polygon(new_outline);polygon(old_outline);}}
module joint_solids(){for(b=joints)translate([b[1],b[2],b[3]])cube([b[4],b[5],b[6]]);}
module subject(){ear();joint_solids();}
// +/-0.2 mm XYZ assembly allocation and 0.25 mm extra clearance are explicit
// study requirements. They remain unapproved by fabrication/assembly vendors.
module swept_subject(){minkowski(){subject();cube([.9,.9,.9],center=true);}}
module electronics(){for(b=boxes)translate([b[1],b[2],b[3]-.2])cube([b[4],b[5],b[6]+.4]);for(c=cylinders)translate([c[1],c[2],c[3]-.2])cylinder(d=c[4]/cos(180/128),h=c[5]+.4,$fn=128);
"""
    for b in native["boards"]:
        if b["id"] != "E28":
            source += (
                "translate("
                + json.dumps([*b["datum"][:2], b["datum"][2] - 0.2])
                + ")linear_extrude("
                + str(b["thickness_range_allocation_mm"][1] + 0.4)
                + ")polygon("
                + json.dumps(b["outline_relative_mm"])
                + ");\n"
            )
    for b in data["boards"]:
        if b[0] != "disconnect_carrier":
            source += "board_reserve(" + json.dumps(b) + ");\n"
    source += """}
module hardware(){return_assembly();import("../../../positive_links/generated/positive-links.stl");}
module case_parts(){retained_thermal_shell();thermal_controls();thermal_metal_base();lower_shell_fasteners();}
if(trial=="geometry")subject();
if(trial=="ear_geometry")ear();
if(trial=="electronics_collision")intersection(){swept_subject();electronics();}
if(trial=="case_collision")intersection(){swept_subject();case_parts();}
if(trial=="hardware_collision")intersection(){swept_subject();hardware();}
if(trial=="ear_hardware_collision")intersection(){ear();hardware();}
if(trial=="joint_hardware_collision")intersection(){joint_solids();hardware();}
if(trial=="ear_case_collision")intersection(){ear();case_parts();}
if(trial=="joint_case_collision")intersection(){joint_solids();case_parts();}
if(trial=="positive_control")intersection(){ear();translate([165,140,5.7])cube([.2,.2,.2]);}
"""
    if offset_retainer:
        folder = PROPOSAL / "retainer"
        retainer = json.loads((folder / "analysis.json").read_text())
        for name, value in {**retainer["source_sha256"], **retainer["artifacts_sha256"]}.items():
            assert sha(REPO / name) == value, "Offset retainer source changed"
            hashes[name] = value
        hashes[str((folder / "analysis.json").relative_to(REPO))] = sha(folder / "analysis.json")
        source = "use <../../proposals/j4-ear/retainer/retainer.scad>\n" + source
        remaining = []
        for name in ["ANA", "DIG"]:
            for part in [
                "POST",
                "CAP",
                "BASE-SCREW",
                "CAP-SCREW0",
                "CAP-SCREW1",
                "END0-SCREW",
                "END1-SCREW",
                "END0-WASHER",
                "END1-WASHER",
            ]:
                if name == "ANA" and part in ("POST", "CAP", "CAP-SCREW0", "CAP-SCREW1"):
                    continue
                remaining.append(f'import("../../../returns/generated/AFX-A12-R01-{name}-{part}.stl");')
        replacement = (
            "module hardware(){return_bars();proposed_ana_retainer();"
            + "".join(remaining)
            + 'import("../../../positive_links/generated/positive-links.stl");}'
        )
        source = source.replace(
            'module hardware(){return_assembly();import("../../../positive_links/generated/positive-links.stl");}',
            replacement,
        )
        # Independently check the new retention parts, including the raised
        # underside and arm, against every existing body and the actual PCB.
        source += "module candidate_board(){translate(datum)linear_extrude(thickness)polygon(new_outline);}\n"
        source += 'if(trial=="retainer_geometry")proposed_ana_retainer();\n'
        source += 'if(trial=="retainer_electronics_collision")intersection(){proposed_ana_retainer();union(){electronics();candidate_board();joint_solids();}}\n'
        # Exclude only the intended coplanar stem/base seating face at Z0.
        source += 'if(trial=="retainer_case_collision")intersection(){translate([0,0,.00001])proposed_ana_retainer();case_parts();}\n'
        source += 'if(trial=="retainer_links_collision")intersection(){proposed_ana_retainer();union(){return_bars();import("../../../positive_links/generated/positive-links.stl");}}\n'
        source += (
            'if(trial=="retainer_return_collision")intersection(){proposed_ana_retainer();return_bars();}\n'
        )
        source += 'if(trial=="retainer_positive_collision")intersection(){proposed_ana_retainer();import("../../../positive_links/generated/positive-links.stl");}\n'
    (out / "checks.scad").write_text(source)
    report = dict(
        scope="Actual PCB extension and relocated J4 pad/solder reserves only; curved wires and destination excluded",
        source_sha256=hashes,
        native_snapshot=native,
        other_snapshot=data,
        xyz_position_allocation_mm=0.2,
        extra_clearance_mm=0.25,
        offset_retainer_proposal=offset_retainer,
        actual_ear_expected_volume_mm3=3.3 * 10 * board["thickness_range_allocation_mm"][1],
        current_path_resistance_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Source changed during snapshot"
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify(executable, out=OUT):
    report = json.loads((out / "analysis.json").read_text())
    (out / "verification.json").unlink(missing_ok=True)
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [out / "checks.scad", out / "analysis.json"]}
    cases = {}
    names = [
        "geometry",
        "ear_geometry",
        "electronics_collision",
        "case_collision",
        "hardware_collision",
        "ear_hardware_collision",
        "joint_hardware_collision",
        "ear_case_collision",
        "joint_case_collision",
        "positive_control",
    ]
    if report["offset_retainer_proposal"]:
        names += [
            "retainer_geometry",
            "retainer_electronics_collision",
            "retainer_case_collision",
            "retainer_links_collision",
            "retainer_return_collision",
            "retainer_positive_collision",
        ]
    for case in names:
        target = out / (case + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for name in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", name + '="output_port_only"']
        cmd += ["-D", 'trial="' + case + '"', "-o", str(target), str(out / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (out / (case + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        if case.endswith("collision") and empty and not any(s in log for s in ["WARNING", "ERROR"]):
            cases[case] = dict(clear=True, empty=True)
        elif (
            p.returncode == 0
            and target.exists()
            and ("NoError" in log or "Top level object is a 3D object (PolySet):" in log)
            and not any(s in log for s in ["WARNING", "ERROR"])
        ):
            cases[case] = dict(clear=not case.endswith("collision"), **binary_stl(target))
            if case == "ear_geometry":
                cases[case]["clear"] = math.isclose(
                    cases[case]["volume_mm3"], report["actual_ear_expected_volume_mm3"], rel_tol=1e-5
                )
            if case == "positive_control":
                cases[case]["clear"] = math.isclose(cases[case]["volume_mm3"], 0.008, abs_tol=1e-6)
        else:
            cases[case] = dict(clear=False, returncode=p.returncode)
        print(case, cases[case], flush=True)
    changed = [n for n, h in {**report["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        cases=cases,
        changed_inputs=changed,
        local_port_clear=not changed and all(c["clear"] for c in cases.values()),
        source_sha256=report["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in out.iterdir() if p.suffix in (".log", ".stl")
        },
        physical_fit_verified=False,
        complete_output_harness=False,
        fabrication_released=False,
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", type=Path)
    parser.add_argument("--offset-retainer", action="store_true")
    args = parser.parse_args()
    out = OUT if not args.offset_retainer else OUT.parent / "output-port-j4-ear-offset-retainer"
    generate(args.offset_retainer, out)
    if args.openscad:
        raise SystemExit(0 if verify(args.openscad, out)["local_port_clear"] else 1)
