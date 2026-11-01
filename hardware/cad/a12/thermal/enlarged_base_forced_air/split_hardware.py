"""Exact distributive recovery of a resource-terminated union, no geometry edits."""

import argparse
import json
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .stage import OUT, ROOT, sha, write

EXPECTED = [
    "ui_electronics(false,false)",
    "cp_other_pot_bodies(p)",
    "ui_power_only()",
    "ps_other_controls()",
    "pf_wires(.25)",
    "ui_all_joints(.25)",
]


def capture_plan():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("Sealed source is read-only")
    target = ROOT / "hardware-split.scad"
    if target.exists():
        raise RuntimeError("Split source already captured")
    source = (OUT / "context-derived.scad").read_text()
    branch = next(
        s for s in source.splitlines() if s.startswith('if(ps_case=="hardware_other_components_collision")')
    )
    body = branch.split("intersection(){", 1)[1]
    hardware, tail = body.split("union(){", 1)
    assert hardware == "translate([p[0],p[1],0])ps_hardware_max();"
    assert tail.endswith("}}")
    families = [s for s in tail[:-2].split(";") if s]
    assert families == EXPECTED
    line = next(s for s in source.splitlines() if s.startswith("ps_centres="))
    centres = json.loads(line.split("=", 1)[1].rstrip(";"))
    assert len(centres) == 10 and len(set(map(tuple, centres))) == 10
    text = "include <generated/context-derived.scad>\np=ps_centres[fi_hw_index];\n"
    for j, call in enumerate(families):
        text += f"if(fi_hw_family=={j})intersection(){{" + hardware + call + ";}\n"
    text += (
        "if(fi_hw_family==6)intersection(){"
        + hardware
        + "translate([p[0]+3.9,p[1]-.1,47])cube([.2,.2,.2]);}\n"
    )
    target.write_text(text)
    write(
        OUT / "hardware-split-plan.json",
        dict(
            scope=__doc__,
            original_branch_exact=branch,
            original_branch_sha256=__import__("hashlib").sha256(branch.encode()).hexdigest(),
            hardware_expression_exact=hardware,
            obstacle_family_expressions_exact=families,
            centres=centres,
            pairs=[[i, j] for i in range(10) for j in range(6)],
            nonempty_HW_controls=[[i, 6] for i in range(10)],
            equivalence="For everyp, H(p) intersect union(Fj(p)) is empty iff all six H(p) intersect Fj(p) are empty. Require all tenp and all sixfamilies; own-pot exclusion unchanged.",
            failed_original_case_completed=False,
            geometry_tolerance_or_source_modules_changed=False,
            source_model_sha256=sha(OUT / "context-derived.scad"),
            source_helper_sha256=sha(target),
            original_rejected_full_receipt_sha256=sha(OUT / "verification.json"),
            original_exact_retry_receipt_sha256=sha(OUT / "retry-ps-hardware/verification.json"),
        ),
    )


def run(executable, output, pairs=None):
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(ROOT) and (ROOT / "handoff.json").exists():
        raise RuntimeError("Require fresh nonsealed output directory")
    plan = json.loads((OUT / "hardware-split-plan.json").read_text())
    assert plan["obstacle_family_expressions_exact"] == EXPECTED and len(plan["centres"]) == 10
    required = [*plan["pairs"], *plan["nonempty_HW_controls"]]
    selected = pairs or required
    assert all(p in required for p in selected)
    original = json.loads((OUT / "verification.json").read_text())
    retry = json.loads((OUT / "retry-ps-hardware/verification.json").read_text())
    assert original["input_sha256"] == retry["input_sha256"]
    assert original["cases"]["ps_hardware_other_components_collision"]["returncode"] == 137
    assert retry["cases"]["ps_hardware_other_components_collision"]["returncode"] == 137
    bindings = dict(original["input_sha256"])
    for p in [
        ROOT / "hardware-split.scad",
        Path(__file__),
        OUT / "hardware-split-plan.json",
        OUT / "verification.json",
        OUT / "retry-ps-hardware/verification.json",
    ]:
        bindings[str(p.resolve())] = sha(p)
    assert all(sha(Path(n)) == h for n, h in bindings.items())
    base = original["cases"]["ps_hardware_other_components_collision"]["command"][:-3]
    base[base.index('ps_case="hardware_other_components_collision"')] = 'ps_case="cp_only"'
    assert Path(base[0]).resolve() == Path(executable).resolve()
    output.mkdir(parents=True)
    rows = {}
    for i, j in selected:
        name = f"pot{i:02d}_family{j}"
        target = output / (name + ".stl")
        cmd = base + [
            "-D",
            "fi_hw_index=" + str(i),
            "-D",
            "fi_hw_family=" + str(j),
            "-o",
            str(target),
            str(ROOT / "hardware-split.scad"),
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        log = p.stdout + p.stderr
        (output / (name + ".log")).write_text(log)
        stat = mesh(target) if p.returncode == 0 and target.exists() else None
        clear = (
            (p.returncode == 1 and "Current top level object is empty." in log and not target.exists())
            if j < 6
            else (
                p.returncode == 0
                and "NoError" in log
                and stat
                and stat["closed_oriented_boundary"]
                and not stat["degenerate_triangles_excluded"]
                and abs(stat["volume_mm3"] - 0.008) < 2e-6
            )
        )
        clear = bool(clear and "WARNING" not in log and "ERROR" not in log)
        rows[name] = dict(
            pot_index=i,
            family_index=j,
            centre=plan["centres"][i],
            expected_empty=j < 6,
            clear=clear,
            returncode=p.returncode,
            statistics=stat,
            command=cmd,
        )
        changed = [n for n, h in bindings.items() if sha(Path(n)) != h]
        result = dict(
            scope=__doc__,
            cases=rows,
            selected_pairs=selected,
            required_pairs=required,
            complete_distributive_coverage=selected == required and len(rows) == 70,
            all_requested_clear=not changed and all(r["clear"] for r in rows.values()),
            original_union_native_execution_completed=False,
            input_sha256=bindings,
            changed_inputs=changed,
            artifact_sha256={
                str(p): sha(p)
                for n in rows
                for p in [output / (n + ".log"), output / (n + ".stl")]
                if p.exists()
            },
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        )
        write(output / "verification.json", result)
        print(
            json.dumps(
                dict(
                    case=name,
                    clear=clear,
                    returncode=p.returncode,
                    volume=stat["volume_mm3"] if stat else None,
                )
            ),
            flush=True,
        )
        if not clear:
            break
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-plan", action="store_true")
    parser.add_argument("--openscad")
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--pairs", help="JSONlist of [pot,family]; default all60pairs+10controls")
    a = parser.parse_args()
    if a.capture_plan:
        capture_plan()
    else:
        r = run(a.openscad, a.outdir, json.loads(a.pairs) if a.pairs else None)
        raise SystemExit(0 if r["all_requested_clear"] else 1)
