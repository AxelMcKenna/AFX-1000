"""Native actual-PCB integration diagnostics, including both populated faces.

Nonempty intersections are retained as failures, not suppressed. Even a clear
conditional envelope cannot approve unselected component/mate dimensions.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path

from hardware.cad.a11.integration import assignments

from .generate import OUT, REPO, ROOT, sha
from .generate import main as generate_base
from .repaired import main as generate_repaired
from .verify import stl_volume


def verify(executable, e28_bottom=None, vertical_uncertainty=None):
    generate_base()
    data = generate_repaired()
    contract = json.loads((ROOT / "interface.json").read_text())
    switch_count = len(assignments(ROOT.parent / "a11/generated/controls.scad")["buttons"])
    switch_geometry = contract["switch_assembly"]
    if vertical_uncertainty is None:
        vertical_uncertainty = contract["disconnect_terminals"]["vertical_assembly_uncertainty_allocation"]
    assert 0 <= vertical_uncertainty <= 1
    p03 = next(board for board in data["boards"] if board["id"] == "P03")
    p03_range = contract["power_candidate"]["adjustable_bottom_z_range"]
    p03_uncertainty = max(abs(value - p03["datum"][2]) for value in p03_range)
    e28 = next(board for board in data["boards"] if board["id"] == "E28")
    bottom = e28["datum"][2] if e28_bottom is None else e28_bottom
    dz = bottom - e28["datum"][2]
    assert 0 <= dz <= 1, "Only nominal or upward candidate trials are supported"
    sources = dict(json.loads((OUT / "allocation.json").read_text())["source_sha256"])
    sources.update(data["source_sha256"])
    for path in [
        Path(__file__),
        ROOT / "repaired-integration.scad",
        ROOT / "thermal-integration.scad",
        OUT / "repaired-components.scad",
        OUT / "components.scad",
        OUT / "interface.scad",
        ROOT / "thermal/generated/thermal-base.scad",
        ROOT / "returns/generated/returns.scad",
        *sorted((ROOT / "returns/generated").glob("*.stl")),
    ]:
        sources[str(path.relative_to(REPO))] = sha(path)
    assert all(sha(REPO / name) == value for name, value in sources.items()), (
        "Initial geometry snapshot is stale"
    )
    label = f"e28-z{bottom:.2f}-u{vertical_uncertainty:.2f}"
    output = REPO / "build/artifacts/cad/a12/repaired" / label
    output.mkdir(parents=True, exist_ok=True)
    checks = {}
    for part in [
        "pcbs",
        "components",
        "switch_electronics",
        "switch_lead_positive_control",
        "pcb_case_collision",
        "component_case_collision",
        "component_other_electronics_collision",
        "boards_mutual_collision",
        "component_positive_control",
    ]:
        target = output / (part + ".stl")
        target.unlink(missing_ok=True)
        command = [
            str(executable),
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            'part="repaired_only"',
            "-D",
            'thermal_part="repaired_only"',
            "-D",
            f'repaired_part="{part}"',
            "-D",
            f"repaired_e28_dz={dz}",
            "-D",
            f"repaired_e28_vertical_uncertainty={vertical_uncertainty}",
            "-D",
            f"repaired_p03_vertical_uncertainty={p03_uncertainty}",
            "-o",
            str(target),
            str(ROOT / "repaired-integration.scad"),
        ]
        run = subprocess.run(command, capture_output=True, text=True, timeout=60)
        log = run.stdout + run.stderr
        logfile = OUT / ("repaired-" + label + "-" + part + ".log")
        logfile.write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, (part, log)
        if run.returncode == 1 and "Current top level object is empty." in log:
            assert part.endswith("collision"), (
                part,
                "Missing geometry",
            )
            target.unlink(missing_ok=True)
            checks[part] = dict(result="empty intersection", collision=False)
        else:
            assert run.returncode == 0 and target.exists(), (part, log)
            volume = stl_volume(target)
            assert volume > 0.001, (part, "Degenerate or empty native output", volume)
            if part == "switch_electronics":
                expected = (
                    switch_count
                    * math.prod(switch_geometry["local_body_terminal_reserve_xy_mm"])
                    * (
                        switch_geometry["body_projection_maximum_mm"]
                        + switch_geometry["lead_solder_projection_requirement_mm"]
                    )
                )
                assert abs(volume - expected) < 0.2, ("Missing/overlapping switch reserves", volume, expected)
            if part == "switch_lead_positive_control":
                assert abs(volume - 1) < 1e-5, (part, volume)
            checks[part] = dict(
                volume_mm3=volume,
                stl_sha256=sha(target),
                collision=part.endswith("collision"),
                result="collision found" if part.endswith("collision") else "nonempty native geometry",
            )
        checks[part]["log_sha256"] = sha(logfile)
        print(part, checks[part]["result"], flush=True)
    assert all(sha(REPO / name) == value for name, value in sources.items()), (
        "Board/source changed during native checks"
    )
    report = dict(
        scope="Actual native outlines and both-face courtyards; conditional body/mating/lead/seat limits",
        component_count=len(data["component_records"]),
        pcb_mount_fastener_requirements=data["mounting_fastener_requirements"],
        both_populated_faces_included=sorted({record["face"] for record in data["component_records"]}),
        control_switch_count=switch_count,
        control_switch_allocations=switch_geometry,
        complete_loose_control_wiring_covered=False,
        source_e28_bottom_z_mm=e28["datum"][2],
        evaluated_e28_bottom_z_mm=bottom,
        e28_vertical_uncertainty_allocation_mm=vertical_uncertainty,
        p03_component_bottom_z_sweep_mm=p03_range,
        pcb_material_geometry_check_is_nominal=True,
        raised_post_extensions_included=dz > 0,
        nominal_clearance_allocation_mm=0.25,
        p03_thickness_range_allocation_mm=next(board for board in data["boards"] if board["id"] == "P03")[
            "thickness_range_allocation_mm"
        ],
        checks=checks,
        same_board_component_overlap_candidates=data["same_board_component_overlap_candidates"],
        all_checked_intersections_clear=not any(value.get("collision") for value in checks.values())
        and not data["same_board_component_overlap_candidates"],
        source_sha256=sources,
        log_sha256={part: value["log_sha256"] for part, value in checks.items()},
        all_component_and_mate_heights_approved=False,
        raised_board_mounts_and_return_bars_released=False,
        harness_and_terminal_cover_fit_verified=False,
        physical_fit_verified=False,
        fabrication_released=False,
        build_ready=False,
    )
    (OUT / ("repaired-" + label + "-verification.json")).write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", required=True, type=Path)
    parser.add_argument("--e28-bottom", type=float)
    parser.add_argument("--vertical-uncertainty", type=float)
    args = parser.parse_args()
    result = verify(args.openscad.resolve(), args.e28_bottom, args.vertical_uncertainty)
    if not result["all_checked_intersections_clear"]:
        raise SystemExit(2)
