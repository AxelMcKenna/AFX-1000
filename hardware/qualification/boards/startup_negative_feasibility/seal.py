"""Seal the bounded comparison, rejecting fabricated guaranteed/physical conclusions."""

import json

from .compare import REPO, ROOT, sha


def claim_errors(report):
    errors = []
    for key in [
        "viable_with_all_current_contracts_verified",
        "provisional5s_is_hard_user_requirement",
        "canonical_boards_modified",
        "new_schematic_authored",
        "pcb_implemented",
        "startup_qualified",
        "soa_qualified",
    ]:
        if report[key] is not False:
            errors.append("Unsupported claim:" + key)
    if report["physical_tests_performed"] != 0 or report["five_second_guarantee_s"] is not None:
        errors.append("Unsupported physical/timing result")
    if (
        report["lt4250"]["n12_local_supply_supported"]
        or report["lt4250"]["guaranteed_fault_timer_s"] is not None
    ):
        errors.append("LT4250 range/timer misrepresented")
    if report["lm5067_fixed_limit_dead_end"]["larger_shunts_supported"]:
        errors.append("LM5067 shunt maximum waived")
    for rail, row in report["rails"].items():
        ss = row["ltc_native_ss_180mohm_comparison"]
        if (
            ss["normal_start_current_qualified"]
            or ss["selected_css_f"] is not None
            or ss["complete_startup_s"] is not None
        ):
            errors.append(rail + " native SS prematurely selected/qualified")
        for key in [
            "guaranteed_ss_gain_bounds",
            "guaranteed_ss_current_bounds_a",
            "guaranteed_ss_rss_bounds_ohm",
            "guaranteed_ss_offset_bounds_v",
        ]:
            if ss[key] is not None:
                errors.append(rail + " invented SS bound")
        t = row["ltc_fixed_shunt_candidate"]["timer"]
        if t is not None and (
            t["guaranteed_fault_window_s"] is not None or t["guaranteed_initial_delay_s"] is not None
        ):
            errors.append(rail + " typical timer converted to guarantee")
    return errors


def main():
    report = json.loads((ROOT / "comparison.json").read_text())
    errors = claim_errors(report)
    for name, expected in report["source_sha256"].items():
        if sha(REPO / name) != expected:
            errors.append("Stale source:" + name)
    paths = sorted(
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".md", ".json"}
        and p.name != "seal.json"
        and "__pycache__" not in p.parts
    )
    result = dict(
        contract_errors=errors,
        comparison_integrity_accepted=not errors,
        sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        feasibility_qualified=False,
        physical_tests_performed=0,
        canonical_boards_modified=False,
    )
    (ROOT / "seal.json").write_text(json.dumps(result, indent=2) + "\n")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
