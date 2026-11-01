"""NF03C static feed/endpoint comparisons from real native source values.

These are design requirements and conditional calculations, never new
manufacturer limits or physical acceptance. NF02's immutable sources are used.
"""

import copy
import itertools
import json
from pathlib import Path

from hardware.electronics.power_distribution.p03.bipolar import source_corners
from hardware.electronics.power_distribution.p03.models import constant_power_feed
from hardware.electronics.power_distribution.p03.models import value
from hardware.qualification.boards.startup_negative_protection.analyze import watchdog, cuk_peak
from hardware.qualification.boards.startup_negative_protection.analyze import native
from hardware.qualification.boards.startup_negative_protection.capture import sha
from hardware.qualification.boards.startup_negative_protection.verify import validate_handoff

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent.parent / "startup_negative_protection"
REPO = ROOT.parents[4]


def interval(value, fraction):
    assert value > 0 and 0 <= fraction < 1
    return value * (1 - fraction), value * (1 + fraction)


def feed(p):
    vlo, vhi = p["complete_delivered_module_voltage_requirement_v"]
    assert 0 < vlo <= vhi
    rlo, rhi = interval(sum(p["feed_series_resistors_ohm"]), p["feed_total_fraction_requirement"])
    zlo, zhi = p["native_vin_normal_requirement_v"]
    minimum, maximum = (vlo - zhi) / rhi, (vhi - zlo) / rlo
    load = (
        p["controller_table_iq_a"] + p["iso_secondary_dc_max_table_a"]
        + p["intvcc_requirement_v"][1] / (p["on_pulldown_ohm"] * 0.97)
        + zhi / (p["vin_bleed_ohm"] * 0.97)
        + p["other_float_current_requirement_a"]
        +p["floating_supervisor_count_per_rail"]*p["floating_supervisor_iq_requirement_a"]
        +p["native_vin_normal_requirement_v"][1]/(88700*.999)
        +p["intvcc_requirement_v"][1]/(40400*.999)
        +p["intvcc_requirement_v"][1]/(47000*.97)
    )
    zero = vhi / rlo
    out_p = maximum * vhi
    return dict(
        module_part=p["isolated_module_part"], module_delivered_voltage_requirement_v=[vlo, vhi],
        series_resistor_requirement_ohm=[rlo, rhi], normal_feed_interval_a=[minimum, maximum],
        normal_controller_and_isolator_requirement_a=load,
        normal_load_has20pct_headroom=minimum >= p["normal_guardband"] * load,
        normal_shunt_feed_below25ma=maximum <= p["native_vin_shunt_characterized_upper_current_a"],
        vin_zero_feed_current_upper_given_module_requirement_a=zero,
        initial_feed_has20pct_below50ma=1.2 * zero <= p["native_vin_feed_guidance_maximum_a"],
        normal_module_load_inside10_to90pct_characterized_region=(
            minimum >= 0.1 * p["module_output_current_table_a"]
            and maximum <= 0.9 * p["module_output_current_table_a"]
        ),
        initial_module_load_inside90pct=zero <= 0.9 * p["module_output_current_table_a"],
        module_output_normal_power_requirement_w=out_p,
        both_module_input_power_requirement_w=2 * out_p / p["module_efficiency_minimum_requirement"],
        complete_series_normal_power_requirement_w=(vhi-zlo)**2/rlo,
        complete_series_vin_zero_power_requirement_w=vhi**2/rlo,
        resistor_thermal_and_pulse_qualified=False,
        module_peak_no_load_startup_collapse_and_input_inrush_verified=False,
        minimum_efficiency_guaranteed=False,
        feed_qualified=False,
        rejected15v_213ohm_initial_current_a=15.8/(213*0.97),
        rejected15v_reason="Normal load and initial VIN=0 feed cannot both meet the primary50mA guidance with that simple resistor.",
    )


def recenter(p, parts):
    rows=[]
    for total in (180000, 180200, p["new_n12_r40_top_total_comparison_ohm"], 181000):
        trial=copy.deepcopy(parts)
        trial["R40"].find("value").text=f"{total} ohm"
        rail=source_corners(trial)["N12"]
        lo,hi=rail["source_magnitude_v"]
        # Use the final target HIGH for bleeds: no undercount after recenter.
        current=(0.151+12.12/(47000*0.97)+p["protected_extra_hot_leakage_and_crossrail_requirement_a"]
                 +p["new_protected_monitor_current_requirement_a"])
        resistance=(0.120*1.05+p["pass_hot_on_resistance_requirement_ohm"]
                    +p["e28_bank_pair_hot_resistance_requirement_ohm"]
                    +p["new_negative_force_contacts_total_requirement_ohm"]+p["e28_copper_scenarios_ohm"]["N12"])
        dc=current*resistance
        lower=lo-0.010-0.005-1.2*dc
        upper=hi+1.2*(0.010+0.005)
        rows.append(dict(
            proposed_r40_total_ohm=total, source_magnitude_interval_v=[lo,hi],
            steady_bank_force_current_requirement_a=current,
            separate_pre_limiter_vee_bleed_current_a=12.12/(p["negative_to_agnd_bleed_ohm"]*0.97),
            vee_bleed_is_not_bank_or_shunt_current=True,complete_new_stage_resistance_requirement_ohm=resistance,
            stage_dc_drop_requirement_v=dc, guarded_final_comparison_v=[lower,upper],
            guarded_low_margin_v=lower-11.88, guarded_high_margin_v=12.12-upper,
            interval_within_retained_target=lower>=11.88 and upper<=12.12,
            no_load_and_full_load_adverse_corners_both_included=True,
            dynamic_and_ground_harness_allocations_retained_v=[0.010,0.005],
            actual_resistor_mpn_and_total_lifetime_error_accepted=False,
            actual_force_resistance_and_dynamic_envelopes_accepted=False,
            proposed_source_change_implemented=False, endpoint_qualified=False,
        ))
    return rows


def monitor_trip(gain_top, gain_bottom, reference_top, reference_bottom, p):
    """Positive output of a negative-rail inverter versus a positive reference.

    Input bias and opamp error are summed before dividing by the actual gain;
    comparator bias uses the actual reference Thevenin resistance. Output error
    uses noise gain 1+Rf/Rin. Polarity is reported separately by the caller.
    """
    rf=p["input_gain_resistor_complete_error_fraction_requirement"]
    answers=[]
    for ri,fb,rt,rb,ref,sign in itertools.product(
        interval(gain_top,rf),interval(gain_bottom,rf),interval(reference_top,rf),
        interval(reference_bottom,rf),interval(1.25,p["existing_protect_reference_complete_error_requirement_fraction"]),(-1,1)
    ):
        gain=fb/ri
        threshold=ref*rb/(rt+rb)
        sensor_error=p["opamp_offset_plus_drift_receiving_requirement_v"]*(1+gain)+p["opamp_input_bias_complete_receiving_requirement_a"]*fb
        ref_bias=p["comparator_input_bias_full_temperature_table_a"]*(10000+rt*rb/(rt+rb))
        error=sensor_error+ref_bias+p["comparator_offset_full_temperature_table_v"]
        answers.append((threshold+sign*error)/gain)
    return [min(answers),max(answers)]


def complete_power(p, f):
    """Replace NF02 galvanic feed, retain full2.4A rather than add fan twice."""
    old=json.loads((PARENT/'generated/analysis.json').read_text())
    wu_path=REPO/'hardware/cad/a12/thermal/whole_unit/generated/ledger.json'
    wu=json.loads(wu_path.read_text())
    base=old['complete_inlet_steady_diagnostic']
    removed=sum(r['bias']['normal_feed_current_interval_a'][1]*r['raw_voltage_upper_v'] for r in old['rails'].values())
    # Newly explicit existing E28 source-inverter/sense leakage reserve. Its
    # inclusion in the legacy151/26mA was not established, so do not zero it.
    source_monitor_each=0.0006
    source_extra=sum(source_monitor_each*r['raw_voltage_upper_v'] for r in old['rails'].values())
    actual_raw=base['new_actual_ledger_all_four_raw_output_power_w']-removed+source_extra
    protected=base['retained_other_protected_input_power_w']+actual_raw/0.75+f['both_module_input_power_requirement_w']
    point=constant_power_feed(11.4,0.36,protected,0.09)
    current,voltage=point["current_a"],point["protected_voltage_v"]
    # Actual fully enabled DC row, plus all stated branch/pulldown provisions.
    led_branch=(5.1-2*1.1)/(383*0.97)
    nf_digital=2*p["iso_primary_dc_max_table_a"]+2*led_branch+p['digital_other_current_requirement_a']
    reserve=p['total_digital_reserved_a']-p['known_installed_digital_allocations_a']-p['dual_fan_partition_a']
    # All OC outputs LOW independently is conservative (not a claimed state).
    aux_oc=(6+4)*2.7/(10000*0.97)
    external_pulldowns=9*2.7/(47000*0.97)
    logic_iq_requirement=0.00015
    comparator_iq_requirement=6*0.000040
    analog_requirement=2*28e-6+6*1.253/(100000*0.999)
    aux_requirement=aux_oc+external_pulldowns+logic_iq_requirement+comparator_iq_requirement+analog_requirement
    enclosing=[]
    for net,row in wu['retained_raw_current_envelopes'].items():
        required=row['retained_allocation_a']
        if net.startswith('RAW_N'):
            rail='N19' if net=='RAW_N22' else 'N12';r=old['rails'][rail]
            required=(r['p03_internal_raw_current_excluding_new_controller_a']+r['live_protected_current_scenario_a']
                      +r['new_vee_bleed_source_current_a']+r['new_monitor_source_current_requirement_a']+source_monitor_each)
        enclosing.append(dict(net=net,old_retained_a=row['retained_allocation_a'],new_requirement_a=required,
                              enclosing_requirement_a=max(required,row['retained_allocation_a']),voltage_v=row['voltage_magnitude_v']))
    raw_delta=sum(r['voltage_v']*(r['enclosing_requirement_a']-r['old_retained_a']) for r in enclosing)/0.75
    capacity=wu['total_internal_heat_screen_w']+raw_delta+f['both_module_input_power_requirement_w']
    return dict(
        retained_digital_total_a=2.4,fan_and_nf_are_partitions_not_added_loads=True,
        nf_digital_static_requirement_a=nf_digital,nf_digital_with20pct_requirement_a=1.2*nf_digital,
        fan_partition_a=p['dual_fan_partition_a'],fan_protection_partition_a=p['fan_protection_partition_a'],
        remaining_digital_pool_after_fan_a=reserve,
        remaining_for_fan_health_after_nf20pct_and_fp01_a=reserve-1.2*nf_digital-p['fan_protection_partition_a'],
        aux_computed_static_requirement_a=aux_requirement,aux20pct_requirement_a=1.2*aux_requirement,
        selected_aux_receiving_provision_a=p['new_aux_current_receiving_requirement_a'],
        aux_provision_has20pct=1.2*aux_requirement<=p['new_aux_current_receiving_requirement_a'],
        aux_is_suballocation_of_existing90ma=True,aux_source_pool_and_return_qualification=False,
        new_explicit_source_inverse_current_each_negative_a=source_monitor_each,
        nf02_removed_galvanic_negative_raw_output_power_w=removed,
        actual_recomposed_raw_output_requirement_w=actual_raw,
        protected_constant_power_requirement_w=protected,
        normal_feed_point=dict(plug_v=11.4,feed_ohm=0.36,aux_direct_a=0.09,current_a=current,board_v=voltage,
                               plug_power_w=11.4*current,feed_loss_w=current**2*0.36,
                               board_received_power_w=protected+0.09*voltage),
        enclosing_raw_rows=enclosing,retained_wu_capacity_heat_requirement_w=wu['total_internal_heat_screen_w'],
        new_capacity_raw_increment_w=raw_delta,new_isolated_module_input_requirement_w=f['both_module_input_power_requirement_w'],
        new_enclosing_whole_inside_heat_requirement_w=capacity,
        capacity_corner_is_same_as_normal_feed_point=False,
        whole_inside_assumption='All supplied power becomes internal heat; no fan optical/export heat credit. WU feed uses its separate4A/.36ohm provision, not normal-feed-pointI²R added again.',
        complete_temperature_startup_current_and_inlet_upper_bound_accepted=False,
        fan_health_actual_current_selected_a=None,
        source_sha256={'nf02_analysis':sha(PARENT/'generated/analysis.json'),'wu_ledger':sha(wu_path)},
    )


def startup(p):
    """Recalculate the NEW real cap networks and larger loaded gate enclosure.

    Native topology is read, not the predecessor's nominal CF/CG assumptions.
    Prototype current/slew/complete-C requirements remain unaccepted.
    """
    parts,pins,_=native(ROOT/'generated/netlist.xml')
    old=json.loads((PARENT/'generated/analysis.json').read_text())
    rows={}
    for rail in ('N19','N12'):
        r=old['rails'][rail]
        def caps(a,b):return [(ref,value(parts,ref)) for ref in parts if ref.startswith('C') and set(pins.get(ref,{}).values())=={a,b}]
        cr=caps(rail+'_CR_TOP',rail+'_E28_SRC')
        cf=caps(rail+'_RAMP',rail+'_P03_SRC')
        cg=caps(rail+'_CG_SERIES',rail+'_P03_SRC')
        css=caps(rail+'_SS',rail+'_P03_SRC')
        crlo,crhi=interval(sum(v for _,v in cr),.1)
        cflo,cfhi=interval(sum(v for _,v in cf),.1)
        currentlo,currenthi=r['ramp_current_extended_diagnostic_a']
        lo_slew,hi_slew=currentlo/crhi,currenthi/crlo
        live=r['live_protected_current_scenario_a']+p['new_protected_monitor_current_requirement_a']
        peak=live+r['full_network_capacitance_requirement_f']*hi_slew+currenthi
        output_time=r['source_voltage_enclosure_v'][1]/lo_slew
        filter_extra=(crhi+cfhi)*1.4/currentlo
        ss_extra=sum(v for _,v in css)*1.1*2.69/7e-6
        total=output_time+filter_extra+ss_extra+.1+.1+.02
        cwd=next(value(parts,ref) for ref in parts if ref.startswith('C') and rail+'_CWD' in pins.get(ref,{}).values())
        wd=watchdog(cwd,.1)
        cg_above1v=sum(v for _,v in cg)*1.1*(13-1)
        # Include RG when discharging CG; the whole1uC requirement also covers
        # MOS, PhotoMOS/wiring and BOTH bank MOS charges on their common node.
        net_sink=(1-.02)/(220*1.03+10*1.03+2)-.001
        discharge=1e-6/net_sink
        cutoff=.001+.0005+.005+discharge
        internal=r['p03_internal_raw_current_excluding_new_controller_a']
        normal_raw=internal+peak+r['new_vee_bleed_source_current_a']+.0006
        fault_max=r['native_current_limit_table_interval_a'][1]
        rows[rail]=dict(
            actual_cr_components=cr,actual_cf_components=cf,actual_cg_components=cg,
            cr_effective_requirement_f=[crlo,crhi],cf_effective_requirement_f=[cflo,cfhi],
            cf_min_over_cr_max=cflo/crhi,
            normal_peak_current_requirement_a=peak,
            native_min_currentlimit_a=r['native_current_limit_table_interval_a'][0],
            native_limit20pct_over_normal=r['native_current_limit_table_interval_a'][0]>=1.2*peak,
            ramp_full_trajectory_manufacturer_guaranteed=False,
            output_ramp_only_s=output_time,filter_extra_s=filter_extra,explicit_css_charge_extra_s=ss_extra,
            complete_stage_diagnostic_s=total,watchdog_interval_given_unaccepted_cap_s=wd,
            watchdog_min_has20pct_over_complete=wd[0]>=1.2*total,
            external_cg_charge_above1v_requirement_c=cg_above1v,
            old500nc_whole_node_allowance_insufficient_even_before_mos=cg_above1v>500e-9,
            new_whole_node_charge_receiving_requirement_c=1e-6,
            opposing_pv_miller_current_receiving_requirement_a=.001,
            loaded_clamp_net_sink_requirement_a=net_sink,
            conditional_complete_sensor_and_gate_off_s=cutoff,
            new_loaded_cutoff_receiving_enclosure_s=.010,
            cutoff20pct_headroom=1.2*cutoff<=.010,
            fault_watchdog_rectangle_with10ms_cutoff_scenario_j=r['source_voltage_enclosure_v'][1]*fault_max*(wd[1]+.010),
            actual_fault_peak_current_a=None,actual_fault_energy_upper_j=None,
            source_capacitor_inductor_bodydiode_and_wiring_discharge_bound_verified=False,
            normal_raw_current_requirement_a=normal_raw,
            normal_cold_switch_peak_scenario_a=cuk_peak(r['raw_voltage_upper_v'],normal_raw),
            hot_switch_frequency_efficiency_current_guaranteed=False,
            actual_gate_voltage_during_source_collapse_and_hot_soa_verified=False,
            watchdog_and_clamp_physical_qualified=False,
        )
    return rows


def analyze(p=None):
    assert not (ROOT / "handoff.json").exists(), "Immutable NF03C; create a successor"
    p=p or json.loads((ROOT/"parameters.json").read_text())
    validate_handoff(PARENT / "handoff.json")
    parts,_,_=native(PARENT/"sources/p03-fresh-netlist.xml")
    monitors={}
    for rail,ri,fb,uvtop,ovtop in (("N19",160000,10000,8695.7,2040.2),("N12",102000,10000,10869,2000)):
        monitors[rail]=dict(
            output_uv_magnitude_interval_v=monitor_trip(ri,fb,uvtop,100000,p),
            output_ov_magnitude_interval_v=monitor_trip(ri,fb,ovtop,100000,p),
            reference_error_is_unaccepted_complete_requirement=True,
            precision_endpoint_monitor=False,
            maximum_fault_delay_guaranteed_s=None,
            prototype_complete_sensor_delay_requirement_s=0.001,
        )
    f=feed(p)
    result=dict(
        revision="NF03C-static-design-region-not-qualification", feed=f, power=complete_power(p,f),startup=startup(p),
        n12_source_recenter_comparisons=recenter(p,parts), output_windows=monitors,
        source_sha256={str(x.relative_to(ROOT)):sha(x) for x in [ROOT/"parameters.json",ROOT/"analyze.py",ROOT/"integration.json"]},
        p03_frozen_netlist_sha256=sha(PARENT/"sources/p03-fresh-netlist.xml"),
        native_schematic_authored=True, e28_integration_implemented=False, pcb_implemented=False,
        physical_qualified=False,startup_qualified=False,fabrication_released=False,
    )
    (ROOT/"generated/analysis.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__ == "__main__":
    a=analyze()
    print(json.dumps({"feed":a["feed"],"output_windows":a["output_windows"]},indent=2))
