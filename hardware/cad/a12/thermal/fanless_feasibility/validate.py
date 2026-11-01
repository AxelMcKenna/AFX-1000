"""Reject stale/native-empty/false-qualification FF01 evidence."""

import json
import math

from .analyze import OUT, ROOT, read, sha
from .native_geometry import metadata


def errors(a):
    bad = []
    if abs(a["heat_target_w"] - 35.43154587633119) > 1e-10:
        bad.append("Retained heat target changed")
    if a["envelope"]["overall_including_controls_mm"] != 87.6:
        bad.append("Envelope changed")
    for key in [
        "actual_installed_capacity_upper_or_lower_w",
        "installed_h_lower_bound",
        "actual_model_uncertainty_bound_c",
    ]:
        if a[key] is not None:
            bad.append("Invented installed bound:" + key)
    if (
        a["physical_tests_performed"] != 0
        or a["new_cooling_geometry_adopted"]
        or a["thermal_qualified"]
        or a["fabrication_released"]
    ):
        bad.append("Unsupported adoption or physical claim")
    for row in a["bottom_arrays"]:
        if row["installed_bound"] or not row["no_installed_lower_h_guarantee"]:
            bad.append("Correlation promoted to installed guarantee")
        if not 0 < row["fin_efficiency"] <= 1:
            bad.append("Invalid fin efficiency")
        if (
            row["target_base_c"] == 65
            and row["capacity_black_aperture_plus20percent_h_control_w"] >= a["heat_target_w"]
        ):
            bad.append("Unexpected bottom-only comparison; requires review")
    for row in a["metal_shell_proposals"] + a["lid_refinement"]:
        if (
            not row["converged"]
            or not math.isfinite(row["heat_accepted_from_base_w"])
            or abs(row["conduction_and_surface_energy_residual_w"]) > 1e-6
        ):
            bad.append("Rejected surface/conduction solve")
        if row["installed_guarantee"]:
            bad.append("Metal-shell proposal promoted to installed guarantee")
        if not 40 <= row["lid_min_c"] <= row["lid_max_c"] <= row["base_prescribed_c"]:
            bad.append("Nonphysical lid temperatures")
    for row in a["vent_bounds"]:
        if row["actual_airflow_bound_established"]:
            bad.append("Invented installed vent airflow")
    return bad


def packet_errors():
    a = read(OUT / "analysis.json")
    bad = errors(a)
    for path, h in a["source_sha256"].items():
        if not (ROOT / path).exists() or sha(ROOT / path) != h:
            bad.append("Changed captured/model input:" + path)
    for name, expected in a["native_geometry"]["parts"].items():
        path = OUT / (name + ".stl")
        if not path.exists():
            bad.append("Missing required native solid:" + name)
            continue
        actual = metadata(path)
        if actual != {k: v for k, v in expected.items() if k != "wetted_minus_four18mm_foot_disks_m2"}:
            bad.append("Changed native solid metadata:" + name)
        if (
            actual["nonmanifold_edges"]
            or actual["inconsistent_oriented_edges"]
            or actual["connected_components"] != 1
        ):
            bad.append("Rejected required solid topology:" + name)
        if actual["zero_area_faces"]:
            bad.append("Degenerate required native solid:" + name)
    for name in ["native-geometry.json", "geometry-contract.json", "drawing-inputs.json"]:
        for path, h in read(OUT / name)["source_sha256"].items():
            if not (ROOT / path).exists() or sha(ROOT / path) != h:
                bad.append("Changed geometry/plot dependency:" + path)
    for key in ["bottom", "lid"]:
        log = (OUT / (key + "-native.log")).read_text()
        accepted_type = (
            ("NoError" in log) if key == "bottom" else ("3D object (PolySet)" in log and "Triangles:" in log)
        )
        if not accepted_type or "ERROR:" in log or "WARNING:" in log:
            bad.append("Rejected native geometry log:" + key)
    return bad


def seal_errors(saved=None):
    a = read(ROOT / "handoff.json") if saved is None else saved
    expected = {
        str(p.relative_to(ROOT)): sha(p)
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    }
    return (
        []
        if a.get("sha256") == expected and a.get("packet_integrity_accepted") is True
        else ["Changed/rejected FF01 seal"]
    )


def main():
    bad = packet_errors()
    a = dict(
        packet_integrity_accepted=not bad,
        errors=bad,
        sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in ROOT.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
        },
        thermal_qualified=False,
        new_cooling_geometry_adopted=False,
        physical_tests_performed=0,
    )
    (ROOT / "handoff.json").write_text(json.dumps(a, indent=2) + "\n")
    if bad:
        raise SystemExit("\n".join(bad))
    print("FF01 input/geometry/conservation checks accepted; no installed thermal pass or adoption.")


if __name__ == "__main__":
    main()
