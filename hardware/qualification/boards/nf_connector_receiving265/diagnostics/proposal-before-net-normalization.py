"""Actual NF265 connector/force-port placement input, not a full-board fit."""

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KICAD = Path("/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/SharedSupport/footprints/Connector_JST.pretty")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def force_fp():
    return """(footprint "NC265_Force2_18AWG_P5_Drill2p2_Land3p8"
 (version 20241229) (generator "NC265_receiving_proposal") (layer "F.Cu")
 (descr "Custom direct-solder receiving proposal: finished bore MIN2.1, nominal2.2, no manufacturing/process qualification")
 (property "Reference" "J?" (at 2.5 -3) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))
 (property "Value" "DIRECT_18AWG_FORCE" (at 2.5 3) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))
 (attr through_hole)
 (fp_rect (start -2.4 -2.4) (end 7.4 2.4) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
 (pad "1" thru_hole circle (at 0 0) (size 3.8 3.8) (drill 2.2) (layers "*.Cu" "*.Mask"))
 (pad "2" thru_hole circle (at 5 0) (size 3.8 3.8) (drill 2.2) (layers "*.Cu" "*.Mask"))
)\n"""


def native_net_contract(parts):
    xml = ET.parse(ROOT / "inputs/NF265/generated/netlist.xml")
    nets = {}
    for n in xml.findall(".//nets/net"):
        for node in n.findall("node"):
            nets[(node.attrib["ref"], node.attrib["pin"])] = n.attrib["name"]
    ports = {}
    for p in parts:
        if p["ref"] not in {f"J{i}" for i in range(1, 7)}:
            continue
        ports[p["ref"]] = {}
        for pin in p["pins"]:
            expected = pin["net"]
            actual = nets.get((p["ref"], str(pin["number"])))
            if expected != actual:
                raise ValueError(
                    f"Actual native export pin mismatch:{p['ref']}.{pin['number']}:{expected}/{actual}"
                )
            ports[p["ref"]][str(pin["number"])] = actual
    if (
        len(ports) != 6
        or ports["J1"]["4"] is not None
        or ports["J1"]["7"] != "ABS_AUX_FAULT"
        or ports["J6"]["2"] != "MODULE_INPUT_GND"
    ):
        raise ValueError("Wrong final NF265 connector contract")
    return ports


def build():
    if (ROOT / "ports.json").exists() or (ROOT / "ConnectorCandidates.pretty").exists():
        raise RuntimeError("Fresh proposal required; do not change a consumed interface")
    lib = ROOT / "ConnectorCandidates.pretty"
    lib.mkdir()
    files = {}
    for stem in ["JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical", "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"]:
        source = ROOT / "inputs/references/KiCad" / (stem + ".kicad_mod")
        to = lib / source.name
        shutil.copyfile(source, to)
        files[str(to)] = dict(original=str(source), sha256=sha(to), unmodified=True)
    source = KICAD / "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical.kicad_mod"
    to = lib / source.name
    shutil.copyfile(source, to)
    files[str(to)] = dict(original=str(source), sha256=sha(to), unmodified=True)
    shutil.copyfile(ROOT / "inputs/references/KiCad/LICENSE.md", lib / "LICENSE.md")
    force = lib / "NC265_Force2_18AWG_P5_Drill2p2_Land3p8.kicad_mod"
    force.write_text(force_fp())
    files[str(force)] = dict(
        original="NEW custom receiving drawing", sha256=sha(force), manufacturer_approved=False
    )
    parts = json.loads((ROOT / "inputs/NF265/components.json").read_text())
    netmaps = native_net_contract(parts)
    poses = {
        "J1": [5, 17.5],
        "J2": [68, 21],
        "J3": [57, 30],
        "J4": [78, 21],
        "J5": [100, 30],
        "J6": [123, 17.5],
    }
    kinds = {"J1": "PHD30", "J2": "FORCE2", "J3": "PH2", "J4": "FORCE2", "J5": "PH2", "J6": "XH2"}
    profiles = {
        "PHD30": dict(
            footprint=lib / "JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod",
            header="JST B30B-PHDSS",
            housing="JST PHDR-30VS",
            contact="JST SPHD-002T-P0.5",
            wire="Alpha3049 AWG26",
            nominal_catalog_body_uv_bounds_mm=[-1.95, -1.5, 29.95, 3.5],
            catalog_reference_mated_normal_mm=8.8,
            receiving_body_uv_bounds_mm=[-2.2, -1.75, 30.2, 3.75],
            receiving_body_front_normal_mm=10,
            primary_pdf="inputs/references/primary/jst-PHD-public-ES.pdf",
            supplier_guaranteed_maximum=False,
            wire_OD_max_mm=1.3462,
            wire_bend_Rmin_mm=13.462,
            local_bend_candidate_R_mm=14,
        ),
        "PH2": dict(
            footprint=lib / "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical.kicad_mod",
            header="JST B2B-PH-K-S",
            housing="JST PHR-2",
            contact="JST SPH-002T-P0.5S",
            wire="Alpha3049 AWG26",
            nominal_catalog_body_uv_bounds_mm=[-1.95, -1.7, 3.95, 2.8],
            catalog_reference_mated_normal_mm=8,
            receiving_body_uv_bounds_mm=[-2.2, -1.95, 4.2, 3.05],
            receiving_body_front_normal_mm=9,
            primary_pdf="inputs/references/primary/jst-PH-public-US.pdf",
            supplier_guaranteed_maximum=False,
            wire_OD_max_mm=1.3462,
            wire_bend_Rmin_mm=13.462,
            local_bend_candidate_R_mm=14,
        ),
        "XH2": dict(
            footprint=lib / "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical.kicad_mod",
            header="JST B2B-XH-A(LF)(SN)",
            housing="JST XHP-2",
            contact="JST SXH-001T-P0.6",
            wire="Alpha3050 AWG24",
            nominal_catalog_body_uv_bounds_mm=[-2.45, -3.4, 4.95, 2.35],
            catalog_reference_mated_normal_mm=9.8,
            receiving_body_uv_bounds_mm=[-2.7, -3.65, 5.2, 2.6],
            receiving_body_front_normal_mm=10.5,
            primary_pdf="inputs/references/jst-XH-public.pdf",
            supplier_guaranteed_maximum=False,
            wire_OD_max_mm=1.4732,
            wire_bend_Rmin_mm=14.732,
            local_bend_candidate_R_mm=15,
        ),
        "FORCE2": dict(
            footprint=force,
            header=None,
            housing=None,
            contact="Direct solder pigtail; four joint1mohm allocations unaccepted",
            wire="Alpha6715 18AWG MPPE",
            nominal_catalog_body_uv_bounds_mm=None,
            catalog_reference_mated_normal_mm=None,
            receiving_body_uv_bounds_mm=[-2.4, -2.4, 7.4, 2.4],
            receiving_body_front_normal_mm=3.1,
            primary_pdf="inputs/references/primary/alpha6715-current.pdf",
            supplier_guaranteed_maximum=False,
            wire_OD_max_mm=1.7526,
            wire_bend_Rmin_mm=8.763,
            local_bend_candidate_R_mm=9.7,
            finished_bore_min_receiving_mm=2.1,
            nominal_authored_drill_mm=2.2,
            bare_tinned_bundle_max_receiving_mm=1.4,
            relative_centering_receiving_mm=0.3,
            geometry_reserve_mm=0.005,
            radial_gauge_margin_mm=0.045,
            first_straight_insulated_grip_ends_normal_mm=13,
            rear_trim_plus_solder_receiving_mm=1.5,
        ),
    }
    ports = []
    for ref in [f"J{i}" for i in range(1, 7)]:
        profile = dict(profiles[kinds[ref]])
        fp = profile.pop("footprint")
        ports.append(
            dict(
                ref=ref,
                footprint_file=str(fp),
                footprint_sha256=sha(fp),
                anchor_mm=poses[ref],
                rotation_deg=0,
                physical_pads=netmaps[ref],
                **profile,
            )
        )
    plan = dict(
        revision="NC265-ports-prototype",
        exact_electrical_source_seal="f53cdb06d5f8c717ddc7b0b077bedf5ff1b855561d742b6e0197465467738cad",
        source_components_sha256=sha(ROOT / "inputs/NF265/components.json"),
        source_native_netlist_sha256=sha(ROOT / "inputs/NF265/generated/netlist.xml"),
        PCB_outline_mm=[149, 39],
        native_frame=dict(
            u="worldX172+u",
            v="worldZ3.5+v",
            w="worldY180.5-w",
            front_copper_w_mm=0,
            proper_rotation_Rx_deg=90,
            maximum_FR4_receiving_mm=1.76,
            rear_SMD_projection_receiving_mm=1.2,
            rear_THT_trim_plus_fillet_receiving_mm=1.5,
        ),
        ports=ports,
        J1_pin7_output_only_external_drive_permitted=False,
        module_return_AGND_tie_permitted=False,
        native_clip_KO=dict(
            u_centres=[38, 138],
            width_mm=7.2,
            v_intervals_mm=[[0, 1.65], [37.35, 39]],
            all_copper_pad_via_track_pour=True,
        ),
        force_shared_strain_candidate=dict(
            PCB_mount_holes=[
                dict(ref="H101", uv_mm=[61, 21], drill_mm=2.4),
                dict(ref="H102", uv_mm=[90, 21], drill_mm=2.4),
            ],
            all_layer_copper_pad_via_track_pour_exclusion_radius_mm=3.7,
            body_uv_bounds_mm=[58, 17.5, 93, 24.5],
            insulating_posts_normal_mm=[0, 5],
            clamp_contact_normal_mm=[5, 13],
            channel_centres_u_mm=[68, 73, 78, 83],
            channel_centre_v_mm=21,
            proposed_material="MCAM Ketron1000 natural unfilled PEEK; supplier lot/mechanical approval pending",
            channel_diameter_is_matched_measured_wire_minus_trial_compression=True,
            nominal_CAD_channel_diameter_mm=1.65,
            trial_diametric_compression_mm=0.05,
            compression_grip_pull_creep_strength_and_torque_qualified=False,
            mechanical_load_path="Grip to independent insulator/posts to H101/H102 and PCB/carrier mounts; solder joints are not strain anchors",
            PCB_bending_and_existing_carrier_loadpath_qualified=False,
            selected_mount_screw="Accu SPP-M2-5-A2",
            mount_screw_head_max_mm=[4, 1.72],
            screw_length_tolerance_and_PEEK_thread_engagement_unaccepted=True,
        ),
        manufacturer_board_thickness_hold="PHD/XH reference1.6mm; PH applicable0.8..1.6mm. The1.76mm max receiving case is not supplier approved; obtain actual factory acceptance or coherent fabricator thickness contract before adoption.",
        contact_current_and_hot_stall_fault_inrush_crimp_lifetime_retention_qualified=False,
        measured_receiver_maxima_are_project_requirements_NOT_catalog_tolerances=True,
        intended_for_NEW265_repack_old233_WIMA_and_semiconductor_poses_NOT_inherited=True,
        full_board_fit_certified=False,
        full_unit_harness_fit_certified=False,
        physical_qualified=False,
        fabrication_released=False,
        source_sha256={
            str(p): sha(p)
            for p in [Path(__file__), ROOT / "capture.json", ROOT / "inputs/NF265/integration-contract.json"]
        },
        library_sources=files,
    )
    (ROOT / "ports.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                ports=len(ports),
                electrical_pad_contracts=sum(len(p["physical_pads"]) for p in ports),
                PCB_repack_required=True,
                full_board_fit_certified=False,
            )
        )
    )


if __name__ == "__main__":
    build()
