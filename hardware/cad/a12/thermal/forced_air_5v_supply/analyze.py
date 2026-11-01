"""Source-bound 5V fan supply and space proposal; no new circuit is adopted."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
P03 = REPO / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined"
CP = REPO / "hardware/cad/a12/thermal/enlarged_base_pot"
FA = REPO / "hardware/cad/a12/thermal/forced_air_prototype"
SEED = REPO / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-seed"
PDN = REPO / "hardware/cad/a12/harness/proposals/processor-awg18-ear-fanout-j29-central-r1-pdn"


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    s, fa = read(ROOT / "source.json"), read(FA / "fan-source.json")
    for path, expected in [
        (s["technical_pdf_external_path"], s["technical_pdf_sha256"]),
        (s["shared_CAD_external_path"], s["shared_CAD_sha256"]),
    ]:
        assert sha(Path(path)) == expected
    assert s["shared_CAD_url"] == fa["cad_url"]
    assert s["shared_CAD_sha256"] == "273e1fcb9e90eb31215dc8758d78b10675ee14def1bc3a9f6269f125e1d75cd0"
    assert s["padded_dimensions_mm"] == fa["dimensions_with_pads_mm"]
    assert s["dimension_tolerance_mm"] == fa["drawing_tolerance_each_dimension_mm"]
    for left, right in [
        ("mounting_pitch_mm", "mounting_pitch_mm"),
        ("pitch_tolerance_mm", "mounting_pitch_tolerance_mm"),
        ("hole_diameter_mm", "mounting_hole_diameter_mm"),
        ("hole_tolerance_mm", "mounting_hole_diameter_tolerance_mm"),
    ]:
        assert s[left] == fa[right]
    tree = ET.parse(P03 / "generated/netlist.xml")
    j3 = {}
    for net in tree.findall("./nets/net"):
        for node in net.findall("node"):
            if node.attrib["ref"] == "J3":
                j3[node.attrib["pin"]] = net.attrib["name"]
    assert j3 == {"1": "/5V_DIG_SRC", "2": "/AGND"}
    cp_scene = CP / "context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"
    line = next(x for x in cp_scene.read_text().splitlines() if x.startswith("ui_native_boards="))
    board = next(x for x in json.loads(line.split("=", 1)[1].rstrip(";")) if x[0] == "P03")
    holes = [h for h in board[4] if h[5] == "J3"]
    assert len(holes) == 2 and all(h[2:4] == [1.0, 1.0] for h in holes)
    world = {h[6]: [h[0] + board[1][0], h[1] + board[1][1]] for h in holes}
    assert world["1"] == [216.0, 112.0] and math.isclose(world["2"][0], 218.54)
    coarse, endpoint = read(PDN / "generated/coarse.json"), read(SEED / "generated/endpoint-R1.json")
    pair = 2 * s["rated_current_a"] * (1 + s["rated_current_tolerance_fraction"])
    provision = 1.2 * pair
    remaining = coarse["reserve_unassigned_a"] - provision
    assert remaining > 0 and math.isclose(provision, 0.132, abs_tol=1e-12)
    assert math.isclose(coarse["known_positive_total_a"] + provision, 2.116, abs_tol=1e-12)
    vlow, vhigh = endpoint["source_voltage_interval_v"]
    dynamic = endpoint["source_dynamic_allocation_v"] + endpoint["local_spread_allocation_v"]
    target = 1.2 * s["starting_voltage_v"]
    sources = [
        Path(__file__),
        ROOT / "source.json",
        FA / "fan-source.json",
        FA / "handoff.json",
        CP / "handoff.json",
        cp_scene,
        P03 / "power_p03.kicad_pcb",
        P03 / "generated/netlist.xml",
        PDN / "generated/coarse.json",
        SEED / "generated/endpoint-R1.json",
    ]
    result = dict(
        scope=__doc__,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        two_fan_rated_current_with_tolerance_a=pair,
        twenty_percent_planning_provision_a=provision,
        previous_unassigned_reserve_a=coarse["reserve_unassigned_a"],
        remaining_unassigned_reserve_a=remaining,
        known_input_plus_fan_provision_a=coarse["known_positive_total_a"] + provision,
        nominal5V_pair_power_with_tolerance_w=2
        * s["rated_power_w"]
        * (1 + s["rated_power_tolerance_fraction"]),
        nominal5V_twenty_percent_fan_power_provision_w=5 * provision,
        modelled_source_voltage_interval_v=[vlow, vhigh],
        assumed_dynamic_and_spread_v=dynamic,
        twenty_percent_starting_voltage_target_v=target,
        remaining_modelled_drop_to_target_before_unknown_signed_terms_v=vlow - dynamic - target,
        catalogue_operating_maximum_v=s["operating_voltage_v"][1],
        source_model_is_not_a_guaranteed_port_or_fan_voltage=True,
        plausible_source_port=dict(
            ref="P03.J3",
            pins=j3,
            world_pin_centres_mm=world,
            drill_mm=1.0,
            exact_header_or_mating_MPN_selected=False,
        ),
        source_is_before_E28_disconnect=True,
        native_circuit_or_PCB_changes=False,
        same_shared_CAD_and_declared_external_receiving_dimensions=True,
        old_FA01_12V_source_substituted=False,
        tach=dict(
            pulses_per_rev=2,
            nominal4500rpm_hz=4500 / 60 * 2,
            illustrative3V3_2k2_pullup_ma=3.3 / 2.2,
            actual_logic_interface_selected=False,
        ),
        required_next_work=[
            "Actual P03.J3 copper/return and source-capacity solve with fan currents",
            "Selected branch protection/current limiting, startup/stall/fault waveform and partial-power proof",
            "Keyed connector/mating/strain and complete source/branch/tach harness CAD",
            "Tach/thermal interlock circuit and firmware with fail-safe startup and fan-loss behavior",
            "Whole-unit heat allocation from existing reserve without double-counting; new installed airflow/thermal/noise tests",
        ],
        startup_stall_fault_peak_bound_a=None,
        fan_health_control_logic_and_tach_pullup_currents_included=False,
        internal_air_path_and_actual_nonbase_heat_paths_designed=False,
        complete_source_to_fan_voltage_interval_v=None,
        electrical_thermal_physical_or_fabrication_qualified=False,
    )
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print("5Vfan planning provision", provision, "A; reserve remaining", remaining, "A; no adopted circuit")


if __name__ == "__main__":
    main()
