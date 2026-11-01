"""Portable native-contract/provenance integrity and unsupported-claim rejection."""

import json

from hardware.cad.a12.thermal.generate import REPO, sha

from .analyze import OUT, ROOT, analyze, read


def errors(a):
    result = []
    if a["native_contract_errors"] or a["native_component_counts"] != dict(E20=49, E19=76):
        result.append("Native pin/value contract failed")
    expected = dict(
        LED_ICC_four=0.360,
        LED_misc_unpartitioned=0.020,
        LED_logic_label=0.380,
        LED_sink_each=0.004,
        LED_sink_24_each_group=0.096,
        LED_sink96=0.384,
        LED_5v_total=0.764,
        Seed_parent5v=1.0,
    )
    if a["retained_current_allocations_a"] != expected:
        result.append("Reserved source/current target silently changed")
    if a["actual_setting_matches_that_row"] or a["actual_LED_all_state_ICC_upper_a"] is not None:
        result.append("Wrong-condition ICC max promoted to actual bound")
    for key in [
        "module_input_max_current_from_reviewed_primary_a",
        "module_3v3_output_max_current_from_reviewed_primary_a",
    ]:
        if a[key] is not None:
            result.append("Invented module current/capacity bound")
    if (
        not a["no_reserves_removed"]
        or a["whole_unit_35v4315_heat_target_revised"]
        or a["actual_power_qualified"]
        or a["physical_tests_performed"] != 0
    ):
        result.append("Unsupported target/physical qualification")
    if a["E20_misc20mA_verified_against_all_components_states"] or a["filter0v5A_screen_is_1A_validation"]:
        result.append("Partial screen represented as complete proof")
    return result


def packet_errors():
    a = read(OUT / "analysis.json")
    result = errors(a)
    if a != analyze():
        result.append("Saved analysis differs from actual captured source/native contracts")
    for p, h in a["source_sha256"].items():
        if not (REPO / p).exists() or sha(REPO / p) != h:
            result.append("Stale audit input:" + p)
    native = read(OUT / "native-export.json")
    for group in [native["source_sha256"], native["artifact_sha256"]]:
        for p, h in group.items():
            if sha(REPO / p) != h:
                result.append("Changed actual native export evidence:" + p)
    if native["full_new_ERC_DRC_claimed"] or any(row["returncode"] != 0 for row in native["exports"]):
        result.append("Wrong native proof scope")
    cap = read(ROOT / "capture.json")
    for row in cap["repository"].values():
        if sha(REPO / row["captured"]) != row["sha256"]:
            result.append("Changed captured repository input")
    for p, h in cap["primary_PDF_sha256"].items():
        if sha(REPO / p) != h:
            result.append("Changed primary PDF")
    return result


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
        if a.get("sha256") == actual and a.get("packet_integrity_accepted") is True
        else ["Changed or rejected audit seal"]
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
        actual_current_qualified=False,
        no_reserve_reduction=True,
        physical_tests_performed=0,
        canonical_modified=False,
        prior_sealed_packets_modified=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(a, indent=2) + "\n")
    if bad:
        raise SystemExit("\n".join(bad))
    print("PA01 native power roles and provenance accepted; actual current bounds remain unqualified.")


if __name__ == "__main__":
    main()
