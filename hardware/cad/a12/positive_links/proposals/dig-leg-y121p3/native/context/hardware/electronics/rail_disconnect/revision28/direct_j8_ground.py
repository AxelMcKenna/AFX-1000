"""Read-only direct-J8 force-return interface study, with no guessed lug CAD.

Existing source PCB, bar and fastener geometry are bound. Lug geometry/tooling
and the new complete wire path remain prerequisites: no topology is adopted.
Native annular-pad anchor coordinates are never substituted for the stud centre.
"""

import argparse
import hashlib
import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .terminals import check_terminal

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def main():
    source = ROOT / "generated/p9-u14-input-escape-work"
    pcb = source / "rail_disconnect.kicad_pcb"
    pads_path = source / "generated/native-pads.json"
    parts_path = source / "components.json"
    receipt_path = source / "generated/current-native.json"
    design_path = REPO / "hardware/cad/a12/returns/design.json"
    facts_path = design_path.with_name("source-facts.json")
    inputs = [pcb, pads_path, parts_path, receipt_path, design_path, facts_path, Path(__file__)]
    blobs = {p: p.read_bytes() for p in inputs}
    hashes = {str(p.relative_to(REPO)): hashlib.sha256(blob).hexdigest() for p, blob in blobs.items()}
    assert (
        hashes[str(pcb.relative_to(REPO))]
        == "28c86cea474e46e9b857c11c059f304b8e61f46444d87b8aabcfc50f2b81c945"
    )
    receipt = json.loads(blobs[receipt_path])
    assert receipt["candidate_pcb_sha256"] == hashes[str(pcb.relative_to(REPO))]
    tree = read_sexpr(blobs[pcb].decode())
    design = json.loads(blobs[design_path])
    parts = {p["ref"]: p for p in json.loads(blobs[parts_path])}
    geometry = json.loads(blobs[pads_path])
    filled = source / "generated/filled-u14-input-escape1.kicad_pcb"
    assert geometry["source_pcb_sha256"] == hashlib.sha256(filled.read_bytes()).hexdigest()
    hashes[str(filled.relative_to(REPO))] = geometry["source_pcb_sha256"]
    datum = design["native_boards"]["E28"]["datum"]
    assert datum == [8, 108.5, 5]

    def fp(ref):
        return next(
            f
            for f in children(tree, "footprint")
            if next(p[2] for p in children(f, "property") if p[1] == "Reference") == ref
        )

    stud = fp("J8")
    terminal = check_terminal(stud)
    at = list(map(float, first(stud, "at")[1:]))
    assert len(at) == 2 or at[2] == 0
    center = [at[0] - 100 + datum[0], at[1] - 100 + datum[1]]
    assert center == [132, 129.5] == design["paths"]["DIG"]["xy"][0]
    anchor = list(map(float, first(children(stud, "pad")[0], "at")[1:3]))
    primitive = first(first(children(stud, "pad")[0], "primitives"), "gr_circle")
    local_circle = list(map(float, first(primitive, "center")[1:3]))
    assert [anchor[i] + local_circle[i] for i in (0, 1)] == [0, 0]

    def port(ref, pin):
        row = next(p for p in geometry["pad_polygons"] if p["ref"] == ref and p["pin"] == str(pin))
        return dict(
            ref=ref,
            pin=str(pin),
            net=row["net"],
            native_mm=row["position_mm"],
            world_xy_mm=[row["position_mm"][i] - 100 + datum[i] for i in (0, 1)],
            part=parts[ref]["part"],
            geometry_source_sha256=hashes[str(pads_path.relative_to(REPO))],
        )

    endpoints = {
        name: port(ref, pin)
        for name, ref, pin in (
            ("positive_output_unchanged", "J4", "1"),
            ("ground_pad_test_kelvin_candidate", "J4", "2"),
            ("digital_bulk_ground_still_on_pcb", "C24", "2"),
            ("digital_bulk_positive", "C24", "1"),
            ("analog_bulk_ground", "C20", "2"),
        )
    }
    assert endpoints["digital_bulk_ground_still_on_pcb"]["world_xy_mm"] == [158.25, 145.5]
    assert endpoints["positive_output_unchanged"]["world_xy_mm"] == [161, 120.5]
    assert endpoints["ground_pad_test_kelvin_candidate"]["world_xy_mm"] == [161, 129.5]
    thickness = design["native_boards"]["E28"]["thickness"]
    stud_plane = datum[2] + thickness + design["e28_stud_body_height_nominal_mm"]
    bar = design["bar"]
    hardware = design["terminal_hardware"]
    native_thickness = float(first(first(tree, "general"), "thickness")[1])
    prior_return = json.loads((source / "generated/return-diagnostic.json").read_text())
    drawing = Path("/private/tmp/afx-e28-lug-review/phoenix3240070-allied.pdf")
    drawing_sha = hashlib.sha256(drawing.read_bytes()).hexdigest()
    assert drawing_sha == "298dfeae7e889b60ebda6a0f73a22e4d1c8088fc0e80fec8865d1b0492276f9e"
    report = dict(
        scope="PRIVATE source-bound interface/resistance-endpoint proposal; no adopted topology or new lug CAD",
        source_sha256=hashes,
        unchanged_native_counts=receipt["native_counts"],
        native_J8_part=parts["J8"]["part"],
        native_J8_footprint_sha256=hashlib.sha256(sexpr(stud).encode()).hexdigest(),
        actual_J8_stud_center_world_xy_mm=center,
        actual_J8_annulus_custom_anchor_relative_mm=anchor,
        primitive_center_relative_to_anchor_mm=local_circle,
        copper_anchor_is_not_the_physical_stud_center=True,
        nominal_terminal_contract=terminal,
        current_interface_endpoints=endpoints,
        schematic_component_x_y_not_used_as_mechanical_coordinates=True,
        existing_MCAD_stack=dict(
            declared_board_datum_mm=datum,
            mcad_body_thickness_mm=thickness,
            native_general_thickness_mm=native_thickness,
            native_general_minus_mcad_body_mm=round(native_thickness - thickness, 6),
            thickness_mask_reference_and_solder_seating_convention_approved=False,
            nominal_stud_top_and_bar_lower_face_z_mm=stud_plane,
            nominal_bar_thickness_mm=bar["thickness"],
            finished_bar_max_thickness_requirement_mm=bar["thickness"]
            + bar["thickness_tolerance"]
            + 2 * bar["plating_max_per_face_mm"],
            nominal_bar_top_lug_lower_contact_face_z_mm=stud_plane + bar["thickness"],
            current_screw=hardware["screw"],
            nominal_screw_length_mm=hardware["length"],
            screw_length_minimum_and_usable_thread_depth_approved=False,
            current_washer=hardware["washer"],
            washer_thickness_range_mm=hardware["washer_thickness_range"],
            washer_outer_diameter_max_requirement_mm=hardware["washer_od_max"],
            head_max_diameter_mm=hardware["head_max_diameter"],
            head_max_height_mm=hardware["head_max_height"],
            nominal_engagement_formula="8 - 3.5 - lug_t - 0.55 mm; no minimum guarantee without drawing/lot bounds",
            nominal_head_top_formula="11.6 + 3.5 + lug_t + 0.55 + 2.52 mm",
            usable_thread_minimum_approved_mm=hardware["stud_usable_thread_minimum_approved_mm"],
        ),
        screened_lug_candidate_primary_page_only=dict(
            part="TE165291",
            source_url="https://www.te.com/en/product-165291.html",
            drawing="ENG_CD_165291_D1.pdf",
            drawing_visual_reviewed=False,
            wire_range_awg=[20, 17],
            wire_area_range_mm2=[0.5, 1],
            stud="M3",
            page_stud_hole_nominal_mm=3.2,
            page_tongue_nominal_mm=0.79,
            page_length_nominal_mm=14.35,
            page_barrel_ID_nominal_mm=1.6,
            plating="tin",
            insulation_support=False,
            page_temperature_c=[0, 170],
            all_page_dimensions_are_nominal_not_MCAD_or_tolerance_authority=True,
            drawing_and_CAD_fetch_status="Official public endpoints403/cache miss; browser window unavailable",
            geometry_tooling_contact_lifetime_and_supply_accepted=False,
        ),
        preferred_lug_drawing_review=dict(
            part="Phoenix Contact3240070 C-RC1/M3 DIN",
            official_current_url="https://www.phoenixcontact.com/gb/products/3240070/pdf",
            external_unmodified_manufacturer_pdf=str(drawing),
            external_pdf_sha256=drawing_sha,
            public_mirror_url="https://assets.alliedelec.com/image/upload/v1560335573/Datasheets/7eaee44fb49a5f530b06013ed722fd87.pdf",
            original_footer_date="06/11/2019",
            all_three_pages_visually_inspected=True,
            copyright_notice="Phoenix Contact2019,all rights reserved; original PDF remains external",
            current_official_text_generation_date="Oct2,2026",
            drawing_page=2,
            dimension_mapping_mm=dict(
                a_head_width=6,
                b_total_length=14,
                c_barrel_length=5,
                d_barrel_bore=1.6,
                e_ring_center_to_barrel_start=6,
                f_ring_bore=3.2,
                g_2019_flat_stock=0.8,
            ),
            nominal_model_axis_x_extents_mm=dict(head_left=-3, ring_center=0, barrel_start=6, barrel_end=11),
            dimensional_consistency_3_plus_6_plus_5_equals_14=True,
            current_2026_data_calls_g_minimum_not_maximum=True,
            wire_area_range_mm2=[0.5, 1],
            material="tin-plated electrolytic copper",
            crimp_zone="brazed",
            tool_family_suggested="CRIMPFOX-RC",
            nominal_0p8mm_example=dict(
                thread_engagement_mm=3.15,
                screw_head_top_world_z_mm=18.97,
                manufacturer_guaranteed_bounds=False,
            ),
            overall_barrel_height_OD_transition_radii_and_post_crimp_envelope_not_dimensioned=True,
            tinned_fine_stranded_selected_wire_and_exact_die_recipe_approved=False,
            actual_lug_MCAD_created=False,
            receiving_dimension_and_contact_limits_accepted=False,
        ),
        source_force_return_graph_proposal=[
            dict(
                edge="receiver_ground_to_wire",
                endpoint="Actual receiving terminal/fanout remains unselected",
                qualified=False,
            ),
            dict(
                edge="wire_conductor",
                endpoint="Actual formed route/length/hotR requires a new check",
                qualified=False,
            ),
            dict(
                edge="source_crimp_lug_and_lug_to_bar_joint",
                endpoint="New ring joins existing J8 DIG bar top face, not an ideal PCB electrode",
                maximum_R_requirement_ohm=None,
                allocation_owner_pending=True,
                qualified=False,
            ),
            dict(
                edge="existing_DIG_bar",
                endpoint="J8 landing to P03J21 landing",
                hot_bar_requirement_ohm=bar["bar_resistance_allocation_mohm"] / 1000,
                qualified=False,
            ),
            dict(
                edge="P03_terminal_assembly",
                endpoint="P03J21.1 solder/stud/bar interfaces",
                assembly_requirement_ohm=hardware["terminal_assembly_resistance_allocation_mohm"] / 1000,
                qualified=False,
            ),
            dict(
                edge="P03_multiport_ground",
                endpoint="J21.1 to actual regulator/reference/inlet ports; signed coupling retained",
                qualified=False,
            ),
        ],
        source_lug_contact_must_not_be_double_counted_in_harness_and_bar_budgets=True,
        existing_PCB_parallel_ground_path_remains_real_and_unremoved=True,
        PCB_force_current_not_assumed_zero_without_complete_parallel_harness_graph=True,
        local_C24_charging_and_transient_return_still_requires_actual_PCB_or_new_force_path=True,
        C20_is_analog_not_digital=True,
        predecessor_E28_only_return_ohm_by_grid={str(r["grid_mm"]): r["ohm"] for r in prior_return},
        predecessor_return_results_not_applied_to_new_force_boundary=True,
        preexisting_fed_wire_ground_world_xy_mm=[161, 126.5],
        P9_current_ground_pad_world_xy_mm=[161, 129.5],
        proposed_new_force_ground_world_xy_mm=center,
        no_prior_wire_native_pass_inherited=True,
        new_lug_body_created=False,
        native_PCB_or_BOM_changed=False,
        physical_startup_PDN_thermal_contact_and_fabrication_qualified=False,
    )
    assert all(p.read_bytes() == blob for p, blob in blobs.items()), "Source changed during read-only capture"
    out = ROOT / "generated/direct-j8-ground-study"
    out.mkdir(exist_ok=True)
    (out / "interface.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Bound actual J8/bar/hardware and bulk/force endpoints; no new lug geometry or topology adopted")


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    main()
