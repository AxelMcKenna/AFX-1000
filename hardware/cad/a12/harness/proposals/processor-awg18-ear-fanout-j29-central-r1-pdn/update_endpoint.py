"""Recombine frozen source/R1 terms with this new finite matrix, preserving unknowns."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
SEED = ROOT.parent / "processor-awg18-ear-fanout-j29-central-seed"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    original = SEED / "generated/endpoint-R1.json"
    matrix = ROOT / "generated/coarse.json"
    a = json.loads(original.read_text())
    q = json.loads(matrix.read_text())
    resistor = next(r for r in a["R1_candidates"] if r["mpn"] == "WSLT2512R4700FEA")
    assert (
        a["one_ampere_retained_not_reduced"] and resistor["load_a"] == 1 and resistor["nominal_ohm"] == 0.47
    )
    source = a["source_voltage_interval_v"]
    base = (
        source[0]
        - a["source_dynamic_allocation_v"]
        - a["local_spread_allocation_v"]
        - a["source_design_drop_without_unknown_ground_and_socket_v"]
        - resistor["resistance_scenario_ohm"][1]
    )
    intercepts = {n: base - v["seed"][1] for n, v in q["fixture_loop_copper_drop_intervals_v"].items()}
    result = dict(
        source_sha256={
            str(original.relative_to(REPO)): sha(original),
            str(matrix.relative_to(REPO)): sha(matrix),
            str(Path(__file__).relative_to(REPO)): sha(Path(__file__)),
        },
        complete_Seed_report_all41seal_hashes_verified=all(
            sha(SEED / n) == h
            for n, h in json.loads((SEED / "handoff.json").read_text())["files_sha256"].items()
        ),
        new_Seed_VIN_finite_copper_resistance_ohm=q["networks"]["SEED_VIN"]["transfer_resistance_ohm"][
            "seed"
        ]["seed"],
        conditional_intercepts_before_unknown_terms_v=intercepts,
        remaining_unallocated_downward_drop_to_operating4V_v={n: v - 4 for n, v in intercepts.items()},
        unknown_signed_terms=a["unknown_signed_ground_socket_and_network_terms"]
        + ["unassigned0p416Aphysical_endpoint_and_return_are_not_implemented"],
        unassigned_reserve_fixture_at_J14_or_J15_does_not_bound_arbitrary_endpoint=True,
        R1_load_a=1.0,
        R1_resistance_scenario_ohm=resistor["resistance_scenario_ohm"],
        R1_20percent_capacity_or_theta_claim_unchanged=True,
        all_source_copper_contact_and_temperature_allocations_unaccepted=True,
        complete_guaranteed_Seed_VIN_interval_v=None,
        physical_qualified=False,
        fabrication_released=False,
    )
    assert result["complete_Seed_report_all41seal_hashes_verified"]
    (ROOT / "generated/updated-endpoint-intercept.json").write_text(json.dumps(result, indent=2) + "\n")
    print(intercepts)


if __name__ == "__main__":
    run()
