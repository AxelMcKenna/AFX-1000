"""Independent actual-artifact gate for a routing-incomplete thermal feasibility packet."""

import json
import math

from hardware.cad.a12.thermal.verify import binary_stl

from .generate import OUT, ROOT
from .network import REPO, sha

CASES = [
    "geometry",
    "component_collision",
    "link_collision",
    "case_collision",
    "positive_control",
    "source_front_witness",
    "C32_tail_witness",
]


def artifact_errors(report, output=OUT):
    errors = []
    rows = report.get("native_checks", {})
    if set(rows) != set(CASES) or not report.get("accepted_native_evidence"):
        errors.append("Missing/rejected required native case")
    for name in CASES:
        row = rows.get(name, {})
        p = output / (name + ".stl")
        logpath = output / (name + ".log")
        if not logpath.exists():
            errors.append(name + ": native log missing")
            continue
        log = logpath.read_text()
        if name.endswith("collision") and row.get("result") == "empty":
            if p.exists():
                errors.append(name + ": forged empty row with actual STL")
            if (
                row.get("returncode") != 1
                or "Current top level object is empty." not in log
                or any(t in log for t in ["WARNING", "ERROR"])
            ):
                errors.append(name + ": invalid native empty-case evidence")
            continue
        if row.get("result") != "valid native manifold" or not p.exists():
            errors.append(name + ": required actual geometry missing")
            continue
        if row.get("returncode") != 0 or "NoError" not in log or any(t in log for t in ["WARNING", "ERROR"]):
            errors.append(name + ": invalid native solid-case evidence")
        actual = json.loads(json.dumps(binary_stl(p)))
        if any(actual.get(k) != row.get(k) for k in actual):
            errors.append(name + ": actual STL/row mismatch")
        if name.endswith("collision") and actual["volume_mm3"] > 1e-6:
            errors.append(name + ": collision")
        if name == "geometry" and actual["volume_mm3"] <= 1:
            errors.append("Required LAND/TIM absent")
        if (name == "positive_control" or name.endswith("witness")) and not math.isclose(
            actual["volume_mm3"], 0.008, rel_tol=0.005, abs_tol=1e-6
        ):
            errors.append(name + ": witness failed")
    return errors


def main():
    native = json.loads((OUT / "verification.json").read_text())
    errors = artifact_errors(native)
    geometry = json.loads((OUT / "geometry.json").read_text())
    actual = binary_stl(OUT / "geometry.stl")["volume_mm3"]
    if not math.isclose(actual, sum(geometry["volumes_mm3"].values()), rel_tol=0.0005):
        errors.append("Wrong actual required geometry volume")
    a = json.loads((OUT / "analysis.json").read_text())
    if a["actual_native_electrical"]["electrically_complete"] or a["actual_native_electrical"]["opens"] != 16:
        errors.append("Routing-incomplete candidate misrepresented")
    if (
        a["candidate_package_contract"]["U10"]["face"] != "F.Cu"
        or a["original_package_contract"]["U10"]["face"] != "B.Cu"
    ):
        errors.append("Actual thermal source face misrepresented")
    for key in [
        "physical_fit_verified",
        "thermal_path_qualified",
        "canonical_pcb_modified",
        "frozen_heat_kit_modified",
        "fabrication_released",
    ]:
        if a[key] is not False:
            errors.append("Unsupported claim:" + key)
    if a["acceptance"]["guardbanded_project_acceptance"] or a["acceptance"]["path_upper_k_per_w"] is not None:
        errors.append("Invented thermal qualification bound")
    for group in [a["source_sha256"], geometry["source_sha256"], native["source_sha256"]]:
        for path, expected in group.items():
            if sha(REPO / path) != expected:
                errors.append("Stale input:" + path)
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.name != "handoff.json"
    ]
    report = dict(
        packet_integrity_accepted=not errors,
        errors=errors,
        sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(paths)},
        routing_complete=False,
        thermal_path_qualified=False,
        physical_tests_performed=0,
        canonical_modified=False,
        fabrication_released=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
