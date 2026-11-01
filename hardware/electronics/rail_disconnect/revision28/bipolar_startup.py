"""Source-bound retained-stage defect and explicitly unimplemented repair study.

The pass elements/bulk remain unchanged. These calculations identify requirements
for a subsequent native design; they are not component selection or SOA proof.
"""

import hashlib
import json
from pathlib import Path

from .manufacturer import ROOT
from .positive import components

PRIMARY = {
    "Si8751": (
        "https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf",
        "/private/tmp/e28-si8751.pdf",
        "206331A, 2022-07-27, 2.3/2.6/Table4.1",
    ),
    "CSD18540Q5B": (
        "https://www.ti.com/lit/ds/symlink/csd18540q5b.pdf",
        "/private/tmp/e28-csd18540q5b.pdf",
        "SLPS488B, April2017, 5.1/5.3",
    ),
    "LM5069": (
        "https://www.ti.com/lit/ds/symlink/lm5069.pdf",
        "/private/tmp/e28-lm5069.pdf",
        "SNVS452G, January2020, 7.3/7.5/8.4/9.2",
    ),
    "LM5067": (
        "https://www.ti.com/lit/ds/symlink/lm5067.pdf",
        "/private/tmp/e28-lm5067.pdf",
        "SNVS532D, August2020, 7.3/7.5/8.3/9.2",
    ),
}


def audit(parts=None):
    parts = components() if parts is None else parts
    by = {p["ref"]: p for p in parts}

    def pins(ref):
        return {str(p["number"]): p["net"] for p in by[ref]["pins"]}

    rows = []
    for i, rail, cap, cnom, voltage in (
        (1, "P19", "C4", 0.0015, 19),
        (2, "N19", "C8", 0.0015, 19),
        (3, "P12", "C12", 0.00022, 12),
        (4, "N12", "C16", 0.00022, 12),
    ):
        u = "U" + str(i)
        q1 = "Q" + str(2 * i - 1)
        q2 = "Q" + str(2 * i)
        assert by[u]["part"] == "SI8751AB-ISR"
        assert by[q1]["part"] == by[q2]["part"] == "CSD18540Q5B"
        assert pins(q1)["1"] == pins(q2)["1"] == pins(u)["5"] == rail + "_COMMON"
        assert pins(q1)["2"] == pins(q2)["2"] == rail + "_GATE"
        assert pins(q1)["3"] == rail + "_SRC" and pins(q2)["3"] == rail
        assert set(pins(cap).values()) == {"AGND", rail}
        assert "20%" in by[cap]["part"]
        maximum_cap = cnom * 1.2
        rows.append(
            dict(
                rail=rail,
                driver=u,
                fets=[q1, q2],
                protected_bulk=cap,
                actual_bulk_value=by[cap]["part"],
                local_bulk_max_f=maximum_cap,
                local_bulk_only_energy_j=0.5 * maximum_cap * voltage**2,
                driver_permit="E28_MASTER_ENABLE",
                current_or_slew_limit_present=False,
                # A charge time cannot be calculated without a guaranteed
                # charging-current/load waveform, even if gate timing exists.
                guaranteed_bulk_charge_time_s=None,
                proposed_controller="LM5067-1" if rail.startswith("N") else "LM5069-1",
                repair_implemented=False,
            )
        )
    return dict(
        revision="E28",
        rows=rows,
        defect="All four retained hard-disconnect banks enable together with firstDIGmaster; no bounded bipolar inrush element exists.",
        mcap_function="OFF-state drain-dVdt-induced false-turn-on suppression; not regulated load-capacitor soft start.",
        si8751_table_conditions=dict(
            vdd_range_v=[2.25, 5.5],
            tt_ohm=10000,
            gate_on_no_load_v=[9, 13],
            on_resistance_max_ohm=370000,
            on_resistance_min_not_specified=True,
            input_high_current_max_a=0.0095,
            input_vih_fraction_vdd=0.5,
            input_vil_fraction_vdd=0.25,
            maximum_turnoff_s=35e-6,
            turnoff_test_load_f=100e-12,
            actual_two_fet_gate_charge_tested=False,
        ),
        retained_fet_limits=dict(
            vds_v=60,
            vgs_abs_v=20,
            rds_max_25c_4v5_ohm=0.0033,
            rds_max_25c_10v_ohm=0.0022,
            gate_leakage_max_25c_at20v_a=100e-9,
            hot_gate_leakage_guaranteed=False,
            hot_rds_guaranteed=False,
            normalized_hot_rds_is_typical=True,
            existing_device_linear_soa_qualified=False,
        ),
        repair_proposal=dict(
            architecture="Unimplemented candidate: retained bidirectional hard-off pair, then independently controlled normal-ramp/fault-limited stage, then ALL protected bulk. An upstream ramp stage is an alternative only with a proven hard-off-bank ON interlock before ramp; otherwise late bank closure bypasses the soft start.",
            selection="LM5069-1 positive / LM5067-1 negative are research candidates only; separate linear-rated MOSFET, shunt and protection/level-shift circuitry still need selection.",
            sequence=[
                "all5VstagesfullyON",
                "P19controlledcharge",
                "N19controlledcharge",
                "P12controlledcharge",
                "N12controlledcharge",
            ],
            advancement="Each stage must have independently verified protected-voltage completion plus retained raw-source health; PGD alone has coarse VDS threshold and is not precision/unmute approval.",
            fault="Any sourceUV/OV/AUX/run/fault must deassert all enables; latchoff requires deliberate reset; reverse/partial-power behavior is retained through B2B but all new sense/driver pin paths need analysis.",
            low_current_shunt_only_proposal_rejected=True,
            rejection="Both controller datasheets require RS<=100mohm for proper operation; proposed1.2ohm/0.28ohm low-current shunts violate this requirement.",
            maximum_supported_shunt_ohm=0.1,
            minimum_current_limit_at_max_supported_shunt_a={"positive": 0.485, "negative": 0.440},
            bounded_slew_or_different_controller_required=True,
            lm5069_shunt_threshold_at_datasheet_test_v=[0.0485, 0.0615],
            lm5067_shunt_threshold_at_datasheet_test_v=[0.044, 0.056],
            lm5069_fault_timer_threshold_v=[3.76, 4.16],
            lm5069_fault_timer_charge_a=[51e-6, 120e-6],
            lm5067_fault_timer_threshold_v=[3.76, 4.16],
            lm5067_fault_timer_charge_a=[44e-6, 140e-6],
            threshold_test_conditions="LM5069 electrical table VIN48V; LM5067 ICC2mA/OUT48VaboveVEE unless stated. Do not silently extend conditional limits to12/19V without manufacturer-supported coverage.",
            controller_operating_temperature_c=[-40, 125],
            additional_drop_budget_accepted=False,
            startup_source_current_headroom_accepted=False,
            negative_enable_and_pg_level_shift_selected=False,
            current_power_timer_corner_network_selected=False,
            linear_pass_fet_and_pulse_soa_selected=False,
            native_area_and_height_fit_checked=False,
            actual_load_and_full_capacitance_inventory_accepted=False,
        ),
        build_ready=False,
        physical_qualified=False,
    )


def main():
    result = audit()
    result["sources"] = {
        name: dict(url=url, revision=rev, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
        for name, (url, path, rev) in PRIMARY.items()
    }
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (ROOT / "generated/bipolar-startup-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Four actual retained banks audited; bipolar inrush is uncontrolled; repair remains unimplemented.")


if __name__ == "__main__":
    main()
