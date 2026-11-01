"""Source-bound partial local current inventory; never a completed thermal ledger.

Only literal resistor paths with stated endpoint assumptions are calculated.
Capacitor leakage, active-device currents and operating-state-dependent loads
are explicitly outstanding. Reserves are not added to loads a second time.
"""

import hashlib
import json
from pathlib import Path

from ...common.netlists import netlist, number
from ...power_distribution.p02.distribution import LOADS
from ...power_distribution.p03.models import disconnect_startup

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def inventory():
    assert LOADS["digital_reserve"][2] == 0.416 and LOADS["analog_reserve"][2] == 0.008
    assert abs(sum(v[2] for v in LOADS.values() if v[0] == "DIG") - 2.4) < 1e-12
    assert abs(sum(v[2] for v in LOADS.values() if v[0] == "ANA") - 0.251) < 1e-12
    startup = disconnect_startup()
    for domain, expected in (("DIG", 0.024), ("ANA", 0.008)):
        row = startup[domain]
        local = (
            row["source_total_startup_current_a"]
            - row["full_load_present_during_startup_a"]
            - row["maximum_capacitor_current_a"]
        )
        assert abs(local - expected) < 1e-12, "P03 local reservation changed: reconcile the inventory"
    native = ROOT / "generated/local-loads-netlist.xml"
    parts, pins = netlist(native)
    metadata = json.loads((ROOT / "components.json").read_text())
    for c in metadata:
        assert parts[c["ref"]].findtext("value") == c["part"]
        for p in c["pins"]:
            if p.get("net"):
                assert pins[c["ref"]][str(p["number"])] == p["net"]

    # Deliberately rounded upper requirements, not measured rail voltages.
    voltages = {"P19": 19.2, "N19": 19.2, "P12": 12.2, "N12": 12.2, "V5_REG": 5.1, "5V_DIG": 5.1}
    paths = [
        ("P19", "protected_bleed", ["R8"], ["P19", "AGND"], 0.03, 0),
        ("N19", "protected_bleed", ["R16"], ["N19", "AGND"], 0.03, 0),
        ("P12", "protected_bleed", ["R24"], ["P12", "AGND"], 0.03, 0),
        ("N12", "protected_bleed", ["R32"], ["N12", "AGND"], 0.03, 0),
        ("V5_REG", "protected_bleed", ["R40"], ["V5_REG", "AGND"], 0.03, 0),
        ("5V_DIG", "protected_bleed", ["R48"], ["5V_DIG", "AGND"], 0.03, 0),
        (
            "P19",
            "source_OV_sense",
            ["R56", "R57", "R58"],
            ["P19_SRC", "P19_SENSE_MID", "P19_OV_SENSE", "AGND"],
            0.0006,
            0,
        ),
        ("P12", "source_OV_sense", ["R65", "R66"], ["P12_SRC", "P12_OV_SENSE", "AGND"], 0.0006, 0),
        ("N19", "source_OV_sense", ["R49", "R50"], ["N19_SRC", "N19_INPUT_MID", "N19_SUM"], 0.0006, 0.010),
        ("N12", "source_OV_sense", ["R53"], ["N12_SRC", "N12_SUM"], 0.0006, 0.010),
        ("V5_REG", "source_OV_sense", ["R73", "R74"], ["V5_REG_SRC", "V5_REG_OV_SENSE", "AGND"], 0.0006, 0),
        ("5V_DIG", "source_OV_sense", ["R78", "R79"], ["5V_DIG_SRC", "5V_DIG_OV_SENSE", "AGND"], 0.0006, 0),
    ]
    for rail, tag, top, bottom, node in (
        ("V5_REG", "source_UV_sense", "R123", "R124", "E28_ANA_SRC_SENSE"),
        ("5V_DIG", "source_UV_sense", "R126", "R127", "E28_DIG_SRC_SENSE"),
        ("V5_REG", "protected_UV_sense", "R129", "R130", "E28_ANA_OUT_SENSE"),
        ("5V_DIG", "protected_UV_sense", "R132", "R133", "E28_DIG_OUT_SENSE"),
    ):
        source = rail + "_SRC" if tag.startswith("source") else rail
        paths.append((rail, tag, [top, bottom], [source, node, "AGND"], 0.0006, 0))
    rows = []
    totals = {rail: 0 for rail in voltages}
    for rail, tag, refs, nodes, tol, end_error in paths:
        for ref, a, b in zip(refs, nodes, nodes[1:]):
            assert {pins[ref]["1"], pins[ref]["2"]} == {a, b}
        resistance = sum(number(parts[r].findtext("value")) for r in refs)
        current = (voltages[rail] + end_error) / (resistance * (1 - tol))
        rows.append(
            dict(
                rail=rail,
                kind=tag,
                native_refs=refs,
                path_nodes=nodes,
                nominal_resistance_ohm=resistance,
                total_resistance_error_requirement=tol,
                endpoint_error_requirement_v=end_error,
                partial_current_requirement_a=current,
                source_power_requirement_w=voltages[rail] * current,
            )
        )
        totals[rail] += current
    paths_bound = [
        Path(__file__),
        ROOT / "components.json",
        ROOT / "rail_disconnect.kicad_sch",
        ROOT / "rail_disconnect.kicad_pcb",
        native,
        ROOT / "auxiliary.py",
        REPO / "hardware/electronics/power_distribution/p02/distribution.py",
        REPO / "hardware/electronics/power_distribution/p03/models.py",
        REPO / "hardware/electronics/power_distribution/p03/bipolar.py",
    ]
    return dict(
        source_sha256={
            str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths_bound
        },
        native_netlist_and_component_metadata_agree=True,
        upper_rail_magnitude_requirements_v=voltages,
        resistor_paths=rows,
        partial_resistive_current_requirements_a=totals,
        existing_allocations=dict(
            protected_DIG_total_a=2.4,
            DIG_reserve_already_inside_total_a=0.416,
            protected_ANA_total_a=0.251,
            ANA_reserve_already_inside_total_a=0.008,
            p03_separate_unreconciled_startup_local_DIG_a=0.024,
            p03_separate_unreconciled_startup_local_ANA_a=0.008,
            p03_bipolar_new_unselected_controller_reserve_each_a=0.003,
            external_AUX_total_a=0.060,
            four_Si8751_AUX_maximum_a=0.038,
        ),
        missing=[
            "TPS259482L input operating/fault/off current across all seven devices and temperatures",
            "Bulk and ceramic leakage at actual voltage, temperature, age and assembly conditions",
            "MCAP capacitor leakage and transient drain-to-driver charge transfer",
            "Complete AUX active/quiescent/delta-ICC and state-dependent resistor/input loads",
            "Actual negative-sense amplifier virtual-ground error and input-bias/load corners",
            "Reconcile local current against existing reserves without silently double-counting",
            "Latest actual downstream-board load inventories and operating-state/dynamic behavior",
            "Unimplemented bipolar startup controller current and sense-network contribution",
        ],
        total_current_ledger_closed=False,
        total_thermal_ledger_closed=False,
        resistor_requirements_physically_accepted=False,
        physical_qualified=False,
    )


if __name__ == "__main__":
    result = inventory()
    (ROOT / "generated/local-loads-partial.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["partial_resistive_current_requirements_a"], indent=2))
