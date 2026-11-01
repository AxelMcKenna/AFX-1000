"""Actual native AUX ownership/state ledger; all unguaranteed bounds explicit."""

import hashlib
import json
import re
from pathlib import Path

import numpy as np

from hardware.electronics.common.netlists import netlist, number

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_data():
    parts, pins = netlist(ROOT / "sources/E28/native-netlist.xml")
    components = json.loads((ROOT / "sources/E28/components.json").read_text())
    assert len(parts) == len(components) == 269
    for c in components:
        assert parts[c["ref"]].findtext("value") == c["part"]
        for p in c["pins"]:
            got = pins[c["ref"]][p["number"]]
            assert got == p["net"] if p["net"] is not None else got.startswith("unconnected-"), (
                c["ref"],
                p["number"],
            )
    return parts, pins, components


def power_run(top=150, rd_error=0.03, loop=250, source_extra=5e-6, dest_extra=22e-6):
    """Actual source/leaf two-node DC circuit, with both real pulldowns."""
    p03, _ = netlist(ROOT / "sources/P03/generated/complete-scratch-netlist.xml")
    nf = json.loads((ROOT / "sources/NF05R/generated/analysis.json").read_text())
    vsrc = nf["AUX_source_applicability"]["source_P03_corner_v"]
    rd = 10000 * (1 - rd_error)
    rp = number(p03["R112"].findtext("value")) * 0.97
    ru = top * 1.03
    # Source S has R112; destination D has R93. The complete250ohm leaf
    # already INCLUDES the100ohm hot-photorelay receiving requirement.
    G = np.array([[1 / ru + 1 / rp + 1 / loop, -1 / loop], [-1 / loop, 1 / loop + 1 / rd]])
    s, d = np.linalg.solve(G, [vsrc[0] / ru - source_extra, -dest_extra])
    return dict(
        resistor_nominal_ohm=top,
        source_min_v=vsrc[0],
        source_node_min_v=float(s),
        E28_RUN_min_v=float(d),
        R112_low_ohm=rp,
        R93_low_ohm=rd,
        R113_high_ohm=ru,
        complete_leaf_loop_receiving_ohm=loop,
        contact_max_included_in_loop_ohm=100,
        source_extra_sink_receiving_a=source_extra,
        destination_input_board_sink_receiving_a=dest_extra,
        receiving_HIGH_v=2.0,
        target_times1p2_v=2.4,
        target_margin_v=float(d) - 2.4,
        short_current_at2p7_a=2.7 / (top * 0.97),
        short_power_at2p7_w=2.7**2 / (top * 0.97),
        short_current_times1p2_a=1.2 * 2.7 / (top * 0.97),
        short_power_times1p2_w=1.2 * 2.7**2 / (top * 0.97),
        R93_open_harness_high_limit_ohm=10000 * (1 + rd_error),
        disconnected_HIGH_leaks_receiving_a=32e-6,
        disconnected_max_v=32e-6 * 10000 * (1 + rd_error),
        disconnected_times1p2_v=1.2 * 32e-6 * 10000 * (1 + rd_error),
        continuous_Schmitt_threshold_enclosure_at2p5_to2p7_is_receiving=True,
        physical_switch_contact_leak_and_ground_offsets_accepted=False,
    )


def ledger(slow_input_extra=0.0005, legacy_extra=0.0005):
    actual, pins, components = source_data()
    r = {ref: number(c.findtext("value")) for ref, c in actual.items() if ref.startswith("R")}
    families = {}
    for c in components:
        if c["ref"].startswith("U"):
            families.setdefault(c["part"], []).append(c["ref"])
    small = families["SN74LVC3G17DCUR"]
    assert len(small) == 8
    active3 = [
        (c["ref"], p["number"], p["net"])
        for c in components
        if c["ref"] in small
        for p in c["pins"]
        if p["kind"] == "input" and p["net"] != "AGND"
    ]
    assert len(active3) == 22
    oc = {p["net"] for c in components for p in c["pins"] if p["kind"] == "open_collector" and p["net"]}
    pulls = {}
    for ref, v in r.items():
        ns = set(pins[ref].values())
        if "V2V5_AUX" in ns:
            other = next(n for n in ns if n != "V2V5_AUX")
            if other in oc:
                pulls[ref] = dict(net=other, ohm=v)
    assert len(pulls) == 21, len(pulls)
    master_pairs = [("R4", "R5"), ("R12", "R13"), ("R20", "R21"), ("R28", "R29")]
    push = {
        p["net"]
        for c in components
        if c["ref"].startswith("U")
        for p in c["pins"]
        if p["kind"] == "output" and p["net"]
    }
    logic_pd = {
        ref: v
        for ref, v in r.items()
        if "AGND" in pins[ref].values() and any(n in push for n in pins[ref].values()) and ref != "R94"
    }
    assert not {"R93", "R142", "R143"} & set(logic_pd)
    # Actual divider paths, not one full-rail current per series resistor.
    direct_dividers = [["R83", "R84"], ["R88", "R89"], ["R137", "R138", "R139"]]
    div_current = sum(2.7 / (sum(r[x] for x in row) * 0.97) for row in direct_dividers)
    nf = json.loads((ROOT / "sources/NF05R/components.json").read_text())
    nr = {
        c["ref"]: number(re.match(r"^[0-9.]+[kM]?", c["part"]).group(0))
        for c in nf
        if c["ref"].startswith("R")
    }
    nfref = [
        ["R25", "R26", "R27"],
        ["R29", "R30", "R31"],
        ["R33", "R34", "R35"],
        ["R42", "R43", "R44"],
        ["R46", "R47"],
        ["R49", "R50", "R51"],
    ]
    reference_source = (
        sum(1.2625 / (sum(nr[x] for x in row) * 0.97) for row in nfref) + 1.2625 / (r["R94"] * 0.97) + 2e-6
    )
    # No-load supply current is separate from output/resistor current. These
    # are their table test points, NOT certified2.5V/all-input-voltage bounds.
    icc = dict(
        Si8751_ON_four=0.038,
        Si8751_OFF_four_receiving=0.0004,
        LVC3G17_no_load_8=8 * 10e-6,
        LVC_ordinary_no_load_10=10 * 40e-6,
        AUP_no_load_4=4 * 1.7e-6,
        TLV1824_12_channels=12 * 10e-6,
        OPA2333_2_channels_at_table_test_voltage=2 * 28e-6,
        REF35_no_load=2.6e-6,
        TPS3890_2=2 * 6.5e-6,
    )
    assert sum(c["part"].startswith("SN74LVC") and c["part"] != "SN74LVC3G17DCUR" for c in components) == 10
    assert sum(c["part"] == "SN74AUP2G08DCUR" for c in components) == 4
    regular_inputs = [
        (c["ref"], p["number"], p["net"])
        for c in components
        if c["ref"].startswith("U") and c["part"].startswith("SN74LVC") and c["part"] != "SN74LVC3G17DCUR"
        for p in c["pins"]
        if p["kind"] == "input" and p["net"] not in ["AGND", "POWER_RUN", "P03_SOURCES_READY"]
    ]
    aup_inputs = [
        (c["ref"], p["number"], p["net"])
        for c in components
        if c["part"] == "SN74AUP2G08DCUR"
        for p in c["pins"]
        if p["kind"] == "input" and p["net"] != "AGND"
    ]
    # NewSchmitt INPUT leak on a LOW open-drain node is already inside its
    # full-rail pullup current; don't add it again. Push-pull receiver loads
    # below are counted once, not as output drive-capability table maxima.
    input_push_load = len(regular_inputs) * 5e-6 + len(aup_inputs) * 0.5e-6
    all_no_load = sum(v for k, v in icc.items() if not k.startswith("Si8751"))
    startup_low = {
        "ANA_PG0",
        "ANA_PG1",
        "ANA_PG2",
        "DIG_PG0",
        "DIG_PG1",
        "DIG_PG2",
        "DIG_PG3",
        "ANA_OUTPUT_OK",
        "DIG_OUTPUT_OK",
        "E28_TIMEOUT_RAW",
    }
    assert startup_low <= {x["net"] for x in pulls.values()}
    scenarios = []
    for name, drivers, low, enabled_pd in [
        ("healthy_settled", True, set(), True),
        ("positive_startup_valid_sources", True, startup_low, True),
        ("valid_AUX_RUN_low_or_fault_latched", False, {x["net"] for x in pulls.values()}, False),
        (
            "uncorrelated_all_OC_low_but_drivers_still_ON_TRANSIENT_ONLY",
            True,
            {x["net"] for x in pulls.values()},
            True,
        ),
    ]:
        pull_low = sum(2.7 / (x["ohm"] * 0.97) for x in pulls.values() if x["net"] in low)
        high_count = len(pulls) - len(low)
        off_and_input = high_count * (2e-6 + 1e-6)
        pd = sum(2.7 / (v * 0.97) for v in logic_pd.values()) if enabled_pd else 0
        si_pds = sum(2.7 / ((r[a] + r[b]) * 0.97) for a, b in master_pairs) if drivers else 0
        terms = dict(
            Si8751_supply=icc["Si8751_ON_four"] if drivers else icc["Si8751_OFF_four_receiving"],
            all_other_no_load=all_no_load,
            actual_AUX_dividers=div_current,
            PROTECT_REF_output_including_NF_six_dividers=reference_source,
            OPA_output_DC_receiving=0.00035,
            actual_pushpull_pulldowns=pd,
            actual_MASTER_to_Si_IN_resistor_loads=si_pds,
            OC_LOW_pullup_branch_total=pull_low,
            OC_HIGH_off_and_Schmitt_input_leaks_receiving=off_and_input,
            pushpull_to_LVC_AUP_input_leaks_receiving=input_push_load,
            Si_logic_input_extra_receiving=0.0002 if drivers else 0,
            external_E28_pushpull_output_total_receiving=0.0005,
            all22_Schmitt_extra_receiving=len(active3) * slow_input_extra,
            legacy_logic_dynamic_nonrail_extra_receiving=legacy_extra,
        )
        total = sum(terms.values())
        scenarios.append(
            dict(
                name=name,
                all_terms_a=terms,
                raw_receiving_sum_a=total,
                guarded_sum_a=1.2 * total,
                LOW_OC_count=len(low),
                HIGH_OC_count=high_count,
                all_joint_static_current_and_temperature_bounds_accepted=False,
            )
        )
    healthy = scenarios[0]["raw_receiving_sum_a"]
    extra_allow = (0.060 / 1.2 - (healthy - len(active3) * slow_input_extra)) / len(active3)
    return dict(
        native_E28_parts=269,
        families=families,
        active_Schmitt_inputs=active3,
        eight_packages_seven_additional=True,
        OC_pullups=pulls,
        direct_AUX_divider_series_paths=direct_dividers,
        internal_output_pulldowns=logic_pd,
        MASTER_series_and_PD_pairs=master_pairs,
        excluded_external_resistors={
            "R93": "P03R113 source path",
            "R142": "P03R316 READY pullup source allocation",
            "R143": "NF05R externaloutput0.5mA allocation",
        },
        actual_NF_reference_series_paths=nfref,
        IC_no_load_table_or_receiving_values_a=icc,
        ordinary_LVC_receiving_input_count=len(regular_inputs),
        AUP_receiving_input_count=len(aup_inputs),
        prototype_IC_temperature_receiving_max_C=85,
        industrial_Si8751_operating_max_C=105,
        whole_board125C_operating_proof=False,
        Schmitt_extra_per_active_input_receiving_a=slow_input_extra,
        legacy_nonrail_extra_receiving_a=legacy_extra,
        maximum_Schmitt_extra_to_fit60mA_guarded_receiving_a=extra_allow,
        primary_DeltaICC500uA_starts3V_NOT_actual2p5_guarantee=True,
        old_LVC125C_DeltaICC5mA_rows_NOT_typical500uA=True,
        Si8751_38mA_row_conditions="IN=VDD,TTexact10k; not guaranteed actualIN>=VIH/TTtol/switching",
        Si8751_OFF_140nA_is_typical_not_upper=True,
        complete_hot_VDD_VI_TT_static_dynamic_physical_bound_a=None,
        scenarios=scenarios,
    )


def p03_state_current(run_resistor=3300, separate_leaf=False):
    c, pins = netlist(ROOT / "sources/P03/generated/complete-scratch-netlist.xml")
    r = {ref: number(x.findtext("value")) for ref, x in c.items() if ref.startswith("R")}
    # The resistor changes here only as an explicit successor comparison.
    r["R113"] = run_resistor
    fixed = (
        2.7 / (r["R111"] * 0.97)
        + 2.7 / ((r["R118"] + r["R119"]) * 0.997)
        + 2.7 / ((r["R108"] + r["R130"] + r["R109"]) * 0.997)
    )
    state = []
    for name, run_short in [
        ("sources_good_RUN_high", False),
        ("RUN_short_fault_AUX_held_upper_stress", True),
    ]:
        if run_short:
            terms = dict(
                always_on_bleed_reference_feedback=fixed,
                R113_RUN_short=2.7 / (r["R113"] * 0.97),
                R110_POWER_READY_low=2.7 / (r["R110"] * 0.97),
                R316_SOURCES_READY_low=2.7 / (r["R316"] * 0.97),
                R246_buckPG_low=2.7 / (r["R246"] * 0.97),
                FAST_OV_gate_and_feedback=2.7 / (r["R120"] * 0.97) + 2.7 / (r["R117"] * 0.97),
                U25_U26_U103_active_and_leak_reserve=0.003,
            )
        else:
            # Source2.7V/lowR gives an upper normalcurrent, with all stated
            # input sinks. Actual output voltage feasibility is separate.
            ru = r["R113"] * 0.97
            rp = r["R112"] * 0.97
            rd = 10000 * 0.97
            rc = 250
            s, d = np.linalg.solve(
                [[1 / ru + 1 / rp + 1 / rc, -1 / rc], [-1 / rc, 1 / rc + 1 / rd]], [2.7 / ru - 5e-6, -22e-6]
            )
            run_i = (2.7 - s) / ru
            if separate_leaf:
                # New supervisor senses RUN; external E28 current is sourced
                # by the separate high-side leaf, never through PG/R113.
                local_sink = 5e-6
                local = (2.7 / ru - local_sink) / (1 / ru + 1 / rp)
                run_i = (2.7 - local) / ru
            ready_i = (2.7 + 22e-6 * 15000 * 0.98) / (r["R316"] * 0.97 + 15000 * 0.98)
            terms = dict(
                always_on_bleed_reference_feedback=fixed,
                R113_RUN_high=float(run_i),
                R110_POWER_READY_off_leak_receiving=2e-6,
                R316_READY_high_total=ready_i,
                R246_buckPG_off_leak_receiving=2e-6,
                FAST_OV_feedback_conservative=2.7 / (r["R117"] * 0.97),
                U25_U26_U103_active_and_leak_reserve=0.003,
            )
        state.append(
            dict(
                name=name,
                terms_a=terms,
                raw_receiving_sum_a=sum(terms.values()),
                guarded_sum_a=1.2 * sum(terms.values()),
            )
        )
    return state


def leaf():
    """Literal schematic and conditional DC comparisons; no timing inference."""
    nf = json.loads((ROOT / "sources/NF05R/generated/analysis.json").read_text())
    vlo = nf["AUX_source_applicability"]["source_P03_corner_v"][0]
    # The two FETs together are allocated2ohm at|VGS|>=1.8 across0..85C.
    # This is receiving, not the 25C transistor's -2.5V RON guarantee.
    force = 2 + 100 * 1.03 + 250
    high = (vlo - force * 22e-6) / (1 + force / (10000 * 0.97))
    gate_low = (vlo / (100000 * 1.03) - (0.25 + 0.5 + 0.1) * 1e-6) / (
        1 / (100000 * 1.03) + 1 / (1000000 * 0.97)
    )
    off_run = (10 + 1 + 0.1 + 1) * 1e-6 * (47000 * 1.03)
    por_load = 0.8 / (100000 * 0.97) + (1 + 0.5 + 0.1) * 1e-6
    off_pmos_vgs = (100 + 2 * 1 + 0.1) * 1e-6 * (1000 * 1.03)
    boot_s = vlo - 0.6
    boot_gate = 3e-3 * 1
    branch = (2.7 - high) / (force)  # only diagnostic; upper current separately below
    del branch
    bias = 2.7 / (1000 * 0.97) + 2.7 / (100000 * 0.97) + 6.5e-6 + 2e-6 + 2e-6
    normal_output = (2.7 + 22e-6 * 9700) / (100 * 0.97 + 250 + 9700)
    short = 2.7 / (100 * 0.97)
    return dict(
        native_parts=14,
        integrated_new_parts=12,
        bench_headers=2,
        actual_physical_pin_roles=dict(
            U1={
                "1": "POWER_RUN_INTERNAL",
                "2": "AGND",
                "3": "AUX",
                "4": "AUX",
                "5": "RUN_CT",
                "6": "RUN_GATE_COMMAND",
            },
            Q1={"1": "RUN_GATE_COMMAND", "2": "AGND", "3": "PMOS_GATES"},
            Q2={"1": "PMOS_GATES", "2": "PMOS_COMMON_SOURCE", "3": "AUX"},
            Q3={"1": "PMOS_GATES", "2": "PMOS_COMMON_SOURCE", "3": "PRELIMIT"},
            D1={"1": "AUX", "2": "RUN_GATE_COMMAND"},
        ),
        original_R113_ohm=3300,
        original_PG_and_guard_RUN_unchanged=True,
        external_destination="P03J106.3 -> FH normally-open contact -> E28J5.3 ONLY",
        external_force_series_pair_ohm_receiving=2,
        series_resistor_complete_fraction=0.03,
        FH_contact_included_in_250ohm_loop=True,
        steady_HIGH_receiving_v=high,
        high_target1p2_v=2.4,
        steady_HIGH_receiving_margin_v=high - 2.4,
        input_gate_HIGH_receiving_v=gate_low,
        NMOS_ON_1ohm_at_VGS2V_is_receiving=True,
        fixed1p15_supervisor_release_max_v=1.157 * 1.01,
        old_internal_RUN_open_max_receiving_v=off_run,
        PG_LOW_sink_current_upper_at_VOLp4_a=(2.7 - 0.4) / (3300 * 0.97) + 11.1e-6,
        PG_LOW_current_table_a=0.001,
        POR_pulldown_test_current_a=15e-6,
        POR_max_pullup_gate_leak_current_a=por_load,
        POR_current_times1p2_a=por_load * 1.2,
        RESET_LOW_primary_scope="VPORmax0.8V < VDD <1.5V; VOL0.2 at15uA. BelowVPOR undefined.",
        gate_LOW_max_receiving_v=0.25,
        PMOS_OFF_gate_source_max_receiving_v=off_pmos_vgs,
        PMOS_OFF_required_total_source_leak_a=10e-6,
        PMOS_OFF_leak_at_nonzero_VGS_is_NOT_guaranteed_by_IDSS_VGS0=True,
        destination_open_leak_total_a=32e-6,
        destination_open_max_receiving_v=32e-6 * 10300,
        destination_open_times1p2_v=1.2 * 32e-6 * 10300,
        destination_open_target_v=0.4,
        bootstrap_required_body_diode_VF_max_v=0.6,
        bootstrap_source_floor_receiving_v=boot_s,
        bootstrap_NMOS_drain_max_receiving_v=boot_gate,
        bootstrap_initial_abs_VGS_floor_receiving_v=boot_s - boot_gate,
        bootstrap_PMOS_pair_RON_required_max_ohm_at_VGS1p8_hot=2,
        bootstrap_diode_VF_at3mA_hot_qualified=False,
        bootstrap_finite_gate_charge_and_node_capacitance_upper_c=None,
        bootstrap_turnon_time_upper_s=None,
        conditional_steady_high_is_NOT_selfstart_proof=True,
        normal_leaf_bias_raw_a=bias,
        normal_output_source_raw_a=normal_output,
        normal_total_raw_a=bias + normal_output,
        normal_total_guarded_a=1.2 * (bias + normal_output),
        short_output_raw_a=short,
        short_total_raw_a=bias + short,
        short_total_guarded_a=1.2 * (bias + short),
        output_resistor_short_power_w=2.7**2 / (100 * 0.97),
        output_resistor_short_power_times1p2_w=1.2 * 2.7**2 / (100 * 0.97),
        TNPW1206_general_mode_conditional_P85_w=0.27 * (125 - 85) / (125 - 70),
        extra_local_nominal_input_cap_f=200e-9,
        extra_local_max_input_cap_f=200e-9 * 1.1 * 1.15,
        CT_nominal_f=10e-9,
        max_local_known_input_charge_at2p7_c=200e-9 * 1.1 * 1.15 * 2.7,
        CT_charge_current_min_a=0.9e-6,
        CT_charge_current_max_a=1.35e-6,
        reset_fall_propagation_table_typical_only=True,
        loaded_cutoff_upper_s=None,
        below0p8V_partial_power_safe=False,
        reverse_feed_and_independent_AUX_ground_domains_qualified=False,
        complete_hot_off_on_bootstrap_driver_bounds_qualified=False,
        receiving_requires=dict(
            NMOS_RON_at_VGS_ge2p0_max_ohm=1,
            NMOS_drain_leak_at_VGS_le_p25_max_a=100e-6,
            PMOS_each_gate_leak_max_a=1e-6,
            NMOS_gate_leak_max_a=0.5e-6,
            clamp_reverse_leak_max_a=1e-6,
            clamp_VF_at_small_current_max_v=0.25,
            board_gate_leak_max_a=0.1e-6,
            temperature_C=[0, 85],
        ),
        adopted=False,
        PCB_implemented=False,
        physical_qualified=False,
    )


def analyze():
    l = ledger()
    p = p03_state_current(3300, separate_leaf=True)
    proposed = leaf()
    cases = [power_run(r) for r in [3300, 680, 560, 470, 402, 390, 330, 220, 200, 180, 150, 100]]
    for c in cases:
        c["PG_required_sink_at_VOLp4_a"] = (2.7 - 0.4) / (c["resistor_nominal_ohm"] * 0.97) + 11.1e-6
        c["PG1mA_row_supported"] = c["PG_required_sink_at_VOLp4_a"] <= 0.001
        c["HIGH_target_supported"] = c["target_margin_v"] >= 0
        c["joint_value_only_feasible"] = c["PG1mA_row_supported"] and c["HIGH_target_supported"]
    rd = 9700
    rp = 47000 * 0.97
    d = 2.4
    idrain = d / rd + 22e-6
    s = d + 250 * idrain
    max_nom = (cases[0]["source_min_v"] - s) / (idrain + s / rp + 5e-6) / 1.03
    min_nom = (2.7 - 0.4) / (0.001 - 11.1e-6) / 0.97
    e = {x["name"]: x for x in l["scenarios"]}
    # The sealed NF allocation inherited a reference-source charge. Move it
    # to its actual REF35/E28 source once, without consuming NF headroom twice.
    nf_ref_overlap_guarded = 1.2 * 6 * 1.253 / (100000 * 0.999)
    pool = []
    for name, en, pn, nfn, leaf_a in [
        (
            "normal_steady",
            e["healthy_settled"]["guarded_sum_a"],
            p[0]["guarded_sum_a"],
            0.011,
            proposed["normal_total_guarded_a"],
        ),
        (
            "positive_startup",
            e["positive_startup_valid_sources"]["guarded_sum_a"],
            p[0]["guarded_sum_a"],
            0.011,
            proposed["normal_total_guarded_a"],
        ),
        (
            "fault_latched_internal_RUN_low",
            e["valid_AUX_RUN_low_or_fault_latched"]["guarded_sum_a"],
            p[1]["guarded_sum_a"],
            0.014,
            1.2 * 50e-6,
        ),
        (
            "leaf_short_before_E28_logic_settles_TRANSIENT_NOT_CLOSED",
            e["healthy_settled"]["guarded_sum_a"],
            p[0]["guarded_sum_a"],
            0.011,
            proposed["short_total_guarded_a"],
        ),
        (
            "unconstrained_overlap_NOT_closed",
            e["uncorrelated_all_OC_low_but_drivers_still_ON_TRANSIENT_ONLY"]["guarded_sum_a"],
            p[1]["guarded_sum_a"],
            0.014,
            proposed["short_total_guarded_a"],
        ),
    ]:
        nf_at_AUX = nfn - nf_ref_overlap_guarded
        unique = en + pn + nf_at_AUX + leaf_a
        # Keep the original complete NF11/14mA receiving reserve. The
        # re-owned reference charge is displayed as spare reserve, not spent.
        total = unique + nf_ref_overlap_guarded
        pool.append(
            dict(
                name=name,
                E28_guarded_a=en,
                P03_guarded_a=pn,
                NF_guarded_allocation_a=nfn,
                new_leaf_guarded_receiving_a=leaf_a,
                NF_AUX_partition_after_reference_ownership_a=nf_at_AUX,
                unique_source_subtotal_a=unique,
                preserved_NF_full_reserve_headroom_a=nf_ref_overlap_guarded,
                inherited_NF_reference_overlap_moved_to_E28_a=nf_ref_overlap_guarded,
                source_total_receiving_a=total,
                margin_to90mA_a=0.090 - total,
                numerical_receiving_screen_inside90mA=total <= 0.09,
                actual_complete_temporal_correlation_and_current_bound_accepted=False,
            )
        )
    return dict(
        revision="AX01-AUX-state-partition-and-POWER_RUN-conditional-leaf",
        E28=l,
        P03_unchanged3300_local_state_loads=p,
        POWER_RUN_value_comparisons=cases,
        value_only_repair_REJECTED=True,
        value_only_HIGH_requires_nominal_R113_at_most_ohm=max_nom,
        value_only_PG1mA_requires_nominal_R113_at_least_ohm=min_nom,
        value_only_feasible_intersection_empty=min_nom > max_nom,
        rejected150_HIGH_comparison=next(x for x in cases if x["resistor_nominal_ohm"] == 150),
        no_R113_value_change_or_original_P03_edit=True,
        conditional_new_leaf=proposed,
        old_full_resistor3p3k_model_P03_local_a=0.0057456836 + 0.003,
        old60plusNF14plus7new2mAplusP03_local_a=0.060 + 0.014 + 0.014 + 0.0057456836 + 0.003,
        NF_allocations_already_guarded_normal_fault_a=[0.011, 0.014],
        inherited_NF_reference_overlap_moved_to_actual_REF35_source_guarded_a=nf_ref_overlap_guarded,
        source_output_part="TPS7A1601DGNR",
        source_output_current_rating_a=0.100,
        existing_source_output_planning_pool_a=0.090,
        no_source_pool_increase=True,
        pool_scenarios=pool,
        output_loads_and_oc_branches_are_not_counted_twice=True,
        complete_unknown_source_current_upper_a=None,
        complete_turnoff_transition_and_restart_current_qualified=False,
        source_ldo_thermal_and_dynamic_stability_qualified=False,
        proposed_integrated_P03_PCB_successor_implemented=False,
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "analyze.py",
                ROOT / "leaf/design.py",
                ROOT / "leaf/generated/netlist.xml",
                ROOT / "sources/E28/components.json",
                ROOT / "sources/E28/native-netlist.xml",
                ROOT / "sources/P03/generated/complete-scratch-netlist.xml",
                ROOT / "sources/NF05R/generated/analysis.json",
                ROOT / "sources/FH02/generated/analysis.json",
                ROOT / "sources/NF05S/analysis.json",
            ]
        },
        physical_qualified=False,
        fabrication_released=False,
    )


if __name__ == "__main__":
    assert not (ROOT / "handoff.json").exists()
    r = analyze()
    (ROOT / "generated/analysis.json").write_text(json.dumps(r, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: r[k]
                for k in [
                    "value_only_HIGH_requires_nominal_R113_at_most_ohm",
                    "value_only_PG1mA_requires_nominal_R113_at_least_ohm",
                    "pool_scenarios",
                ]
            },
            indent=2,
        )
    )
