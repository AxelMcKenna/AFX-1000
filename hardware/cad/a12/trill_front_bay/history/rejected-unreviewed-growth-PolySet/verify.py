"""TC02 conditional native checks; retain blocked service and failed fit sensitivity."""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a12.thermal.verify import binary_stl

from .build import OUT, REPO, ROOT, sha

SOLIDS = ["geometry", "posts_geometry", "growth_slab_geometry"]
EMPTY = [
    "existing_collision",
    "case_collision",
    "controls_collision",
    "power_collision",
    "wire_collision",
    "posts_component_tail_collision",
    "heads_components_collision",
    "posts_board_collision",
    "shank_board_collision",
    "bore_relative_0p2_collision",
    "growth_nominal_collision",
    "growth_0p45_collision",
    "growth_0p90_collision",
    "openlid_tool_electronics_collision",
    "openlid_tool_power_case_collision",
]
WITNESS = ["bore_relative_0p3_rejected_sensitivity", "guide_left_in_place_blocked_witness", "floor_bond"]
CONTROL = [
    "post_positive_control",
    "body_positive_control",
    "growth_positive_control",
    "tool_positive_control",
]


def verify(executable):
    meta = json.loads((OUT / "analysis.json").read_text())
    model = json.loads((ROOT.parent / "enclosure_growth/integration/generated/analysis.json").read_text())
    bindings = dict(meta["source_sha256"])
    for p in [OUT / "analysis.json", OUT / "checks.scad", OUT / "context-derived.scad", Path(__file__)]:
        bindings[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in bindings.items())
    cases = {}
    for name in SOLIDS + EMPTY + WITNESS + CONTROL:
        target = OUT / (name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [str(executable), "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl"]
        for key, value in dict(
            part="tc2_only",
            thermal_part="tc2_only",
            positive_part="tc2_only",
            candidate_case="tc2_only",
            trial="tc2_only",
            ui_case="tc2_only",
            body_width=334,
            body_depth=188.4,
            shell_height=45.6,
            panel_z=43.6,
            fasteners=model["nine_lid_boss_positions_mm"],
            board_mounts=json.loads(
                (ROOT.parent / "enclosure_growth/integration/generated/scene.json").read_text()
            )["mounts"],
            tc2_case=name,
        ).items():
            cmd += ["-D", key + "=" + json.dumps(value)]
        cmd += ["-o", str(target), str(OUT / "checks.scad")]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
        (OUT / (name + ".log")).write_text(log)
        empty = p.returncode == 1 and "Current top level object is empty." in log and not target.exists()
        clean = not any(s in log for s in ["WARNING", "ERROR"])
        status = "NoError" in log
        stats = binary_stl(target) if p.returncode == 0 and target.exists() else None
        valid = clean and (empty if name in EMPTY else status and stats and stats["volume_mm3"] > 0.001)
        if name in CONTROL:
            valid &= stats is not None and math.isclose(stats["volume_mm3"], 0.008, abs_tol=1e-6)
        if name == "floor_bond":
            expected = 2 * 64 * (3.6 / math.cos(math.pi / 128)) ** 2 * math.sin(2 * math.pi / 128) * 0.1
            valid &= stats is not None and math.isclose(stats["volume_mm3"], expected, abs_tol=0.0002)
        cases[name] = dict(
            role="empty"
            if name in EMPTY
            else "control"
            if name in CONTROL
            else "diagnostic_interference"
            if name in WITNESS
            else "solid",
            evidence_valid=bool(valid),
            geometry_clear=bool(valid and name in EMPTY),
            empty=empty,
            returncode=p.returncode,
            native_NoError=status,
            statistics=stats,
            command=cmd,
        )
        print(
            json.dumps(
                dict(case=name, evidence_valid=bool(valid), volume_mm3=stats["volume_mm3"] if stats else None)
            ),
            flush=True,
        )
        changed = [n for n, h in bindings.items() if sha(REPO / n) != h]
        result = dict(
            scope=__doc__,
            source_sha256=meta["source_sha256"],
            execution_inputs_sha256={n: h for n, h in bindings.items() if n not in meta["source_sha256"]},
            cases=cases,
            changed_inputs=changed,
            all_required_evidence_valid=all(c["evidence_valid"] for c in cases.values()) and not changed,
            all_primary_empty_checks_clear=len(cases) == len(SOLIDS + EMPTY + WITNESS + CONTROL)
            and all(cases[n]["geometry_clear"] for n in EMPTY),
            relative_0p3_sensitivity_accepted=False,
            panel_and_guide_installed_tool_access_clear=False,
            allphysical_hardware_process_electrical_flags=False,
            physical_qualified=False,
            electrical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
            artifact_sha256={
                str(p.relative_to(REPO)): sha(p)
                for n in cases
                for ext in [".log", ".stl"]
                for p in [OUT / (n + ext)]
                if p.is_file()
            },
        )
        (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--openscad", required=True, type=Path)
    a = p.parse_args()
    r = verify(a.openscad)
    raise SystemExit(not (r["all_required_evidence_valid"] and r["all_primary_empty_checks_clear"]))
