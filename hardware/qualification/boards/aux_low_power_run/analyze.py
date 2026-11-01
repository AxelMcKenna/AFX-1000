"""AX03 source-bound load reduction; receiving bounds stay distinguishable."""

import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def analyze(extra_per_input=100e-6, receiver_resistance=200000, receiver_error=.01, source_series=1000):
    old = json.loads((ROOT / "sources/AX02-analysis.json").read_text())
    parent = json.loads((ROOT / "sources/AX01-analysis.json").read_text())
    vlo = parent["POWER_RUN_value_comparisons"][0]["source_min_v"]
    vhi = 2.7  # Existing local maximum requirement, not a new source setting.
    common_ground_max = .0134786
    rdlo, rdhi = receiver_resistance*(1-receiver_error), receiver_resistance*(1+receiver_error)
    rslo, rshi = source_series*.97, source_series*1.03
    input_extra = 1.5e-6  # AUP0.5uA primary row +1uA board receiving allowance.
    # Shared source: VCC at the receiver and signal voltage experience the SAME
    # ground offset. Do not combine incompatible independent source corners.
    # Ratio bounds are proposed acceptance requirements, NOT interpolated TI
    # guaranteed limits: TI specifies VT at discrete supplies only.
    vtp_ratio, vtm_ratio = .78, .28
    corners = []
    for supply, ground, positive_drop in itertools.product([vlo, vhi], [-common_ground_max, common_ground_max], [0, common_ground_max]):
        local_vcc = supply-positive_drop-ground
        if not 2.52 <= local_vcc <= 2.70:
            continue
        high = (supply-.1-(rshi+250)*input_extra)/(1+(rshi+250)/rdlo)-ground
        corners.append(dict(source_v=supply, ground_offset_v=ground, positive_drop_v=positive_drop,
                            local_vcc_v=local_vcc, leaf_HIGH_v=high,
                            required_HIGH_times1p2_v=1.2*vtp_ratio*local_vcc,
                            HIGH_guarded_margin_v=high-1.2*vtp_ratio*local_vcc))
    assert corners
    # Source TPS3890 RESET_N drives an AUP Schmitt, not a standard CMOS pin.
    reset_high = (vlo/103000-.85e-6)/(1/103000+1/9700000)
    reset_high_target = 1.2*vtp_ratio*vlo
    open_leak = 1e-6+.5e-6+1e-6  # Complete relay-path requirement+input+board.
    off = open_leak*rdhi
    current_drive = 2.7/rdlo+input_extra
    short = 2.7/rslo
    # AX02's E28 scenario ledger includes22 active triple-buffer inputs and
    #8 no-load LVC packages. Replace those terms explicitly and add the actual
    #new single receiver, its nonrail provision and its U28 input load once.
    e28_delta_raw = -.011 + 23*extra_per_input - 8*10e-6 + 9*.9e-6 + 5e-6
    new_bias = .9e-6+extra_per_input+6.5e-6+.85e-6+2.7/(97000+9700000)
    states = []
    for row in old["pool_scenarios"]:
        s = dict(row)
        s["E28_guarded_a"] = row["E28_guarded_a"]+1.2*e28_delta_raw
        line_current = short if row["name"] in ["leaf_short_before_E28_logic_settles_TRANSIENT_NOT_CLOSED", "unconstrained_overlap_NOT_closed"] else current_drive
        s["new_leaf_guarded_receiving_a"] = 1.2*(new_bias+line_current)
        s["source_total_receiving_a"] = s["E28_guarded_a"]+row["P03_guarded_a"]+row["NF_guarded_allocation_a"]+s["new_leaf_guarded_receiving_a"]
        s["raw_receiving_before_joint1p2_a"] = s["source_total_receiving_a"]/1.2
        s["margin_to_existing90mA_a"] = .09-s["source_total_receiving_a"]
        s["inside_existing90mA_receiving_pool"] = s["source_total_receiving_a"] <= .09
        states.append(s)
    return dict(revision="AX03-low-power-high-impedance-RUN", existing_AUX_pool_a=.09,
        existing_LDO_rating_a=.1, source_regulator_or_voltage_changed=False,
        original_R113_ohm=3300, original_PG_sink_load_increased=False,
        selected_triples="SN74AUP3G17DCUR", triple_packages=8,
        selected_source_and_receiver="SN74AUP1G17DCKR", source_buffer_and_receiver_count=2,
        primary_output_20uA_row=dict(supply_range_v=[.8,3.6], VOH_drop_max_v=.1, VOL_max_v=.1),
        primary_input_leak_max_a=.5e-6, primary_Ioff_max_a=.6e-6,
        primary_DeltaICC_50uA_scope="VCC3.3V, VI=VCC-0.6V, otherinputs at rails; NOT a2.52..2.70V/all-input guarantee",
        nonrail_per_active_input_receiving_a=extra_per_input,
        nonrail_receiving_bound_manufacturer_guaranteed=False,
        threshold_ratio_receiving=dict(VTplus_max_ratio=vtp_ratio, VTminus_min_ratio=vtm_ratio,
                                      manufacturer_continuous_ratio_guarantee=False,
                                      actual_supply_temperature_characterization_required=True),
        HIGH_coupled_corners=corners, minimum_HIGH_guarded_margin_v=min(x["HIGH_guarded_margin_v"] for x in corners),
        source_RESET_HIGH_receiving_v=reset_high, source_RESET_HIGH_times1p2_target_v=reset_high_target,
        source_RESET_HIGH_guarded_margin_v=reset_high-reset_high_target,
        source_POR_pull_current_times1p2_a=1.2*(.8/97000+.6e-6), primary_POR_test_a=15e-6,
        source_RESET_LOW_max_v=.25, RESET_LOW_times1p2_v=.3,
        receiver_pulldown_nominal_ohm=receiver_resistance, complete_resistor_receiving_fraction=receiver_error,
        source_series_nominal_ohm=source_series, complete_source_series_fraction=.03,
        complete_contact_and_wire_loop_max_ohm=250, ground_offset_receiving_max_v=common_ground_max,
        source_normal_output_current_max_a=current_drive, primary_light_load_row_max_a=20e-6,
        short_current_conservative_max_a=short, short_current_times1p2_a=1.2*short,
        source_pin_abs_max_output_a=.02, source_absolute_rating_is_NOT_a_logic_drive_guarantee=True,
        short_series_power_times1p2_w=1.2*vhi*vhi/rslo,
        open_path_leak_receiving_total_a=open_leak, disconnected_HIGH_max_v=off,
        disconnected_times1p2_v=1.2*off, LOW_acceptance_floor_v=vtm_ratio*2.52,
        cable_and_input_C_max_receiving_f=1e-9,
        wire_open_RC_to_LOW_acceptance_s=rdhi*1e-9*math.log(vhi/(vtm_ratio*2.52)),
        standalone_loaded_cutoff_upper_s=None,
        source_switch_internal_reverse_comparator_and_BGA_removed=True,
        source_input_local_bypass_nominal_f=200e-9, source_controller_CT_nominal_f=10e-9,
        original_AX02_input_cap_nominal_f=10.1e-6,
        input_cap_reduction_fraction=1-200e-9/10.1e-6,
        source_source_collapse_partial_power_and_capacitance_qualified=False,
        pool_scenarios=states, all_receiving_scenarios_inside90mA=all(x["inside_existing90mA_receiving_pool"] for x in states),
        complete_hot_current_physical_bound_a=None, physical_qualified=False,
        startup_fault_energy_qualified=False, PCB_adopted=False, fabrication_released=False)


if __name__ == "__main__":
    result = analyze()
    target = ROOT / "generated/analysis.json"
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2)+"\n")
    print([(x["name"], x["source_total_receiving_a"]) for x in result["pool_scenarios"]])
