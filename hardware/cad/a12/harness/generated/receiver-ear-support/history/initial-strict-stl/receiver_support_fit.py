"""Private H9 case-post candidate against the actual supported E19 ear.

These solids reserve a blind insert and an M2x4-class fastener; no exact insert,
fastener, material, dimensional process or structural load is qualified. The
frozen case and every prior PCB/check packet remain unchanged.
"""

import argparse
import json
import math
import struct
import subprocess
from pathlib import Path

from hardware.cad.a12.generate import REPO, sha
from hardware.cad.a12.repaired import outline
from hardware.cad.a12.thermal.verify import binary_stl
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from .receiver_review import footprints

ROOT = Path(__file__).resolve().parent
BOARD = ROOT / "proposals/processor-awg18-ear-supported"
BASE = ROOT / "generated/receiver-ear"
OUT = ROOT / "generated/receiver-ear-support"


def surface_components(path):
    """Count exact binary-STL shared-edge components and closed edge incidence."""
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    parent = list(range(count))
    edges = {}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50 * i)
        vertices = [tuple(row[j : j + 3]) for j in (3, 6, 9)]
        assert len(set(vertices)) == 3, "Degenerate triangle"
        for a, b in zip(vertices, vertices[1:] + vertices[:1], strict=True):
            key = tuple(sorted((a, b)))
            if key in edges:
                before, uses = edges[key]
                parent[find(i)] = find(before)
                edges[key] = (before, uses + 1)
            else:
                edges[key] = (i, 1)
    return dict(
        connected_surface_components=len({find(i) for i in range(count)}),
        edges_without_exactly_two_faces=sum(uses != 2 for _, uses in edges.values()),
    )


def generate():
    prior = json.loads((BASE / "verification.json").read_text())
    assert prior["all_local_ear_checks_clear"] and not prior["changed_inputs"]
    hashes = {}
    for key in ["source_sha256", "evidence_inputs_sha256", "evidence_sha256"]:
        hashes.update(prior[key])
    pcb = BOARD / "processor_carrier.kicad_pcb"
    native_path = BOARD / "generated/native.json"
    native = json.loads(native_path.read_text())
    assert native["candidate_pcb_sha256"] == sha(pcb) and not any(native["counts"].values())
    handoff_path = BOARD / "handoff.json"
    handoff = json.loads(handoff_path.read_text())
    for key in ["source_sha256", "artifact_sha256"]:
        for name, digest in handoff[key].items():
            p = BOARD / name
            assert sha(p) == digest, ("Stale supported-board seal", name)
            hashes[str(p.relative_to(REPO))] = digest
    hashes[str(handoff_path.relative_to(REPO))] = sha(handoff_path)
    drc = json.loads((BOARD / "generated/drc.json").read_text())
    erc = json.loads((BOARD / "generated/erc.json").read_text())
    assert all(not drc[k] for k in ["violations", "unconnected_items", "schematic_parity"])
    assert erc["sheets"] and all(not s["violations"] for s in erc["sheets"])
    for key in ["source_sha256", "artifact_sha256"]:
        hashes.update(native[key])
    for name in ["package-review.json", "native-metal-clearance.json"]:
        p = BOARD / "generated" / name
        d = json.loads(p.read_text())
        if name == "package-review.json":
            assert (
                d["candidate_pcb_sha256"] == sha(pcb)
                and d["old85_footprints_and_all_original_board_objects_exact"]
            )
        else:
            assert d["source_pcb_sha256"] == sha(pcb) and d["actual_all_four_layer_copper_clear"]
        hashes[str(p.relative_to(REPO))] = sha(p)
    tree = read_sexpr(pcb.read_text())
    fps = footprints(tree)
    h9 = fps["H9"]
    assert list(map(float, first(h9, "at")[1:])) == [252, 155.2]
    holes = []
    for fp in fps.values():
        for pad in children(fp, "pad"):
            drills = children(pad, "drill")
            if drills and len(drills[0]) == 2:
                drill = drills[0]
                x, y = transform(fp, first(pad, "at")[1:3])
                holes.append([x - 70, y - 58, float(drill[1])])
    # Reusing the body packet requires complete footprint identity, including J13.
    old = footprints(
        read_sexpr((ROOT / "proposals/processor-awg18-ear/processor_carrier.kicad_pcb").read_text())
    )
    assert set(fps) - set(old) == {"H9"} and all(fps[k] == f for k, f in old.items())
    for p in [Path(__file__), native_path, pcb, BASE / "verification.json", BASE / "checks.scad"]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / p) == h for p, h in hashes.items()), "Stale inherited source/evidence"
    OUT.mkdir(parents=True, exist_ok=True)
    scad = "include <" + str(BASE / "checks.scad") + ">\n"
    scad += "support_holes=" + json.dumps(holes) + ";\n"
    scad += "support_outline=" + json.dumps(outline(tree)) + ";\n"
    scad += """
// Added material overlaps the actual retained floor by 0.1 mm. The blind
// 3.2 mm insert reservation starts at Z3.2; it does not drill the floor.
module ss_post(m=0){difference(){translate([182,97.2,2.7-m])cylinder(d=7.2+2*m,h=3.8+2*m,$fn=128);translate([182,97.2,3.2])cylinder(d=3.2,h=3.31+m,$fn=128);}}
module ss_board(min_bore=false){translate([30,42,6.5])difference(){linear_extrude(1.6)polygon(support_outline);for(p=support_holes)translate([p[0]-30,p[1]-42,-.01])cylinder(d=(min_bore && p[0]==182 && p[1]==97.2)?2.3:p[2],h=1.62,$fn=128);}}
module ss_head(m=0){translate([182,97.2,8.1-m])cylinder(d=5.6+2*m,h=2.31+2*m,$fn=128);}
module ss_shaft(m=0){translate([182,97.2,4.1])cylinder(d=2.05+2*m,h=4,$fn=128);}
module ss_service(m=0){translate([182,97.2,8.1-m])cylinder(d=5.6+2*m,h=12+2*m,$fn=128);}
module ss_shell(){union(){retained_thermal_shell();ss_post();}}
// Intended support face is correlated with its own PCB seat, not an obstacle.
// The separate nominal post/board case retains the complete actual outline.
module ss_external(){ss_post(.45);ss_service(.45);}
if(trial=="support_post_geometry")ss_post();
if(trial=="support_board_geometry")ss_board();
if(trial=="support_fastener_geometry"){ss_head();ss_shaft();}
if(trial=="support_shell_geometry")ss_shell();
if(trial=="support_floor_bond")intersection(){ss_post();retained_thermal_shell();}
if(trial=="support_board_collision")intersection(){ss_post();ss_board();}
if(trial=="support_shaft_bore_collision")intersection(){ss_shaft(.105);ss_board(true);}
if(trial=="support_joint_collision")intersection(){ss_external();joint();}
if(trial=="support_electronics_collision")intersection(){ss_external();electronics();}
if(trial=="support_power_hardware_collision")intersection(){ss_external();hardware();}
if(trial=="support_existing_case_collision")intersection(){union(){translate([0,0,.00002])intersection(){ss_post();translate([170,85,2.8])cube([25,25,4]);}ss_service(.45);}case_parts();}
if(trial=="support_post_positive_control")intersection(){ss_post();translate([184.9,97.1,4])cube([.2,.2,.2]);}
if(trial=="support_head_positive_control")intersection(){ss_head();translate([181.9,97.1,9])cube([.2,.2,.2]);}
if(trial=="support_bore_positive_control")intersection(){ss_board(true);translate([183.4,97.1,7])cube([.2,.2,.2]);}
if(trial=="support_blind_bore_empty_control")intersection(){ss_post();translate([181.9,97.1,4])cube([.2,.2,.2]);}
"""
    (OUT / "checks.scad").write_text(scad)
    result = dict(
        scope=__doc__,
        source_sha256=hashes,
        candidate_pcb_sha256=sha(pcb),
        post_world_mm=[182, 97.2],
        post_outer_diameter_mm=7.2,
        post_z_mm=[2.7, 6.5],
        intended_floor_overlap_mm=0.1,
        insert_blind_bore_requirement_mm=[3.2, 3.2, 6.5],
        fastener_class="Unselected M2x4, head OD<=5.6 height<=2.31, shank OD<=2.05",
        minimum_H9_bore_requirement_mm=2.3,
        relative_shank_centering_allocation_mm=0.1,
        construction_margin_mm=0.005,
        proposed_engagement_mm=2.4,
        exact_insert_fastener_material_or_process_selected=False,
        strain_relief_implemented=False,
        structural_or_physical_qualified=False,
        fabrication_released=False,
        canonical_case_modified=False,
        complete_harness_verified=False,
    )
    (OUT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def verify(executable):
    report = json.loads((OUT / "analysis.json").read_text())
    inputs = {str(p.relative_to(REPO)): sha(p) for p in [OUT / "analysis.json", OUT / "checks.scad"]}
    cases = {}
    names = [
        "post_geometry",
        "board_geometry",
        "fastener_geometry",
        "shell_geometry",
        "floor_bond",
        "board_collision",
        "shaft_bore_collision",
        "joint_collision",
        "electronics_collision",
        "power_hardware_collision",
        "existing_case_collision",
        "post_positive_control",
        "head_positive_control",
        "bore_positive_control",
        "blind_bore_empty_control",
    ]
    (OUT / "verification.json").unlink(missing_ok=True)
    for short in names:
        name = "support_" + short
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="support_only"']
        cmd += ["-D", 'trial="' + name + '"', "-o", str(target), str(OUT / "checks.scad")]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = process.stdout + process.stderr
        (OUT / (name + ".log")).write_text(log)
        clean = not any(t in log for t in ["WARNING", "ERROR"])
        expect_empty = short.endswith("collision") or short == "blind_bore_empty_control"
        empty = (
            process.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        )
        if expect_empty and clean and empty:
            row = dict(clear=True, empty=True)
        elif process.returncode == 0 and target.exists() and "NoError" in log and clean:
            stats = binary_stl(target)
            ok = not expect_empty and stats["volume_mm3"] > 0.001
            if short.endswith("positive_control"):
                ok &= math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
            if short == "floor_bond":
                ok &= math.isclose(stats["volume_mm3"], math.pi * 3.6**2 * 0.1, abs_tol=0.003)
            if short == "shell_geometry":
                stats.update(surface_components(target))
                ok &= (
                    stats["connected_surface_components"] == 1
                    and stats["edges_without_exactly_two_faces"] == 0
                )
            row = dict(clear=bool(ok), **stats)
        else:
            row = dict(clear=False, returncode=process.returncode)
        cases[name] = row
        print(name, row, flush=True)
    changed = [p for p, h in {**report["source_sha256"], **inputs}.items() if sha(REPO / p) != h]
    result = dict(
        scope=__doc__,
        cases=cases,
        changed_inputs=changed,
        all_local_support_checks_clear=not changed and all(r["clear"] for r in cases.values()),
        source_sha256=report["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in OUT.iterdir() if p.suffix in [".log", ".stl"]
        },
        complete_harness_verified=False,
        structural_or_physical_qualified=False,
        fabrication_released=False,
    )
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True, type=Path)
    args = parser.parse_args()
    generate()
    raise SystemExit(0 if verify(args.openscad)["all_local_support_checks_clear"] else 1)
