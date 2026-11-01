"""Direct-solder force footprint proposal and explicit resistance bookkeeping."""

import json
import shutil
from pathlib import Path

from .study import REPO, ROOT, sha


def complete_path_wire(lead_m, nominal_dcr_per_1000ft=7, temperature=100, provision=1.2):
    if lead_m <= 0 or not 20 <= temperature <= 105 or provision < 1:
        raise ValueError("Positive physical model inputs required")
    nominal20 = 2 * lead_m * nominal_dcr_per_1000ft / 304.8
    # A declared copper linear-TCR scenario, not a wire supplier upper bound.
    hot = nominal20 * (1 + 0.00393 * (temperature - 20)) * provision
    return dict(
        two_lead_total_length_m=2 * lead_m,
        nominal_wire20_ohm=nominal20,
        temperature_C=temperature,
        copper_linear_TCR_assumption_per_K=0.00393,
        DCR_provision=provision,
        wire_hot_scenario_ohm=hot,
        wire_hot_qualified_upper_bound=False,
    )


def build():
    out = ROOT / "generated"
    target = out / "force-pigtail-proposal.json"
    if target.exists():
        raise RuntimeError("New proposal output required")
    p = REPO / "hardware/cad/a12/harness/output-wire-6715.json"
    q = ROOT / "sources/repository/alpha6715-parent-proposal.json"
    shutil.copyfile(p, q)
    assert sha(p) == sha(q)
    parent = json.loads(q.read_text())
    vendor = Path(parent["external_pdf_path"])
    pdf = ROOT / "sources/primary/alpha6715-current.pdf"
    assert sha(vendor) == parent["manufacturer_pdf_sha256"]
    shutil.copyfile(vendor, pdf)
    fp = ROOT / "ForcePigtail.pretty/NF_Force_18AWG_P5_2p1Drill_Receiving.kicad_mod"
    fp.parent.mkdir()
    fp.write_text("""(footprint "NF_Force_18AWG_P5_2p1Drill_Receiving"
 (version 20240108) (generator "NC01_unreleased_receiving_proposal") (layer "F.Cu")
 (descr "Direct-solder two-wire force proposal; actual wire/solder/strain not qualified")
 (property "Reference" "J?" (at 2.5 -3) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))
 (property "Value" "DIRECT_FORCE_PROPOSAL" (at 2.5 3) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))
 (attr through_hole)
 (fp_rect (start -2 -2) (end 7 2) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
 (pad "1" thru_hole circle (at 0 0) (size 3.4 3.4) (drill 2.1) (layers "*.Cu" "*.Mask"))
 (pad "2" thru_hole circle (at 5 0) (size 3.4 3.4) (drill 2.1) (layers "*.Cu" "*.Mask"))
)\n""")
    scenarios = [complete_path_wire(length) for length in [0.05, 0.1, 0.15, 0.2]]
    for s in scenarios:
        s["four_solder_joint_acceptance_allocation_each_ohm"] = 0.001
        s["joint_total_allocation_ohm"] = 0.004
        s["joint_allocation_within_existing5mohm_contact_requirement"] = True
        s["complete_wire_plus_joints_scenario_ohm"] = s["wire_hot_scenario_ohm"] + 0.004
        s["complete_wire_plus_joint_path_not_proven5mohm"] = True
    a = json.loads((ROOT / "generated/analysis.json").read_text())
    by_length = []
    for source in a["force_source_corner_sensitivities"]:
        for s in scenarios:
            extra = s["complete_wire_plus_joints_scenario_ohm"] - 0.005
            by_length.append(
                dict(
                    source_recenter_comparison_ohm=source["resistor_comparison_ohm"],
                    source_change_implemented=source["source_recenter_implemented"],
                    two_lead_total_length_m=s["two_lead_total_length_m"],
                    added_guarded_drop_v=1.2 * source["allocated_force_current_a"] * extra,
                    guarded_low_margin_given_ALL_conditional_source_copper_current_assumptions_v=source[
                        "original_guarded_low_margin_v"
                    ]
                    - 1.2 * source["allocated_force_current_a"] * extra,
                    actual_hot_path_and_endpoint_qualified=False,
                )
            )
    d = dict(
        revision="NC01-direct-force-receiving-footprint-proposal",
        applicable=["J2", "J4"],
        existing_force_header_drill_mm=1.0,
        selected_wire_candidate="Alpha6715",
        wire_details=parent["wire"],
        existing1mm_drill_less_than_nominal1p2192_conductor=True,
        proposed_footprint=str(fp.relative_to(ROOT)),
        force_pad_pinmap_preserved=dict(pin1="P03_SRC", pin2="E28_SRC"),
        old2p54_pitch_and_pose_not_preserved=True,
        bare_tinned_bundle_max_diameter_requirement_mm=1.4,
        bore_minimum_receiving_requirement_mm=2.1,
        relative_centering_requirement_mm=0.3,
        geometry_reserve_mm=0.005,
        worst_idealized_radial_gauge_gap_mm=(2.1 - 1.4) / 2 - 0.3 - 0.005,
        land_diameter_mm=3.4,
        nominal_pitch_mm=5,
        nominal_annulus_mm=0.65,
        maximum_rear_trim_plus_fillet_requirement_mm=1.5,
        front_strip_wicking_and_fillet_requirements_not_selected=True,
        strain_relief=dict(
            independent_load_path_required=True,
            board_solder_joints_not_strain_anchors=True,
            proposal="Separate insulating clamp/support anchored to chassis or new dedicated PCB mechanical holes, gripping insulated straight wire before first bend",
            material=None,
            clamp_dimensions=None,
            grip_compression=None,
            selected_fasteners=None,
            pull_force_acceptance_N=None,
            creep_temperature_lifetime_qualified=False,
            incomplete_mechanical_design=True,
        ),
        scenarios=scenarios,
        N12_source_corner_sensitivities=by_length,
        force_contact5mohm_allocation_not_complete_wire_loss_budget=True,
        accepted_force_wire_maximum_temperature_C=None,
        new_receiver_PCB_and_scene_not_implemented=True,
        native_KiCad_footprint_parser_check_pending=True,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        source_sha256={
            str(p): sha(p) for p in [Path(__file__), q, pdf, fp, ROOT / "generated/analysis.json"]
        },
    )
    target.write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                force_pad_pitch=5,
                bore_requirement=2.1,
                radial_gap=0.045,
                joint_requirement_only=0.004,
                mechanical_design_complete=False,
            )
        )
    )


if __name__ == "__main__":
    build()
