"""Final nominal receiving datums; every manufacturing field stays unaccepted."""

import json
from pathlib import Path

from .capture import ROOT, sha


def build():
    out = ROOT / "generated/interface-final.json"
    if out.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("New output required")
    mounts = []
    for board, u, x, H, height in [
        ("NF233", 38, 210, 42.5, 39),
        ("NF233", 138, 310, 42.5, 39),
        ("FPC84", 17, 31, 41.5, 38),
        ("FPC84", 54.5, 68.5, 41.5, 38),
    ]:
        mounts.append(
            dict(
                board=board,
                local_u=u,
                world_X=x,
                board_top_Z=H,
                bottom_contact_local_uv=[u - 3, 0, 6, 1.2],
                top_contact_local_uv=[u - 3, height - 1.2, 6, 1.2],
                screw_axis_world_XY=[x, 184.0],
                keeper_width_X=6,
                keeper_section_YZ=[
                    [179.9, H - 1.2],
                    [180.5, H - 1.2],
                    [180.5, H + 0.2],
                    [182.5, H + 0.2],
                    [182.5, H - 0.95],
                    [185.7, H - 0.95],
                    [185.7, 43.6],
                    [179.9, 43.6],
                ],
                column_stem_bounds=[[x - 3, 184.3, 2.8], [x + 3, 186.2, H - 0.95]],
                upper_thread_boss_bounds=[[x - 2, 182.5, 35.5], [x + 2, 186.2, H - 0.95]],
                toe_bounds=[[x - 3, 179.9, 2.8], [x + 3, 185.7, 4.7]],
                keeper_wall_pocket_bounds=[[x - 3.15, 183.6, H - 0.97], [x + 3.15, 185.8, 43.62]],
                future_all_Cu_layer_keepout_local_uv=[
                    [u - 3.6, 0, 7.2, 1.65],
                    [u - 3.6, height - 1.65, 7.2, 1.65],
                ],
                keepout_native_adopted=False,
            )
        )
    d = dict(
        id="FR01",
        boards=dict(
            NF233=dict(
                origin=[172, 180.5, 3.5],
                size=[149, 39],
                native_source_sha256="9fe0966bd98cb980ede898ab9a18a6b411e984c4e4e41e84b16a313464fb3f68",
                routing_open_connections=499,
            ),
            FPC84=dict(
                origin=[14, 180.5, 3.5],
                size=[66, 38],
                native_geometry_parent_sha256="9a4c60467fcbfcebdf8d0cc87e3fb7599c6a360d0bc2828cf7cb6e6a357038e8",
                closed_source_sha256="86e07ac447103ea9974a1b92a50dbe14063d4debb93058931cf83557ba3a548d",
                closed_source_applied_by_C7_strict_subset_only=True,
            ),
        ),
        frame="[u,v,w] -> [X0+u,180.5-w,3.5+v]; w=0 is F copper face; proper Rx+90",
        FR4_maximum_thickness_mm=1.76,
        rear_SMD_assembled_requirement_mm=1.2,
        rear_THT_lead_fillet_requirement_mm=1.5,
        external_receiver_margin_mm=0.45,
        margin_breakdown=dict(position=0.2, clearance=0.25),
        mounting=mounts,
        body_front_plane_Y=180.5,
        nominal_backplane_Y=182.1,
        top_contact_gap_mm=0.2,
        backside_channel_width_mm=2.0,
        backside_matched_shim_requirement="Match measured board thickness to channel; nominal0.4 at1.6mm, range not supplier approved",
        channel_thickness_remainder_at_FR4max_mm=0.24,
        front_wall_original_inner_Y=185.6,
        local_wall_pocket_depth_mm=0.2,
        remaining_wall_thickness_local_mm=2.6,
        column_wall_overlap_mm=0.6,
        fastener_receiving=dict(
            screw_candidate="Accu SPP-M2-10-A4",
            screw_primary="https://www.accu.co.uk/pozi-pan-head-screws/9373-SPP-M2-10-A4",
            washer_candidate="Accu HPW-M2-V1-A2",
            washer_primary="https://www.accu.co.uk/metric-flat-washers/415465-HPW-M2-V1-A2",
            shank_max_diameter_mm=2.1,
            underhead_Z=46.0,
            tip_Z=35.8,
            receiving_length_mm=10.2,
            head_max_diameter_mm=4,
            head_projection_requirement_mm=2.1,
            washer_OD=5,
            washer_ID=2.2,
            washer_thickness_requirement=0.4,
            lid_keeper_clearance_bore_diameter_mm=2.4,
            nominal_pilot_diameter_mm=1.6,
            assembly_thread_receiving_major_diameter_mm=2.12,
            assembly_major_thread_Z_start=35.79,
            major_gauge_only_used_for_actual_shank_overlap=True,
            minimum_planning_engagement_mm=dict(NF233=5.35, FPC84=4.35),
            engagement_basis="9.8 minimum length REQUIREMENT minus .4 washer minus2 lid minusNF2.05/FPC3.05 keeper; length tolerances not manufacturer accepted",
            torque_Nm=None,
            polymer_grade=None,
            tap_process=None,
            thread_and_creep_strength_accepted=False,
        ),
        PCB_soldermask_insulation_credit=False,
        all_layer_edge_copper_keepouts_adopted=False,
        nominal_test_only_contact_guard_mm=0.00002,
        guard_scope="Only named PCB seat planes / keeper support plane / screw bearing plane; physical parts byte-identical to raw trial",
        assembly_sequence=[
            "Fit boards in lower edge channels with matched measured-thickness shims.",
            "Fit four removable keepers and panel aligned bores.",
            "Fit four M2-class screws/washers to positively captured columns.",
            "To remove panel, first remove the four keeper screws and support cards temporarily; full harness extraction/slack remains unproven.",
        ],
        open_holds=[
            "NF generic connector mate collision1.416178mm3: J5/C31/C32, J2/Q1, J4/Q2; exact connector selection required.",
            "195 part-class project height ceilings and WIMA/TLP seating maxima need actual selected-package acceptance.",
            "Material, dimensions, print/machine process, wall strength, tap engagement, creep and torque unaccepted.",
            "Native edge copper keepout successor not adopted; no soldermask insulation credit.",
            "Local14 reference wire exits are not complete crimped/strained/current-rated harnesses.",
            "Port shadow is vertical projection sensitivity; no air-path/pressure/installed thermal proof.",
        ],
        physical_qualified=False,
        thermal_qualified=False,
        electrical_unit_qualified=False,
        full_harness_qualified=False,
        fabrication_released=False,
        source_sha256={
            str(p): sha(p)
            for p in [
                Path(__file__),
                ROOT / "mount_variant5/checks.scad",
                ROOT / "generated/coherent-receiving-model.json",
                ROOT / "generated/FPCClosed-C7-delta.json",
            ]
        },
    )
    out.write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                mounts=4,
                contact_centres={
                    n: [m["local_u"] for m in mounts if m["board"] == n] for n in ["NF233", "FPC84"]
                },
            )
        )
    )


if __name__ == "__main__":
    build()
