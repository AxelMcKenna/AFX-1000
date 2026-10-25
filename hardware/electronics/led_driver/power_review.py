"""Reconcile the actual E21 ledger and switch banks with E20's declared load.

Historical A06/E20 failed screens remain in the immutable review package. This
uses the current circuit allocations once, without adding the LED delta twice.
Physical current, sequencing, stability and thermal limits remain unqualified.
"""

import json
import math
from pathlib import Path

from ..common.reports import sha

ROOT = Path(__file__).resolve().parent


def reconcile(led_allocation):
    records = {}
    sources = []
    for name in ("power_supply", "input_protection", "rail_disconnect"):
        folder = ROOT.parent / name
        report_path = folder / "generated/verification.json"
        report = json.loads(report_path.read_text())
        for relative, digest in report["source_sha256"].items():
            assert sha(folder / relative) == digest, f"Refresh {name} verification: {relative}"
        screen_path = folder / "generated/electrical-screens.json"
        records[name] = json.loads(screen_path.read_text())
        sources.extend((report_path, screen_path))
    supply, inlet, disconnect = (records[n] for n in ("power_supply", "input_protection", "rail_disconnect"))
    ledger = supply["load_budget"]
    digital = ledger["digital_budget"]
    assert ledger["e20_load_included"]
    counted_led = sum(
        digital[k]
        for k in ("led_sink_ceiling_a", "led_driver_logic_allocation_a", "led_driver_misc_allocation_a")
    )
    assert math.isclose(counted_led, led_allocation), "Upstream ledger does not match E20"
    required, provision = ledger["digital_budget_total_a"], ledger["provided_digital_budget_a"]
    assert math.isclose(required, 1.574) and math.isclose(provision, 1.8)
    input_load = inlet["load"]
    input_margin = input_load["efuse_allocated_limit_a"][0] - input_load["combined_load_plus_ramp_a"]
    path = next(r for r in disconnect["normal_drop"] if r["name"] == "5V_DIG")
    assert math.isclose(path["maximum_current_screen_a"], provision + 0.001)
    resistance = (
        2 * path["hot_resistance_each_fet_allocation_ohm"] / path["parallel_devices_per_side"]
        + path["copper_star_path_allocation_ohm"]
    )
    assert path["parallel_devices_per_side"] == 2 and math.isclose(
        resistance, path["effective_switch_and_star_path_allocation_ohm"]
    )
    buck = next(b for b in supply["bucks"] if b["name"] == "DIG")
    protected = [
        buck["minimum_dc_v"] - path["maximum_current_screen_a"] * resistance - 0.010,
        buck["maximum_dc_v"] + 0.010,
    ]
    assert all(math.isclose(a, b) for a, b in zip(protected, path["protected_dc_with_digital_ripple_v"]))
    target = path["target_at_integrated_board_star_v"]
    return dict(
        load_update_revision="E21",
        e20_board_and_emitters_allocation_a=led_allocation,
        revised_allocated_load_a=required,
        existing_digital_provision_a=provision,
        available_steady_load_headroom_a=provision - required,
        digital_load_exceeds_existing_provision=required > provision,
        e20_counted_exactly_once=True,
        conditional_revised_input_power_w=supply["power"]["maximum_allocated_input_power_w"],
        conditional_input_steady_a=input_load["maximum_allocated_steady_input_a"],
        conditional_input_plus_existing_ramp_a=input_load["combined_load_plus_ramp_a"],
        input_bus_ramp_a=input_load["inrush_current_allocation_a"],
        preconnected_digital_bulk_ramp_input_a=input_load[
            "digital_preconnected_bulk_ramp_input_allocation_a"
        ],
        existing_efuse_allocated_minimum_a=input_load["efuse_allocated_limit_a"][0],
        existing_efuse_allocated_maximum_a=input_load["efuse_allocated_limit_a"][1],
        input_current_margin_a=input_margin,
        input_current_allocation_pass=input_margin > 0,
        revised_protected_5v_current_a=path["maximum_current_screen_a"],
        existing_protected_path_resistance_allocation_ohm=resistance,
        conditional_protected_5v_range_v=protected,
        protected_star_target_v=target,
        protected_star_voltage_allocation_pass=protected[0] >= target[0] and protected[1] <= target[1],
        protected_star_margin_v=[protected[0] - target[0], target[1] - protected[1]],
        includes_e20_pcb_or_production_harness_drop=False,
        other_rail_charging_and_late_switch_close_bounded=False,
        physical_load_and_protection_validated=False,
        full_unit_power_budget_closed=False,
        required_work="Route/qualify the power hardware, symmetric parallel FET branches, increased gate charge/leakage, all-rail startup/late closure, connected capacitance and large-capacitor loop, thermal limits, actual low-current LED ICC, 3V3 loads and distribution/contact drops. Passing allocations are not physical proof.",
        historical_a06_e20=dict(
            digital_provision_a=1.2,
            missing_driver_and_sink_allocation_a=0.476,
            input_plus_ramp_a=2.693094551282051,
            input_minimum_limit_a=2.488681874253972,
            protected_5v_minimum_v=4.898190970106395,
            scope="Immutable led-and-housing-review-A06-E20.zip; earlier failed allocation screens",
        ),
        fresh_upstream_screen_sha256={str(p.relative_to(ROOT.parent)): sha(p) for p in sources},
    ), sources
