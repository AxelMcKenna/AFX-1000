"""Native buck settings and analytical screens; no inferred loop-stability pass."""

import math

from ...common.netlists import number
from .models import value


def screen(parts, pins):
    rows = {}
    for name, ref, n, out, load, excursion, bulk in (
        ("DIG", "U20", 200, "5V_DIG_SRC", 2.4, 0.020, 0.0071),
        ("ANA_PRE", "U23", 220, "P03_PRE6V", 0.270, 0.050, 0.0),
    ):
        mode = value(parts, f"R{n + 3}")
        ramp = {3320: 1, 18200: 4}.get(mode)
        if ramp is None:
            raise ValueError(f"{ref} MODE value needs a primary-table review")
        assert value(parts, f"R{n + 2}") == 24300
        caps = [f"C{n + k}" for k in (6, 7, 8, 9)]
        for c in caps:
            assert set(pins[c].values()) == {out, "AGND"}
        local_cmin = len(caps) * 20e-6  # Unverified hot/DC-bias/aging allocation.
        local_cmax = sum(value(parts, c) for c in caps) * 1.2 * 1.22
        inductor_value = parts["L20" if name == "DIG" else "L23"].findtext("value")
        inductance = number(inductor_value.split()[0].removesuffix("H"))
        lmin, lmax = inductance * 0.8, inductance * 1.2
        ratio = [
            2 * math.pi * 450e3 * math.sqrt(lmin * local_cmin),
            2 * math.pi * 550e3 * math.sqrt(lmax * local_cmax),
        ]
        # TI Eq10 is explicitly a bandwidth estimate. Bulk at the far side of
        # finite switches/harness is not an ideal parallel capacitor at AC.
        estimate_c = load / (excursion * 2 * math.pi * (450e3 / 10))
        rows[name] = dict(
            regulator=ref,
            primary_source="https://www.ti.com/lit/ds/symlink/tps543620.pdf",
            primary_revision="SLUSDR5C Rev C",
            frequency_interval_hz=[450e3, 550e3],
            mode_resistor_native_ohm=mode,
            programmed_internal_ramp_pf=ramp,
            programmed_high_current_limit=True,
            nominal_soft_start_s=0.004,
            soft_start_tolerance_manufacturer_guaranteed=False,
            nominal_inductance_h=inductance,
            initial_inductance_interval_h=[lmin, lmax],
            hot_dc_current_inductance_bounds_verified=False,
            local_output_capacitors=caps,
            local_minimum_capacitance_requirement_f=local_cmin,
            local_initial_plus_positive_temperature_partial_maximum_f=local_cmax,
            local_hot_aged_biased_capacitance_verified=False,
            local_fsw_over_flc_scenario_interval=ratio,
            connected_disconnect_capacitance_maximum_scenario_f=bulk,
            downstream_bulk_treated_as_ideal_parallel_ac_capacitance=False,
            local_full_load_step_scenario_a=load,
            local_voltage_excursion_scenario_v=excursion,
            ti_eq10_estimated_minimum_capacitance_f=estimate_c,
            local_allocated_minimum_meets_eq10_estimate=local_cmin >= estimate_c,
            eq10_uses_unverified_fsw_div10_bandwidth=True,
            input_pair_native_nominal_f={f"C{n + k}": value(parts, f"C{n + k}") for k in (2, 3)},
            separate_hf_bypass_native_nominal_f={
                f"C{n + k}": value(parts, f"C{n + k}") for k in (10, 11) if f"C{n + k}" in parts
            },
            separate_hf_bypass_effective_minimum_requirement_f=10e-9,
            each_input_pair_effective_capacitance_requirement_f=1e-6,
            bp5_effective_capacitance_requirement_f=2.2e-6,
            input_and_bp5_hot_aged_effective_capacitance_verified=False,
            complete_coupled_pdn_and_esr_zero_model_accepted=False,
            phase_gain_margin_and_switching_jitter_qualified=False,
            physical_qualified=False,
        )
    return rows
