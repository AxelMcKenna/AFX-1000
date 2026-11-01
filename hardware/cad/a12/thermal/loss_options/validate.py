"""Portable boundary/claim checks for the separate loss-option comparison."""

import json
import math

from hardware.cad.a12.thermal.generate import REPO, sha

from .analyze import OUT, ROOT, WU, read


def errors(a):
    bad = []
    if not math.isclose(a["retained_baseline_heat_target_w"], 35.43154587633119, abs_tol=1e-10):
        bad.append("Existing load/heat target changed")
    if a["actual_heat_upper_w"] is not None or a["actual_loss_saving_guaranteed_w"] is not None:
        bad.append("Assumed comparison promoted to actual bound")
    for r in a["counterfactual_references"]:
        if (
            r["is_implemented"]
            or r["is_actual_minimum_heat_bound"]
            or r["load_allocations_reduced"]
            or r["export_credit_adopted"]
        ):
            bad.append("Counterfactual misrepresented as real design/minimum")
        if not r["result"]["converged"] or abs(r["result"]["energy_balance_residual_w"]) > 1e-6:
            bad.append("Nonconverged/unbalanced thermal comparison")
    if len(a["counterfactual_references"]) != 6:
        bad.append("Missing placement/loss reference")
    if not math.isclose(sum(r["resistance_ohm"] for r in a["complete_feed_partition"]), 0.36, abs_tol=1e-12):
        bad.append("Complete feed counted incorrectly")
    if not math.isclose(sum(r["heat_at4A_w"] for r in a["complete_feed_partition"]), 5.76, abs_tol=1e-10):
        bad.append("Input guard/feed loss counted incorrectly")
    aux = a["AUX_preregulator_option"]
    if (
        aux["implemented"]
        or aux["native_schematic_PCB_or_control_validation"]
        or not aux["feed_from_existing_protected5v_is_rejected_circular_dependency"]
    ):
        bad.append("AUX bootstrap/interface proof invented")
    for r in aux["efficiency_comparisons"]:
        if r["efficiency_is_guaranteed"]:
            bad.append("Typical/unverified efficiency promoted to guarantee")
        if not math.isclose(
            r["old_complete_AUX_input_w"] - r["new_complete_AUX_input_w"],
            r["conditional_saving_w"],
            abs_tol=1e-12,
        ):
            bad.append("AUX input/output/drop double count")
    if (
        a["XLR_inlet_comparison"]["hot_aged_mated_resistance_bound_established"]
        or a["XLR_inlet_comparison"]["implemented"]
    ):
        bad.append("Catalog connector spec promoted to installed proof")
    if a["Q101_hot_resistance_review"]["existing_40mohm_allocation_reduced"]:
        bad.append("Room-temperature resistance replaced hot requirement")
    if (
        a["actual_hardware_changed"]
        or not a["no_load_reserves_removed"]
        or not a["no_fan_or_housing_adopted"]
        or a["physical_tests_performed"]
        or a["thermal_qualified"]
    ):
        bad.append("Unsupported implementation/qualification")
    return bad


def packet_errors():
    a = read(OUT / "analysis.json")
    bad = errors(a)
    for p, h in a["source_sha256"].items():
        if not (REPO / p).exists() or sha(REPO / p) != h:
            bad.append("Stale option input:" + p)
    for p, h in read(OUT / "drawing-inputs.json")["source_sha256"].items():
        if sha(REPO / p) != h:
            bad.append("Changed plot input:" + p)
    return bad


def seal_errors(a=None):
    a = read(ROOT / "handoff.json") if a is None else a
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    ]
    return (
        []
        if a.get("sha256") == {str(p.relative_to(REPO)): sha(p) for p in paths}
        and a.get("packet_integrity_accepted") is True
        else ["Changed/rejected sealed options"]
    )


def main():
    bad = packet_errors()
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    ]
    a = dict(
        packet_integrity_accepted=not bad,
        errors=bad,
        sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        prior_WU01_seal_sha256=sha(WU / "handoff.json"),
        no_hardware_or_load_target_adoption=True,
        physical_tests_performed=0,
        loss_saving_qualified=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(a, indent=2) + "\n")
    if bad:
        raise SystemExit("\n".join(bad))
    print("LO01 source/energy/comparison evidence accepted; no hardware/heat-target adoption.")


if __name__ == "__main__":
    main()
