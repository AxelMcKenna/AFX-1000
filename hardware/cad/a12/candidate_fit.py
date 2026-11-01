"""Isolated actual-PCB integration checks for a coherent P03 candidate.

Uses the same nine native cases as verify_repaired with the candidate's actual
PCB/components. It stages private SCAD inputs and never overwrites canonical
board files or shared A12 generated packets. New thermal LAND/TIM is separate.
"""

import argparse
import json
import math
import re
import subprocess
from pathlib import Path

from hardware.cad.a11.integration import assignments

from .generate import REPO, ROOT, sha
from .positive_links.collisions import snapshot
from .repaired import packet
from .thermal.verify import binary_stl

CASES = [
    "pcbs",
    "components",
    "switch_electronics",
    "switch_lead_positive_control",
    "pcb_case_collision",
    "component_case_collision",
    "component_other_electronics_collision",
    "boards_mutual_collision",
    "component_positive_control",
]


def prepare(candidate, out):
    assert candidate.resolve() != REPO / "hardware/electronics/power_distribution/p03", (
        "Use a separate candidate"
    )
    proof_file = candidate / "generated/current-native.json"
    proof = json.loads(proof_file.read_text())
    for key in ["source_sha256", "artifact_sha256"]:
        assert all(sha(REPO / n) == h for n, h in proof[key].items()), "Stale native candidate proof"
    pcb = candidate / "power_p03.kicad_pcb"
    assert proof["pcb_sha256"] == sha(pcb) == proof["source_sha256"][str(pcb.relative_to(REPO))], (
        "Native proof describes a different candidate PCB"
    )
    assert proof["native_electrically_closed"] and not any(proof["native_counts"].values())
    for name in ["complete-scratch-drc.json", "complete-scratch-erc.json"]:
        raw = candidate / "generated" / name
        assert str(raw.relative_to(REPO)) in proof["artifact_sha256"], "Unbound native report"
        data = json.loads(raw.read_text())
        if name.endswith("drc.json"):
            assert all(not data[k] for k in ["violations", "unconnected_items", "schematic_parity"]), (
                "Native DRC is not closed"
            )
        else:
            assert data["sheets"] and all(not sheet["violations"] for sheet in data["sheets"]), (
                "Native ERC is not closed"
            )
    _, other, hashes = snapshot()
    for key in ["source_sha256", "artifact_sha256"]:
        hashes.update(proof[key])
    native = packet({"P03": candidate})
    hashes.update(native["source_sha256"])
    hashes[str(proof_file.relative_to(REPO))] = sha(proof_file)
    hashes[str(Path(__file__).relative_to(REPO))] = sha(Path(__file__))
    out.mkdir(parents=True, exist_ok=True)
    # The parent source stays bound as a reference; the actual native P03
    # geometry in this private packet comes only from the selected candidate.
    boards = [
        [
            b["id"],
            b["datum"],
            b["nominal_thickness_mm"],
            b["outline_relative_mm"],
            b["mounting_holes_relative_mm"],
        ]
        for b in native["boards"]
    ]
    packet_file = out / "repaired-components.scad"
    packet_file.write_text(
        "\n".join(
            k + "=" + json.dumps(v) + ";"
            for k, v in dict(
                repaired_boards=boards, repaired_boxes=native["boxes"], repaired_cylinders=native["cylinders"]
            ).items()
        )
        + "\n"
    )
    component_file = out / "components.scad"
    component_file.write_text("\n".join(k + "=" + json.dumps(v) + ";" for k, v in other.items()) + "\n")
    staged = {
        "integration.scad": out / "integration.scad",
        "thermal-integration.scad": out / "thermal-integration.scad",
        "generated/components.scad": component_file,
        "generated/repaired-components.scad": packet_file,
    }
    for name in ["integration.scad", "thermal-integration.scad", "repaired-integration.scad"]:
        original = ROOT / name
        hashes[str(original.relative_to(REPO))] = sha(original)

        def rewrite(match):
            kind, target = match.groups()
            replacement = staged.get(target, (original.parent / target).resolve())
            return kind + " <" + str(replacement) + ">"

        text = re.sub(r"(include|use)\s*<([^>]+)>", rewrite, original.read_text())
        (out / name).write_text(text)
    for p in out.glob("*.scad"):
        hashes[str(p.relative_to(REPO))] = sha(p)
    contract = json.loads((ROOT / "interface.json").read_text())
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Source changed during preparation"
    report = dict(
        scope="Nine native actual-board/courtyard/control/housing cases; new thermal LAND/TIM and complete harness excluded",
        candidate_root=str(candidate.relative_to(REPO)),
        candidate_pcb_sha256=proof["pcb_sha256"],
        native_packet=native,
        source_sha256=hashes,
        source_e28_bottom_z_mm=next(b["datum"][2] for b in native["boards"] if b["id"] == "E28"),
        vertical_uncertainty_mm=contract["disconnect_terminals"]["vertical_assembly_uncertainty_allocation"],
        p03_vertical_uncertainty_mm=max(
            abs(z - contract["power_candidate"]["datum"][2])
            for z in contract["power_candidate"]["adjustable_bottom_z_range"]
        ),
        switch_count=len(assignments(ROOT.parent / "a11/generated/controls.scad")["buttons"]),
        switch_allocations=contract["switch_assembly"],
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def verify(executable, out):
    report = json.loads((out / "analysis.json").read_text())
    (out / "verification.json").unlink(missing_ok=True)
    inputs = {str((out / "analysis.json").relative_to(REPO)): sha(out / "analysis.json")}
    cases = {}
    for name in CASES:
        target = out / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key in ["part", "thermal_part", "positive_part"]:
            cmd += ["-D", key + '="candidate_fit_only"']
        cmd += [
            "-D",
            'repaired_part="' + name + '"',
            "-D",
            "repaired_e28_vertical_uncertainty=" + str(report["vertical_uncertainty_mm"]),
            "-D",
            "repaired_p03_vertical_uncertainty=" + str(report["p03_vertical_uncertainty_mm"]),
            "-o",
            str(target),
            str(out / "repaired-integration.scad"),
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        log = p.stdout + p.stderr
        (out / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        if empty and name.endswith("collision") and not any(s in log for s in ["WARNING", "ERROR"]):
            cases[name] = dict(clear=True, empty=True, command=cmd)
        elif (
            p.returncode == 0
            and target.exists()
            and "NoError" in log
            and not any(s in log for s in ["WARNING", "ERROR"])
        ):
            stats = binary_stl(target)
            clear = not name.endswith("collision") and stats["volume_mm3"] > 0.001
            if name == "switch_electronics":
                s = report["switch_allocations"]
                expected = (
                    report["switch_count"]
                    * math.prod(s["local_body_terminal_reserve_xy_mm"])
                    * (s["body_projection_maximum_mm"] + s["lead_solder_projection_requirement_mm"])
                )
                clear = math.isclose(stats["volume_mm3"], expected, abs_tol=0.2)
            if name in ["component_positive_control", "switch_lead_positive_control"]:
                clear = math.isclose(
                    stats["volume_mm3"], 0.008 if name == "component_positive_control" else 1, abs_tol=1e-5
                )
            cases[name] = dict(clear=clear, command=cmd, **stats)
        else:
            cases[name] = dict(clear=False, returncode=p.returncode, command=cmd)
        print(out.name, name, cases[name]["clear"], flush=True)
    changed = [n for n, h in {**report["source_sha256"], **inputs}.items() if sha(REPO / n) != h]
    result = dict(
        scope=report["scope"],
        candidate_pcb_sha256=report["candidate_pcb_sha256"],
        cases=cases,
        changed_inputs=changed,
        same_board_component_overlap_candidates=report["native_packet"][
            "same_board_component_overlap_candidates"
        ],
        all_checked_intersections_clear=not changed
        and all(c["clear"] for c in cases.values())
        and not report["native_packet"]["same_board_component_overlap_candidates"],
        source_sha256=report["source_sha256"],
        evidence_inputs_sha256=inputs,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p) for p in out.iterdir() if p.suffix in (".log", ".stl")
        },
        complete_new_thermal_geometry_included=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--openscad", required=True, type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    out = ROOT / "generated/candidate-fit" / candidate.name
    prepare(candidate, out)
    raise SystemExit(0 if verify(args.openscad, out)["all_checked_intersections_clear"] else 1)
