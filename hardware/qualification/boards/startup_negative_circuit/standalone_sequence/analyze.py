"""NF05S conditional sequencing/current requirements, never physical bounds."""

import collections
import hashlib
import json
import math
from pathlib import Path

from hardware.electronics.power_distribution.p03.models import constant_power_feed
from hardware.qualification.boards.startup_negative_circuit.compact.analyze import feed

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def timing():
    # Primary tRST=170..230ms. CT discharge and complete leakage limits below
    # are explicit receiving conditions; TPS3890 RCT=200ohm is TYPICAL only.
    cmin, cmax = 47e-9 * 0.94, 47e-9 * 1.06
    imin, imax, ileak = 0.9e-6, 1.35e-6, 0.05e-6
    delay = [(1.17 - 0.1) * cmin / (imax + ileak), 1.29 * cmax / (imin - ileak) + 0.0005]
    rdis = 1000
    asymptote = rdis * (imax + ileak)
    discharge = rdis * cmax * math.log((1.29 - asymptote) / (0.1 - asymptote)) + 0.0005
    rows = {}
    for rail, cap in [("N19", 56), ("N12", 33)]:
        rows[rail] = dict(
            watchdog_interval_s=[
                (77.4 * cap * 0.9 + 55) * 0.905 / 1000,
                (77.4 * cap * 1.1 + 55) * 1.095 / 1000,
            ],
            start_delay_interval_s=delay,
            maximum_wait_before_start_given_SAFE_s=0.230 + delay[1],
            maximum_pre_SAFE_wait_s=(77.4 * cap * 1.1 + 55) * 1.095 / 1000 + 0.230,
            power_conduction_window_excludes_pre_SAFE_wait=True,
            maximum_power_conduction_s=None,
            loaded_hardoff_maximum_s=None,
            fault_SOA_qualified=False,
        )
    return dict(
        rails=rows,
        CT_discharge_requirement_ohm=rdis,
        CT_reset_response_requirement_s=0.0005,
        CT_discharge_to_100mV_conditional_s=discharge,
        minimum_recognized_GLOBAL_OFF_requirement_s=0.001,
        actual_E28_GLOBAL_OFF_minimum_verified=False,
        bank_clamp_release_and_gate_settled_requirement_s=0.025,
        delay_has20pct_over_release_requirement=delay[0] >= 1.2 * 0.025,
        CT_discharge_requirement_met_conditionally=discharge < 0.001,
        specified_current_and_thresholds_are_not_full_delay_guarantee=True,
        timing_qualified=False,
    )


def armed_state(old, global_valid, permit_d):
    """Settled SR equation, RESET wins. SAFE is intentionally absent."""
    return bool(global_valid and (old or permit_d))


def analyze():
    parts = json.loads((ROOT / "components.json").read_text())
    count = collections.Counter(c["part"] for c in parts if c["ref"].startswith("U"))
    p = json.loads((ROOT / "sources/nf03c-parameters.json").read_text())
    p["complete_delivered_module_voltage_requirement_v"] = [22.8, 25.2]
    p["feed_series_resistors_ohm"] = [402, 402]
    f = feed(p)
    # Count packages, not the old 150uA aggregate. All complete operating
    # provisions include uncharacterized slow-input excess where applicable.
    provisions = [
        ("HCS_packages", sum(v for k, v in count.items() if k.startswith("SN74HCS")), 100e-6),
        ("AUP2G14_packages", count["SN74AUP2G14DCKR"], 101e-6),
        ("AUP1G74_packages", count["SN74AUP1G74DCUR"], 51e-6),
        ("LVC2T45_AUX_domains", count["SN74LVC2T45DCUR"], 104e-6),
        ("AUX_LVC1G17_packages", count["SN74LVC1G17DCKR"], 110e-6),
        ("TPS3431_packages", count["TPS3431SDRBR"], 19e-6),
        ("new_AUX_TPS3890_only", 2, 7.85e-6),
    ]
    ledger = [
        dict(
            item=n,
            count=nparts,
            complete_per_part_receiving_a=i,
            subtotal_a=nparts * i,
            manufacturer_bound_transferred=False,
        )
        for n, nparts, i in provisions
    ]
    # Four other TPS3890s float on controller INTVCC and are in feed(), not AUX.
    statics = dict(
        OC_10k_pullups_12=12 * 2.7 / (10000 * 0.97),
        external_47k_pulldowns_9=9 * 2.7 / (47000 * 0.97),
        comparators_6=6 * 40e-6,
        opamps_2=2 * 28e-6,
        six_reference_dividers=6 * 1.253 / (100000 * 0.999),
        new_ARM_SENSE_and_board_leak_requirement=10e-6,
    )
    total = sum(r["subtotal_a"] for r in ledger) + sum(statics.values())
    fault = total + 4 * (510e-6 - 110e-6)
    old = json.loads((ROOT / "sources/nf03c-analysis.json").read_text())["power"]
    module_delta = f["both_module_input_power_requirement_w"] - old["new_isolated_module_input_requirement_w"]
    protected = old["protected_constant_power_requirement_w"] + module_delta + 0.120
    point = constant_power_feed(11.4, 0.36, protected, 0.090)
    capacity = old["new_enclosing_whole_inside_heat_requirement_w"] + module_delta + 0.120
    return dict(
        revision="NF05S-conditional-249",
        timing=timing(),
        module_feed=dict(
            **f,
            initial_output_power_w=25.2 * f["vin_zero_feed_current_upper_given_module_requirement_a"],
            initial_20pct_power_w=1.2 * 25.2 * f["vin_zero_feed_current_upper_given_module_requirement_a"],
            min_voltage_applies_only_settled_not_0V_startup=True,
            module_22p8V_before_first_ARM_correlation_implemented=False,
            output_rating_w=1.0,
            output_voltage_max_applies_startup_no_load_and_transients=True,
        ),
        AUX=dict(
            package_ledger=ledger,
            other_receiving_ledger_a=statics,
            normal_static_receiving_a=total,
            normal20pct_a=1.2 * total,
            normal_receiving_allocation_a=0.009,
            nonrail_fault_static_receiving_a=fault,
            fault20pct_a=1.2 * fault,
            fault_receiving_allocation_a=0.011,
            within_existing_source_pool_a=0.090,
            full_source_pool_partition_accepted=False,
            four_floating_TPS3890_not_doublecounted=True,
        ),
        power=dict(
            DIG_receiving_a=2.42,
            module_input_delta_w=module_delta,
            guarded_capacity_heat_screen_w=capacity,
            normal_protected_constant_power_w=protected,
            normal_inlet_point=point,
            source_AUX_90mA_pool_not_incremented=True,
            normal_and_capacity_corners_distinct=True,
            all_supplied_power_inside_no_fan_heat_credit=True,
            fault_stall_and_standby_heat_not_bounded=True,
        ),
        integration=dict(
            external_ARM_START_removed=True,
            ARM_held_until_GLOBAL_OFF=True,
            missing_SAFE_wait_watchdog_enabled=True,
            sequential_N12_requires_N19_protected_complete=True,
            intermediate_AUX_corruption_hardoff_implemented=False,
            source_current_and_voltage_qualified=False,
        ),
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "components.json",
                ROOT / "analyze.py",
                ROOT / "circuit.py",
                ROOT / "generated/netlist.xml",
                ROOT / "generated/native-review.json",
            ]
        },
        physical_qualified=False,
        startup_qualified=False,
        release_approved=False,
    )


if __name__ == "__main__":
    result = analyze()
    (ROOT / "generated/analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(parts=249, timing=result["timing"], AUX=result["AUX"], power=result["power"]), indent=2
        )
    )
