"""NC01 source-backed connector comparison, with no canonical PCB changes."""

import hashlib
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wire_fit(nominal_inches, tolerance_inches, minimum_od, maximum_od, bend_diameters):
    interval = [(nominal_inches - tolerance_inches) * 25.4, (nominal_inches + tolerance_inches) * 25.4]
    return dict(
        OD_mm=interval,
        OD_inside_contact_window=interval[0] >= minimum_od and interval[1] <= maximum_od,
        minimum_centerline_bend_radius_mm=bend_diameters * interval[1],
    )


def contact_screen(per_interface, interfaces=2, allocation=0.005):
    if min(per_interface, allocation) <= 0 or interfaces < 1:
        raise ValueError("Positive physical inputs required")
    total = interfaces * per_interface
    return dict(
        series_interfaces=interfaces,
        complete_contact_ohm=total,
        allocation_ohm=allocation,
        ratio_to_allocation=total / allocation,
        within_allocation=total <= allocation,
    )


def phd_pin_xy(number):
    if not 1 <= number <= 30:
        raise ValueError("PHD30 circuit number must be1..30")
    return [2 * ((number - 1) // 2), 2 * ((number - 1) % 2)]


def layer_bounds(fp, layer):
    points = []
    for kind in ["fp_line", "fp_rect"]:
        for a in children(fp, kind):
            if first(a, "layer")[1] == layer:
                points += [[float(v) for v in first(a, key)[1:3]] for key in ["start", "end"]]
    return [
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
    ]


def library_contract(path):
    fp = read_sexpr(path.read_text())
    pads = {int(p[1]): p for p in children(fp, "pad")}
    assert set(pads) == set(range(1, 31))
    rows = []
    for n, p in sorted(pads.items()):
        xy = [float(v) for v in first(p, "at")[1:3]]
        assert xy == phd_pin_xy(n)
        rows.append(
            dict(
                number=n,
                local_xy_mm=xy,
                finished_drill_mm=float(first(p, "drill")[1]),
                land_mm=[float(v) for v in first(p, "size")[1:3]],
            )
        )
    assert all(r["finished_drill_mm"] == 0.75 and r["land_mm"] == [1.2, 1.2] for r in rows)
    fab = layer_bounds(fp, "F.Fab")
    court = layer_bounds(fp, "F.CrtYd")
    assert all(abs(a - b) < 1e-9 for a, b in zip(fab, [-1.95, -1.5, 29.95, 3.5]))
    return dict(
        circuits=rows,
        nominal_FFab_bounds_mm=fab,
        library_courtyard_bounds_mm=court,
        library_drill_is_manufacturer_approved=False,
        catalog_reference_drill_range_mm=[0.7, 0.8],
        catalog_nonaccumulating_pitch_tolerance_mm=0.05,
        body_maximum_dimensions_established=False,
        catalog_frame_is_mounting_face=True,
        old_regional_solder_side_diagram_not_used_for_pin_orientation=True,
    )


def build():
    out = ROOT / "generated"
    capture = ROOT / "capture.json"
    if capture.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("New snapshot required")
    out.mkdir(exist_ok=False)
    nf = REPO / "hardware/qualification/boards/startup_negative_circuit"
    selected = [
        (nf / "standalone_sequence", n, "NF05S")
        for n in [
            "components.json",
            "negative_startup_sequence.kicad_sch",
            "generated/netlist.xml",
            "generated/erc.json",
            "generated/native-review.json",
            "generated/analysis.json",
        ]
    ]
    selected += [
        (nf / "ready_integration", "components.json", "NF04R"),
        (nf / "ready_integration", "integration-contract.json", "NF04R"),
        (nf / "compact", "parameters.json", "NF03C"),
        (nf / "compact", "generated/analysis.json", "NF03C"),
    ]
    library = Path(
        "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints/Connector_JST.pretty"
    )
    selected += [
        (library, "JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod", "KiCad"),
        (library, "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical.kicad_mod", "KiCad"),
    ]
    originals = {}
    copies = {}
    for folder, n, label in selected:
        p = folder / n
        before = sha(p)
        q = ROOT / "sources/repository" / label / n
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, q)
        assert sha(q) == before == sha(p)
        originals[str(p)] = before
        copies[str(q.relative_to(ROOT))] = before
    capture.write_text(
        json.dumps(
            dict(source_sha256=originals, copied_sha256=copies, canonical_or_sealed_files_edited=False),
            indent=2,
        )
        + "\n"
    )
    parts = json.loads((ROOT / "sources/repository/NF05S/components.json").read_text())
    by = {p["ref"]: p for p in parts}
    pinmap = {
        r: {str(p["number"]): dict(net=p["net"], name=p["name"]) for p in by[r]["pins"]}
        for r in ["J1", "J2", "J3", "J4", "J5"]
    }
    assert len(pinmap["J1"]) == 30 and all(len(pinmap[r]) == 2 for r in ["J2", "J3", "J4", "J5"])
    p = json.loads((ROOT / "sources/repository/NF03C/parameters.json").read_text())
    analysis = json.loads((ROOT / "sources/repository/NF03C/generated/analysis.json").read_text())
    comparisons = []
    for a in analysis["n12_source_recenter_comparisons"]:
        row = dict(
            resistor_comparison_ohm=a["proposed_r40_total_ohm"],
            source_recenter_implemented=a["proposed_source_change_implemented"],
        )
        i = a["steady_bank_force_current_requirement_a"]
        margin = a["guarded_low_margin_v"]
        row.update(
            allocated_force_current_a=i,
            original_guarded_low_margin_v=margin,
            PHD_two_interfaces_initial_extra_guarded_drop_v=1.2
            * i
            * (0.020 - p["new_negative_force_contacts_total_requirement_ohm"]),
            PHD_two_interfaces_environment_extra_guarded_drop_v=1.2
            * i
            * (0.040 - p["new_negative_force_contacts_total_requirement_ohm"]),
        )
        row["new_environment_guarded_low_margin_without_any_wire_v"] = (
            margin - row["PHD_two_interfaces_environment_extra_guarded_drop_v"]
        )
        comparisons.append(row)
    facts = dict(
        PHD=dict(
            header="B30B-PHDSS",
            mate="PHDR-30VS",
            contacts=["SPHD-001T-P0.5", "SPHD-002T-P0.5"],
            pitch_mm=2,
            nominal_contact_span_mm=28,
            nominal_body_length_mm=31.9,
            nominal_body_depth_mm=5,
            reference_mating_height_mm=8.8,
            nominal_header_height_mm=6.5,
            reference_unsoldered_tail_mm=3,
            rated_current_a=3,
            rating_wire_AWG=22,
            rated_voltage_v=250,
            temperature_C=[-25, 85],
            initial_contact_max_ohm=0.010,
            environment_contact_max_ohm=0.020,
            lock="friction, not positive latch",
            retention_force_minimum_N=None,
            minimum_dry_circuit_suitability_established=False,
            maximum_mating_dimensions_mm=None,
            permitted_board_thickness_catalog_mm=1.6,
            actual_boardmax1p76_accepted=False,
            SPHD001=dict(AWG=[26, 22], OD_mm=[1.0, 1.5]),
            SPHD002=dict(AWG=[28, 24], OD_mm=[0.9, 1.5]),
            crimp_tooling="JST matched AP-K2N/MKS-L-10/APLMK SPHD001-05 or manufacturer-approved handtool; exact die/wire settings unaccepted",
            public_catalog="https://www.jst-mfg.com/product/pdf/eng/ePHD.pdf",
            captured_public_catalog="sources/primary/jst-PHD-public-ES.pdf",
            exact_drawing_manual_CAD_restricted_by_form=True,
            restricted_terms_accepted=False,
            personal_data_submitted=False,
        ),
        PH2=dict(
            header="B2B-PH-K-S(LF)(SN)",
            mate="PHR-2",
            contact="SPH-002T-P0.5S",
            pitch_mm=2,
            nominal_header_mm=[5.9, 4.5, 6],
            nominal_housing_mm=[5.8, 4.5, 6.85],
            reference_mated_height_mm=8,
            current_rating_a=2,
            rating_AWG=24,
            voltage_v=100,
            temperature_C=[-40, 105],
            initial_contact_max_ohm=0.010,
            after_test_contact_max_ohm=0.020,
            maximum_mated_dimensions_established=False,
            minimum_dry_circuit_suitability_established=False,
            use="Candidate keyed/shrouded low-current J3/J5 only; not5mohm force-path acceptance",
            public_catalog="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf",
        ),
        PHD_two_circuit_candidate=dict(
            catalog_available=False, reason="PHD catalog starts8circuits; do not invent B2B-PHDSS"
        ),
    )
    wires = {
        n: wire_fit(a, 0.002, lo, 1.5, 10)
        for n, a, lo in [
            ("Alpha3049", 0.051, 0.9),
            ("Alpha3050", 0.056, 0.9),
            ("Alpha3051_rejected", 0.062, 1.0),
        ]
    }
    wires["Alpha3049"].update(
        AWG=26,
        stranding="7/34",
        proposed_contact="SPHD-002T-P0.5",
        primary="https://www.alphawire.com/en/products/wire/hook-up-wire/premium/3049",
        DCR20_nominal_ohm_per_m=41 / 304.8,
    )
    wires["Alpha3050"].update(
        AWG=24,
        stranding="7/32",
        proposed_contact="SPHD-002T-P0.5 or SPHD-001T-P0.5 with correct die",
        primary="https://www.alphawire.com/en/products/wire/hook-up-wire/premium/3050",
        DCR20_nominal_ohm_per_m=25 / 304.8,
    )
    result = dict(
        revision="NC01-preselection-source-and-pin-contract",
        captured_NF05S_parts=len(parts),
        NF05S_pincontract=pinmap,
        connector_facts=facts,
        wire_candidates=wires,
        library=library_contract(
            ROOT / "sources/repository/KiCad/JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod"
        ),
        source_number_to_candidate_PHD_pad={
            n: dict(net=v["net"], pad_xy_mm=phd_pin_xy(int(n))) for n, v in pinmap["J1"].items()
        },
        old90degree_generic_pin_locations_preserved=False,
        all_J1_force_and_sense_nets_physically_rerouted_required=True,
        split_guarded12_primary_return_proposal_not_yet_frozen=True,
        force_contact_screens={
            n: contact_screen(r)
            for n, r in [
                ("PHD_PH_initial", 0.010),
                ("PHD_PH_environment", 0.020),
                ("MegaFit_initial_only", 0.002),
                ("MegaFit_initial_plus_environmental_change", 0.004),
            ]
        },
        force_contact_allocation_is_unaccepted_requirement=True,
        force_source_corner_sensitivities=comparisons,
        force_pigtail_candidate=dict(
            method="Four direct solder joints in each complete P03→NF→E28 force path, with independent mechanical strain transfer",
            removable_mating_interfaces=0,
            planning_joint_allocation_ohm=0.001,
            planning_four_joints_total_ohm=0.004,
            joint_allocation_is_NOT_guaranteed_solder_resistance=True,
            wire_length_DCR_must_be_added_separately=True,
            selected_wire_and_land_and_strain_geometry_ready=False,
            complete_hot_lifetime_measurement_required=True,
        ),
        lower_R_power_connector_counterexample=dict(
            primary="https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/172/172063/1720631000-PS-000.pdf",
            revision="D2026-03-24",
            initial_max_per_contact_ohm=0.002,
            temperature_life_and_shock_change_from_initial_ohm=0.002,
            two_series_interfaces_not_lifetime_qualified_for5mohm=True,
            salt_spray_change_ohm=0.020,
            wire_R_excluded_from_catalog_test=True,
            selected_specific_series_contact_and_housing=False,
        ),
        next_required=[
            "Freeze NF05 splitprimary/return+controlpin contract with electrical owner.",
            "Obtain exact dimensional tolerances and crimp/retention settings without redistributing restricted vendor files.",
            "Build NEW actual connector footprint/pose+wirefanout candidate; renewedwholeunitfit includingforce solderlands/strainretention.",
            "Resolve dry-circuit contacts and loaded current/temperature derating.",
            "Include fullwire resistance, endpoints and measured hot/lifetime joint acceptance in force ledger.",
        ],
        canonical_PCB_edited=False,
        connector_selection_production_adopted=False,
        physical_qualified=False,
        electrical_qualified=False,
        full_harness_qualified=False,
        fabrication_released=False,
        source_sha256={str(Path(__file__)): sha(Path(__file__)), str(capture): sha(capture)},
        primary_local_sha256={str(p): sha(p) for p in (ROOT / "sources/primary").glob("*.pdf")},
    )
    (out / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                parts=len(parts),
                PHDpads=30,
                force_series_PHD_environment_ohm=0.04,
                force_budget_ohm=0.005,
                production_adopted=False,
            )
        )
    )


if __name__ == "__main__":
    build()
