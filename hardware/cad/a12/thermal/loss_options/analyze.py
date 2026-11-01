"""LO01 loss ceilings and conditional engineering options; no target/geometry adoption."""

import copy
import itertools
import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.cad.a12.thermal.whole_unit.plate import plate_scenario

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
WU = ROOT.parent / "whole_unit"


def read(path):
    return json.loads(path.read_text())


def buck_interval(top, bottom):
    vals = [
        v * (1 + top * (1 + a * 0.001) / (bottom * (1 + b * 0.001))) + leak * top * (1 + a * 0.001)
        for v, a, b, leak in itertools.product((0.4975, 0.5025), (-1, 1), (-1, 1), (-0.1e-6, 0.1e-6))
    ]
    return [min(vals), max(vals)]


def main():
    ledger = read(WU / "generated/ledger.json")
    thermal = read(WU / "generated/analysis.json")
    source = read(WU / "sources/hardware/electronics/power_distribution/p03/generated/analysis.json")
    feed = source["selected_input_chain"]
    design = read(WU / "sources/hardware/cad/a12/thermal/design.json")
    baseline = ledger["total_internal_heat_screen_w"]
    categories = {r["id"]: r["category"] for r in ledger["leaf_heat_rows"]}
    totals = {
        name: math.fsum(r["watts"] for r in ledger["leaf_heat_rows"] if r["category"] == name)
        for name in sorted(set(categories.values()))
    }
    references = []
    for mode, inputs in thermal["source_placements"].items():
        for variant in ["lossless_converters", "lossless_all_power_stages", "endpoint_only"]:
            rows = copy.deepcopy(inputs)
            for row in rows:
                c = categories[row["id"]]
                zero = (
                    (variant == "lossless_converters" and c == "converter_loss")
                    or (
                        variant == "lossless_all_power_stages"
                        and c in ["converter_loss", "linear_drop", "input_distribution"]
                    )
                    or (variant == "endpoint_only" and c != "delivered_endpoint")
                )
                if zero:
                    row["watts"] = 0
            result = plate_scenario(design, rows, 3, 0.8)
            references.append(
                dict(
                    placement=mode,
                    variant=variant,
                    result=result,
                    is_implemented=False,
                    is_actual_minimum_heat_bound=False,
                    load_allocations_reduced=False,
                    export_credit_adopted=False,
                )
            )
    entries = feed["resistance_entries_ohm"]
    remainder = feed["total_conditional_feed_allocation_ohm"] - sum(entries.values())
    feed_rows = [
        dict(
            id=name,
            resistance_ohm=r,
            heat_at4A_w=16 * r,
            classification="catalog/test-point/engineering entry; consult capturedH01/P03 source",
        )
        for name, r in entries.items()
    ]
    feed_rows.append(
        dict(
            id="unproved_fuse_P03_copper_remainder",
            resistance_ohm=remainder,
            heat_at4A_w=16 * remainder,
            classification="Unmeasured remainder of complete.36ohm requirement; not an extra physical component",
        )
    )
    assert math.isclose(sum(r["resistance_ohm"] for r in feed_rows), 0.36)
    assert math.isclose(sum(r["heat_at4A_w"] for r in feed_rows), 5.76)
    eta = []
    for efficiency in [0.85, 0.90, 0.95]:
        aux_input = 5 * 0.0901 / efficiency
        eta.append(
            dict(
                efficiency_assumed=efficiency,
                output_target_v=5,
                complete_U102_input_a=0.0901,
                new_complete_AUX_input_w=aux_input,
                old_complete_AUX_input_w=ledger["blocks"]["aux_complete_input_w"],
                conditional_saving_w=ledger["blocks"]["aux_complete_input_w"] - aux_input,
                efficiency_is_guaranteed=False,
            )
        )
    copper_joints = [
        dict(
            new_four_joint_resistance_assumed_ohm=r,
            hypothetical_complete_feed_ohm=0.36 - 0.080 + r,
            saving_at4A_w=16 * (0.080 - r),
            joint_value_is_acceptance_or_guarantee=False,
        )
        for r in [0, 0.004, 0.010, 0.020, 0.080]
    ]
    new_pre = buck_interval(104000, 10000)
    old_pre = source["sources"]["preregulator_dc_interval_v"]
    analog = dict(
        proposed_top_ohm=104000,
        bottom_ohm=10000,
        inherited_reference_interval_v=[0.4975, 0.5025],
        inherited_resistor_error=0.001,
        inherited_FB_bias_allocation_a=0.1e-6,
        bias_is_guaranteed=False,
        proposed_pre_interval_before_ripple_v=new_pre,
        old_pre_interval_before_ripple_v=old_pre,
        retained_ripple_peak_allocation_v=0.050,
        retained_dropout_allocation_v=0.450,
        source_analog_upper_v=source["sources"]["analog_local_source_interval_v"][1],
        conditional_dropout_margin_v=new_pre[0]
        - 0.05
        - source["sources"]["analog_local_source_interval_v"][1]
        - 0.45,
        conditional_source_power_saving_w=(old_pre[1] - new_pre[1]) * 0.259 / 0.85,
        PSRR_noise_loadstep_startup_qualified=False,
    )
    normalized_outputs = [
        ledger["blocks"]["digital_input_w"] * 0.85,
        ledger["blocks"]["analog_prereg_input_w"] * 0.85,
        ledger["blocks"]["bipolar_converter_input_w"] * 0.75,
    ]
    all95 = (
        sum(
            ledger["blocks"][k]
            for k in ["digital_input_w", "analog_prereg_input_w", "bipolar_converter_input_w"]
        )
        - sum(normalized_outputs) / 0.95
    )
    facts = read(ROOT / "sources/primary-facts.json")
    for fact in facts.values():
        if fact.get("local_pdf"):
            assert sha(ROOT / "sources/primary" / fact["local_pdf"]) == fact["local_pdf_sha256"]
    paths = [
        Path(__file__).resolve(),
        ROOT / "sources/primary-facts.json",
        WU / "handoff.json",
        WU / "generated/ledger.json",
        WU / "generated/analysis.json",
        WU / "plate.py",
        WU / "base_geometry.py",
        WU / "sources/hardware/cad/a12/thermal/design.json",
        WU / "sources/hardware/electronics/power_distribution/p03/generated/analysis.json",
    ]
    paths += [p for p in (ROOT / "sources/primary").iterdir() if p.is_file()]
    a = dict(
        revision="LO01-provisional-loss-reduction-feasibility",
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        retained_baseline_heat_target_w=baseline,
        actual_heat_upper_w=None,
        counterfactual_references=references,
        category_totals_w=totals,
        all_converters_95percent_hypothesis_saving_w=all95,
        eta95_is_a_selected_or_guaranteed_build=False,
        complete_feed_partition=feed_rows,
        actual_complete_feed_resistance_upper_ohm=None,
        source_consistent_feed_loss_diagnostic_w=[
            p["complete_feed_heat_w"] for p in thermal["steady_source_consistent_diagnostic"]["points"]
        ],
        internal_VH_replacement=dict(
            option="Retain selectedAlpha16AWGwire; replace fourJSTVHmated interfaces by four inspected solder terminations with independent retention/strainrelief",
            removed_contact_allocation_ohm=0.080,
            unknown_new_joint_resistance_ohm=None,
            illustrative_scenarios=copper_joints,
            maximum_ideal_zero_joint_saving_w=1.28,
            serviceability_and_rework_tradeoff=True,
            implemented=False,
        ),
        XLR_inlet_comparison=dict(
            receptacle="NeutrikNC4MD-L-1",
            plug="NeutrikNC4FXX",
            source_cable_gender="female",
            equipment_input_chassis_gender="male",
            catalog_per_contact_ohm=[0.005, 0.003],
            worst_single_mated_contact_interpretation_ohm=0.005,
            complete_two_pole_comparison_ohm=0.010,
            existing_barrel_contact_allocation_ohm=0.060,
            conditional_saving_at4A_w=16 * (0.060 - 0.010),
            hot_aged_mated_resistance_bound_established=False,
            contact_resistance_measurement_definition_confirmed=False,
            existing_adapter_captive_plug_and_voltage_boundary_unchanged=False,
            adapter_barrel_retained_in_extra_adapter_would_invalidate_saving=True,
            new_cutout_mate_cable_polarity_and_MCAD_unqualified=True,
            implemented=False,
        ),
        AUX_preregulator_option=dict(
            part="LMR36506R5RPER",
            input_node_required="VIN_IC upstream ofU101,afterQ101",
            output_target_v=5,
            nominal_U102_loss_at5v_w=(5 - source["auxiliary"]["source_interval_v"][1]) * 0.090 + 5 * 0.0001,
            preserves_main_eFuse_independent_bootstrap_in_concept=True,
            feed_from_existing_protected5v_is_rejected_circular_dependency=True,
            TPS62175_28v_candidate_not_same60v_input_class=True,
            fixed5v_full_corner_and_startup_headroom_bound_established=False,
            efficiency_comparisons=eta,
            new_90mA_load_bound_established=False,
            native_schematic_PCB_or_control_validation=False,
            implemented=False,
        ),
        analog_pre_5v7_option=analog,
        Q101_hot_resistance_review=dict(
            part="PSMN012-100YL,115",
            retained_engineering_hot_ohm=0.040,
            primary_max_ohm_at25C_VGS5_ID25=0.012,
            primary_max_ohm_at175C_VGS5_ID25=0.0331,
            gate_and_current_temperature_applicability_bound_established=False,
            room_temperature12mohm_not_promoted_to_hot4A_bound=True,
            existing_40mohm_allocation_reduced=False,
        ),
        actual_hardware_changed=False,
        no_load_reserves_removed=True,
        no_fan_or_housing_adopted=True,
        actual_loss_saving_guaranteed_w=None,
        physical_tests_performed=0,
        thermal_qualified=False,
        findings=[
            "Under retainedloadprovisions, evenendpoint-onlyzeroexport18.234W exceeds65C inbothh3/epsilon.8 placements; efficiency/feedchangesalonecannotclosecurrent60/65screen",
            "The35.4315W heat target is a planningcapacityscreen, not measuredactualpower; counterfactualnumbersarenotrealphysicalminimumheat",
            "Input.36ohm remainder1.8072W at4Ais uncertaintycapacity, not demonstrateddeviceheat; actualmeasurementscancloseanallocatedenvelope but donotconstitutehardwareefficiencyimprovement",
            "RealisticAUXprereg/tightenedanalogheadroom/contactoptions give fractional-to-oneWatt papergains, require source/sequence/EMI/PCB/physicalproof, andcannotbesummedwithout renewedcoupledsource/feedanalysis",
        ],
    )
    (OUT / "analysis.json").write_text(json.dumps(a, indent=2) + "\n")
    print(json.dumps(dict(feed=feed_rows, AUX=eta, analog=analog, eta95saving=all95), indent=2))


if __name__ == "__main__":
    main()
