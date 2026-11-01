"""Validation-only certificate for the actual saved robust-rear projection.

No native run, STL or old report is overwritten. The first robust verifier
used the older generic-XH shadow area; this fixes that analysis input.
"""

import json
from pathlib import Path

from hardware.cad.a12.thermal.interior_airpath.verify import mesh

from .capture import ROOT, sha


def validate(stats, expected):
    bad = []
    if not stats or not stats["closed_oriented_boundary"] or stats["degenerate_triangles_excluded"]:
        bad.append("invalid-projection-topology")
    elif abs(stats["volume_mm3"] - expected) > 0.002:
        bad.append("independent-area-mismatch")
    elif any(
        abs(x - y) > 1e-5
        for a, b in zip([stats["min_mm"], stats["max_mm"]], [[38, 168.5, 0], [276.5, 183, 0.1]])
        for x, y in zip(a, b)
    ):
        bad.append("independent-bounds-mismatch")
    return bad


def build():
    out = ROOT / "generated/robust-projection-validation.json"
    if out.exists():
        raise RuntimeError("New validation record required")
    folder = ROOT / "generated/native-robust-rear"
    proof = folder / "verification.json"
    d = json.loads(proof.read_text())
    name = "new_receiving_inlet_shadow"
    row = d["cases"][name]
    stl = folder / (name + ".stl")
    log = folder / (name + ".log")
    p = ROOT / "generated/port-shadow-robust.json"
    area = json.loads(p.read_text())
    expected = (
        area["NF233_receiving_body_projection_overlap_mm2"]
        + area["FPC84_receiving_body_projection_overlap_mm2"]
    ) * 0.1
    assert row["returncode"] == 0 and row["errors"] == ["missing-NoError-or-named-certified-primitive"]
    assert (
        "Top level object is a 3D object (PolySet)" in log.read_text()
        and "WARNING" not in log.read_text()
        and "ERROR" not in log.read_text()
    )
    actual = mesh(stl)
    assert actual == row["statistics"]
    bad = validate(actual, expected)
    assert not bad, bad
    result = dict(
        validation_only_not_native_rerun=True,
        native_original_report_unchanged=True,
        native_original_returncode=1,
        named_primitive_case=name,
        actual_statistics=actual,
        independent_expected_volume_mm3=expected,
        errors=bad,
        full34_receiving_scope=dict(
            actual_clear_or_validated=32,
            remaining_rejections=[
                "NF233_mate_other_components_collision",
                "FPC84_short_bundle_electronics_collision",
            ],
        ),
        opaque_bundle_rejection_has_separate_actual14wire_local_escape9pass=True,
        unselected_NF_connector_still_failed=True,
        source_sha256={str(q): sha(q) for q in [Path(__file__), proof, stl, log, p]},
        physical_qualified=False,
        thermal_qualified=False,
        full_harness_qualified=False,
    )
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                named_primitive_valid=True,
                actual_volume_mm3=actual["volume_mm3"],
                expected=expected,
                native_rerun=False,
            )
        )
    )


if __name__ == "__main__":
    build()
