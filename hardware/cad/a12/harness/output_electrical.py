"""Conditional full-network DIGITAL harness resistance comparison.

Reuses the exact P03 source-to-load solver with a scoped, explicitly recorded
replacement for DIG-PROCESSOR resistance on BOTH its positive and return paths.
No source module, canonical PCB, BOM or acceptance target is edited. Catalog DCR
and temperature coefficient are scenarios; measured hot/lifetime limits remain
required. This retained lumped network is not the actual coupled PCB solution.
"""

import json
from pathlib import Path
from unittest.mock import patch

from ..generate import REPO, sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated/output-electrical"


def evaluate(sources, resistance):
    from hardware.electronics.power_distribution.p02 import distribution
    from hardware.electronics.power_distribution.p03 import analysis

    original = distribution.harness_resistance

    def override(harness, contact_max=0.002):
        return resistance if harness == "DIG-PROCESSOR" else original(harness, contact_max)

    # Single-threaded calculation in this CLI only. The context restores the
    # function even on failure; no module or board file is written.
    with patch.object(distribution, "harness_resistance", override):
        result = analysis.endpoints(sources)
    assert distribution.harness_resistance is original
    ground = [e for e in result["ground_edges"] if e["harness"] == "DIG-PROCESSOR"]
    assert ground and all(e["max_ohm"] == resistance for e in ground)
    for row in result["endpoints"].values():
        if "processor" in row["paths"]:
            assert row["paths"]["processor"] == resistance
    return result


def run():
    paths = [
        Path(__file__),
        ROOT / "output-wire-6717.json",
        ROOT / "output-wire-6716.json",
        ROOT / "output-wire-6715.json",
    ]
    paths += [
        REPO / p
        for p in [
            "hardware/electronics/power_distribution/p03/analysis.py",
            "hardware/electronics/power_distribution/p03/spec.py",
            "hardware/electronics/power_distribution/p03/generated/netlist.xml",
            "hardware/electronics/power_distribution/p03/generated/analysis.json",
            "hardware/electronics/power_distribution/p02/distribution.py",
            "hardware/electronics/common/circuits.py",
            "hardware/electronics/common/netlists.py",
            "hardware/wiring/generated/system-interconnect.json",
        ]
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    from hardware.electronics.common.netlists import netlist
    from hardware.electronics.power_distribution.p02 import distribution
    from hardware.electronics.power_distribution.p03 import analysis

    parts, _ = netlist(REPO / "hardware/electronics/power_distribution/p03/generated/netlist.xml")
    sources, details = analysis.source_bounds(parts)
    baseline = analysis.endpoints(sources)
    saved = json.loads(
        (REPO / "hardware/electronics/power_distribution/p03/generated/analysis.json").read_text()
    )
    for name, row in baseline["endpoints"].items():
        for field in ["minimum_v", "maximum_v"]:
            assert abs(row[field] - saved["source_to_load"]["endpoints"][name][field]) < 1e-12, (
                "Baseline solver/inputs differ"
            )
    original = distribution.harness_resistance("DIG-PROCESSOR")
    assert evaluate(sources, original) == baseline, "Explicit baseline override changed unrelated paths"
    scenarios = []
    for part in [6717, 6716, 6715]:
        proposal = json.loads((ROOT / ("output-wire-" + str(part) + ".json")).read_text())
        wire = proposal["wire"]
        if Path(proposal["external_pdf_path"]).exists():
            assert sha(Path(proposal["external_pdf_path"])) == proposal["manufacturer_pdf_sha256"]
        for length in [0.150, 0.200, 0.250]:
            hot = wire["nominal_conductor_dcr_ohm_per_1000ft_at20c"] / 304.8 * length * (1 + 0.00393 * 80)
            for kind, interfaces in [
                ("retained_mated_interfaces_and_escape", 0.005),
                ("proposed_two_solder_joints_and_escape", 0.002),
            ]:
                result = evaluate(sources, hot + interfaces)
                scenarios.append(
                    dict(
                        wire_part=part,
                        awg=wire["awg"],
                        length_per_lead_m=length,
                        screen_wire_temperature_c=100,
                        nominal_hot_wire_resistance_ohm=hot,
                        interface_scenario=kind,
                        interface_plus_escape_ohm=interfaces,
                        total_resistance_per_lead_ohm=hot + interfaces,
                        full_retained_network_result=result,
                    )
                )
    # The resistor solver requires positive Rmax. Use a small finite lower
    # bracket rather than inserting an ideal zero-resistance return edge.
    lo, hi = 1e-8, 0.100
    assert evaluate(sources, lo)["all_pass"] and not evaluate(sources, hi)["all_pass"]
    for _ in range(45):
        mid = (lo + hi) / 2
        if evaluate(sources, mid)["all_pass"]:
            lo = mid
        else:
            hi = mid
    chosen = evaluate(sources, 0.0085)
    overload = evaluate(sources, 0.030)
    assert chosen["all_pass"] and not overload["all_pass"]
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        source_voltage_intervals_v=sources,
        source_interval_assumptions=details,
        baseline_retained_network=baseline,
        baseline_DIG_PROCESSOR_resistance_per_lead_ohm=original,
        scenarios=scenarios,
        conditional_per_lead_resistance_boundary_ohm=[lo, hi],
        proposed_measured_total_per_lead_ohm=0.0085,
        proposed_measured_hot_wire_only_per_lead_ohm=0.0065,
        proposed_per_joint_max_ohm=0.0005,
        additional_two_board_escape_max_ohm=0.001,
        chosen_limit_result=chosen,
        rejected_30mohm_per_lead_result=overload,
        targets_changed=False,
        loads_changed=False,
        return_path_override_applied=True,
        nominal_DCR_used_as_guaranteed_upper=False,
        copper_temperature_coefficient_per_k_assumed=0.00393,
        wire_current_temperature_and_lifetime_qualified=False,
        contacts_copper_and_wire_measured=False,
        actual_PCB_coupled_network_accepted=False,
        fanout_assembly_selected=False,
        receiving_termination_selected=False,
        complete_output_harness=False,
        canonical_BOM_changed=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    assert all(sha(REPO / n) == h for n, h in hashes.items()), "Electrical scenario source changed"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    weakest = min((r["minimum_v"], n) for n, r in chosen["endpoints"].items() if r["rail"] == "DIG")
    print(
        json.dumps(
            dict(
                baseline_per_lead_ohm=original,
                conditional_boundary_ohm=[lo, hi],
                chosen_measured_limit_ohm=0.0085,
                weakest_chosen_DIG_endpoint=weakest,
                canonical_changed=False,
                physical_qualified=False,
            ),
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    run()
