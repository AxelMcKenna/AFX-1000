"""Reject stale A10 mechanical evidence and incomplete native check records."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OUT = REPO / "build/artifacts/cad/a10"


def verify_sources(record, repo=REPO, cad=ROOT):
    assert set(record["source_sha256"]) == {str(p.relative_to(cad)) for p in cad.rglob("*.scad")}, (
        "CAD source set changed"
    )
    for name, expected in record["source_sha256"].items():
        assert hashlib.sha256((cad / name).read_bytes()).hexdigest() == expected, (
            "Stale mechanical geometry",
            name,
        )
    for name, expected in record["power_integration"]["sources_sha256"].items():
        assert hashlib.sha256((repo / name).read_bytes()).hexdigest() == expected, (
            "Stale supply integration",
            name,
        )


def verify():
    record = json.loads((OUT / "validation.json").read_text())
    assert record["revision"] == "A10"
    verify_sources(record)
    for name in (
        "moving_collision",
        "fixed_collision",
        "lever_collision",
        "power_margin_collision",
        "power_thermal_collision",
    ):
        assert record["checks"][name] == "empty intersection", name
    for name in ("chassis_collision", "optics_collision"):
        result = record["checks"][name]
        assert result == "empty intersection" or (
            result["result"] == "intended planar seating contacts only"
            and result["maximum_plane_deviation_mm"] <= 1e-5
        ), name
    assert record["checks"]["all_holders"]["connected_solids"] == 29
    assert record["checks"]["all_keys"]["connected_solids"] == 29
    actual = record["power_integration"]
    assert len(actual["components"]) == 157 and len(actual["mounts"]) == 4
    assert actual["electronics_box_collisions"] == []
    assert actual["electronics_clearance"]["minimum_axis_gap_mm"] >= 0.25
    assert actual["minimum_allocated_floor_gap_mm"] >= 0.25
    assert actual["physical_fit_verified"] is False and actual["height_limits_qualified"] is False
    print(
        f"A10 current: {record['unique_stl_files']} verified solids, {record['printed_copies']} copies; 157 supply parts; native clearances pass; physical fit unverified"
    )
    return record


if __name__ == "__main__":
    verify()
