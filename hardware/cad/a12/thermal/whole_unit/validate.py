"""Portable energy, source-closure and saved-result integrity gates."""

import json
import math

from hardware.cad.a12.thermal.generate import REPO, sha

from .ledger import OUT, ROOT, read


def energy_errors(a):
    errors = []
    rows = a["leaf_heat_rows"]
    if len({r["id"] for r in rows}) != len(rows):
        errors.append("Duplicate counted power leaf")
    if any(not math.isfinite(r["watts"]) or r["watts"] < 0 for r in rows):
        errors.append("Invalid/negative heat or sign cancellation")
    total = math.fsum(r["watts"] for r in rows)
    for expected in [
        a["total_internal_heat_screen_w"],
        a["source_input_crosscheck_w"],
        math.fsum(a["blocks"].values()),
    ]:
        if not math.isclose(total, expected, abs_tol=1e-9):
            errors.append("Endpoint/conversion/source energy mismatch")
    if (
        a["nested_3v3_diagnostics"]["separately_added_to_heat_w"] != 0
        or a["ground_current_diagnostic_excluded"]["added_w"] != 0
    ):
        errors.append("Nested power or return current double counted")
    feed = next(r for r in rows if r["id"] == "inlet_wire_fuse_and_contacts")
    if not math.isclose(
        feed["remaining_feed_ohm"] + feed["counted_guard_ohm"], feed["complete_feed_ohm"], abs_tol=1e-12
    ):
        errors.append("Guard counted twice within complete feed")
    if (
        a["export_credit_w"] != 0
        or a["actual_whole_unit_heat_upper_w"] is not None
        or a["whole_unit_heat_qualified"] is not False
    ):
        errors.append("Unsupported heat export or qualification bound")
    for r in rows:
        if r["actual_consumption_guaranteed"] or r["optical_or_external_export_credit_w"] != 0:
            errors.append("Unsupported leaf guarantee/export")
    return errors


def analysis_errors(a, ledger):
    errors = []
    if len(a["cases"]) != 12 or len(a["required_uniform_h"]) != 8:
        errors.append("Missing requested thermal scenarios")
    if len(a["historical_equation_controls"]) != 5 or any(
        abs(r["delta_c"]) > 1e-7 for r in a["historical_equation_controls"]
    ):
        errors.append("Historical equation control failed/missing")
    for case in a["cases"]:
        row = case["result"]
        if (
            not row["converged"]
            or row["convergence_delta_c"] >= 1e-8
            or abs(row["energy_balance_residual_w"]) > 1e-6
        ):
            errors.append("Rejected/nonconverged solver evidence")
        if not math.isclose(row["total_w"], ledger["total_internal_heat_screen_w"], abs_tol=1e-6):
            errors.append("Thermal power differs from energy ledger")
        if row["convection_or_assembly_qualified"]:
            errors.append("Unsupported convection qualification")
    for mode in ["unplaced_uniform", "unplaced_hotcluster"]:
        for epsilon in [0.8, 0.05]:
            rows = [
                r["result"]
                for r in a["cases"]
                if r["placement"] == mode and r["result"]["emissivity_assumed"] == epsilon
            ]
            if [r["h_assumed_w_per_m2k"] for r in rows] != [1, 2, 3] or not all(
                x["plate_max_c"] > y["plate_max_c"] for x, y in zip(rows, rows[1:])
            ):
                errors.append("Nonmonotone/missing h sensitivity")
    for r in a["required_uniform_h"]:
        lo, hi = r["required_uniform_h_bracket_w_per_m2k"]
        if not 3 < lo < hi or hi - lo > 0.003 or r["installed_h_is_bounded"] or r["heat_transfer_qualified"]:
            errors.append("Invalid/unsupported cooling requirement")
    if (
        a["whole_base_qualified"]
        or a["physical_tests_performed"] != 0
        or a["actual_whole_unit_heat_upper_w"] is not None
        or a["installed_h_lower_w_per_m2k"] is not None
    ):
        errors.append("Unsupported thermal/physical upper")
    return errors


def packet_errors():
    ledger = read(OUT / "ledger.json")
    analysis = read(OUT / "analysis.json")
    errors = energy_errors(ledger) + analysis_errors(analysis, ledger)
    for name in ["ledger.json", "analysis.json", "drawing-inputs.json", "source-lineage.json", "environment.json"]:
        a = read(OUT / name)
        for path, expected in a["source_sha256"].items():
            if not (REPO / path).exists() or sha(REPO / path) != expected:
                errors.append("Stale saved input:" + path)
    capture = read(ROOT / "capture.json")
    for row in capture["captured"].values():
        if sha(REPO / row["captured"]) != row["sha256"]:
            errors.append("Captured source bytes changed:" + row["captured"])
    lineage = read(OUT / "source-lineage.json")
    for report in lineage["reports"]:
        if sha(REPO / report["report"]) != report["report_sha256"]:
            errors.append("Changed captured report:" + report["report"])
        for row in report["inputs"]:
            if row["captured"] is None or sha(REPO / row["captured"]) != row["actual_captured_sha256"]:
                errors.append("Missing/changed report evidence")
            if not row["captured_matches_report"] and not report["used_as_historical_comparison_only"]:
                errors.append("Unmatched source lineage for current power model")
    return errors


def seal_errors(a=None):
    a = read(ROOT / "handoff.json") if a is None else a
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    ]
    actual = {str(p.relative_to(REPO)): sha(p) for p in paths}
    return (
        []
        if a.get("sha256") == actual and a.get("packet_integrity_accepted") is True and not a.get("errors")
        else ["Sealed source/artifact set changed or rejected"]
    )


def main():
    errors = packet_errors()
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    ]
    report = dict(
        packet_integrity_accepted=not errors,
        errors=errors,
        sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        actual_whole_unit_heat_upper_w=None,
        physical_tests_performed=0,
        whole_base_qualified=False,
        canonical_modified=False,
        frozen_heat_kit_modified=False,
        fabrication_released=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    if errors:
        raise SystemExit("\n".join(errors))
    print("WU01 source/energy/numerical evidence accepted; actual thermal/source qualification false.")


if __name__ == "__main__":
    main()
