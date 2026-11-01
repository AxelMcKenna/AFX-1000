"""Seal exact selected connector representation, analytic bounds and dense coverage."""

import json
import math
from pathlib import Path

import numpy as np

from . import search
from .arcs import evaluate, prefix
from .bezier import certificate
from .capture import INPUTS, OUT, ROOT, sha


def main():
    raw = json.loads((OUT / "cubic-pairs.json").read_text())
    obs = search.obstacles()
    candidates = raw["recommended_pairs"]
    source = raw["source_profiles"]
    chosen = None
    for candidate in candidates:
        a, b = candidate["positive"], candidate["return_profile"]
        proof = certificate(b["control_points_mm"], search.MIN_R)
        if not proof["certified"] or proof["radius_lower_mm"] <= search.MIN_R:
            continue
        a = search.individual([dict(a)], obs, 0.02)[0]
        b = search.individual([dict(b)], obs, 0.02)[0]
        gap, near = search.pair(a, b, source, 0.02)
        if gap > 0 and a["sample_cover_clear"] and b["sample_cover_clear"]:
            chosen = dict(
                positive=a, return_profile=b, pair_margin_mm=gap, pair_nearest=near, return_certificate=proof
            )
            break
    if chosen is None:
        raise ValueError("No densely verified and continuously certified selected pair")
    routes = []
    dense = {}
    maximum_chord = 0
    for pin, key, net in [("1", "positive", "5V_DIG"), ("2", "return_profile", "AGND")]:
        row = chosen[key]
        p = source[pin]
        arcproof = (
            dict(
                method="Exact circular primitives plus tangent straight pieces under arc-length parameterization",
                radii_mm=[
                    row["lift_segment"]["radius_mm"],
                    row["horizontal_radius_mm"],
                    row["vertical_radius_mm"],
                ],
                radius_lower_mm=row["minimum_continuous_radius_lower_mm"],
                certified=True,
                minimum_required_true_centerline_radius_mm=search.MIN_R,
                all_unit_tangent_joins_C1=True,
                curvature_vectors_may_jump=True,
            )
            if pin == "1"
            else chosen["return_certificate"]
        )
        paths = {}
        contracts = {}
        for name, step in [("native", 0.25), ("dense", 0.02)]:
            pre, pc = prefix(p, step)
            free, fc = evaluate(row, step)
            stub = np.array([row["finish"]]) - np.linspace(0, 7, math.ceil(7 / step) + 1)[:, None] * [0, 0, 1]
            full = np.vstack([pre, free[1:], stub[1:]])
            paths[name] = full.tolist()
            contracts[name] = dict(
                prefix=pc,
                free=fc,
                stub_length_mm=7,
                whole_chord_error_bound_mm=max(pc["chord_error_bound_mm"], fc["chord_error_bound_mm"]) + 1e-9,
                whole_nearest_sample_cover_bound_mm=max(
                    pc["continuous_nearest_sample_cover_mm"],
                    fc["continuous_nearest_sample_cover_mm"],
                    step / 2,
                ),
                point_count=len(full),
            )
            if name == "native":
                free_native = free.tolist()
                stub_native = stub.tolist()
                boundary_indices = dict(
                    source_face=0,
                    source_initial_straight_end=max(1, math.ceil(p["initial_straight_mm"] / step)),
                    source_prefix_end=len(pre) - 1,
                    destination_stub_start=len(pre) + len(free) - 2,
                    destination_face=len(full) - 1,
                )
                central_points = full[
                    boundary_indices["source_initial_straight_end"] : boundary_indices[
                        "destination_stub_start"
                    ]
                    + 1
                ]
                central_min_z = float(central_points[:, 2].min())
                initial_straight_end = full[boundary_indices["source_initial_straight_end"]].tolist()
        maximum_chord = max(maximum_chord, contracts["native"]["whole_chord_error_bound_mm"])
        dense[pin] = paths["dense"]
        board_tails = 2 * (1.76 + 1.5)
        length = p["curve_length_mm"] + 1e-9 + row["analytic_length_upper_mm"] + 7 + board_tails
        routes.append(
            dict(
                pin=pin,
                net=net,
                source_prefix_profile=p,
                connector_model=row,
                connector_start_mm=p["endpoint_mm"],
                destination_stub=dict(
                    start=row["finish"],
                    finish=[188, 100 if pin == "1" else 104, 8.1],
                    length_mm=7,
                    bare_length_above_face_mm=3.1,
                    bare_cut_z_mm=11.2,
                    remaining_straight_insulated_length_mm=3.9,
                ),
                source_face_mm=[161, 120.5 if pin == "1" else 126.5, 6.62],
                source_bare_cut_z_mm=9.72,
                native_boundary_indices=boundary_indices,
                source_initial_straight_end_mm=initial_straight_end,
                central_minimum_z_mm=central_min_z,
                central_minimum_z_analytic_basis="Source quarter monotone up; S-lift monotone up; horizontal circles constantZ; positive quarter monotone down; GND cubic Bernstein convex hull has Z>=15.1. End stub and initial source straight excluded.",
                native_points_mm=paths["native"],
                native_free_points_mm=free_native,
                native_stub_points_mm=stub_native,
                dense_points_file="dense-points.json",
                dense_points_key=pin,
                sample_contract=contracts,
                continuous_radius_certificate=arcproof,
                whole_continuous_radius_lower_mm=min(p["radius_mm"] - 1e-9, arcproof["radius_lower_mm"]),
                wire_length_upper_mm_including_prefix_stub_boardtails=length,
                board_and_tail_length_allocation_mm=board_tails,
                tail_length_each_mm=1.5,
                PCB_thickness_each_max_assumption_mm=1.76,
                unallocated_cut_slack_strain_relief_fanout_length_mm=None,
                C1_parameterization="All pieces reparameterized by arc length. Cubic speed positive by Bernstein certificate; matched endpoint unit tangents. Not C2.",
                dense_free_clearance_lower_estimates_mm=row["clearance_lower_estimates_mm"],
            )
        )
    capture = json.loads((ROOT / "capture.json").read_text())
    boards = json.loads((INPUTS / "electronics.json").read_text())["native"]["boards"]
    source_board = next(b for b in boards if b["id"] == "E28")
    source_pcb_top = source_board["datum"][2] + 0.2 + source_board["thickness_range_allocation_mm"][1]
    receiver_pcb_top = 6.5 + 0.2 + 1.76
    exterior_radius = (
        search.OD / 2 + search.POSITION + search.CLEARANCE + search.RESERVE
    ) * search.CIRC + maximum_chord
    min_mid_z = min(route["central_minimum_z_mm"] for route in routes)
    central_height = dict(
        scope="E28 source and E19 receiver PCBs only; all other component/board obstacles remain checked",
        source_PCB_max_top_z_mm=source_pcb_top,
        receiver_PCB_max_top_z_mm=receiver_pcb_top,
        minimum_midpath_center_z_mm=min_mid_z,
        external_tube_radius_including_chord_mm=exterior_radius,
        minimum_height_margin_mm=min_mid_z - max(source_pcb_top, receiver_pcb_top) - exterior_radius,
        endpoint_common_frame_minimum_bore_and_flat_cut_checks_still_required=True,
        source_and_destination_whole_PCB_exclusion_alone_is_not_valid=True,
    )
    if central_height["minimum_height_margin_mm"] <= 0:
        raise ValueError("Missing midpath height proof")
    models = [
        Path(__file__),
        ROOT / "arcs.py",
        ROOT / "bezier.py",
        ROOT / "search.py",
        ROOT / "capture.py",
        ROOT / "h9_capture.py",
        ROOT / "cubic_return.py",
        ROOT / "capture.json",
        INPUTS / "captured_source_search.py",
    ]
    r = dict(
        scope=__doc__,
        revision="EC01-private-selected-source-to-J13-curves",
        routes=routes,
        dense_pair_clearance_lower_estimate_mm=chosen["pair_margin_mm"],
        dense_pair_nearest=chosen["pair_nearest"],
        obstacle_metadata=obs[-1],
        central_height_proof=central_height,
        case_window_mm=search.WINDOW,
        maximum_native_chord_error_bound_mm=maximum_chord,
        wire_insulation_OD_max_mm=search.OD,
        independent_position_allocation_each_wire_mm=search.POSITION,
        separate_required_clearance_mm=search.CLEARANCE,
        separate_geometry_reserve_mm=search.RESERVE,
        circumscribed_sphere_radius_factor=search.CIRC,
        minimum_required_true_centerline_radius_mm=search.MIN_R,
        pair_length_upper_mm=sum(x["wire_length_upper_mm_including_prefix_stub_boardtails"] for x in routes),
        each_wire_and_pair_length_below200mm_before_unallocated_cut_slack=True,
        captured_input_sha256=capture["captured_inputs_sha256"],
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in models},
        actual_receiving_H9_geometry_captured=True,
        H9_vertical_tool_access_clear=False,
        H9_access_obstacle_identity="Parent native diagnosis: actual DIG-CU; no assembled service access claimed",
        source_refined14_native_pass_receipt="hardware/cad/a12/harness/generated/selected-exit-selected-refined-pair/verification.json",
        ear_post_actual_fit_is_separate_from_service_access=True,
        search_clearance_estimates_are_full_native_boolean_proof=False,
        full_bare_insulation_joint_minimum_bore_cases_complete=False,
        physical_fit_verified=False,
        strain_relief_qualified=False,
        cut_slack_and_fanout_qualified=False,
        fabrication_released=False,
    )
    if maximum_chord >= 0.001 or r["pair_length_upper_mm"] >= 200:
        raise ValueError("Selected geometric bound does not meet search contract")
    for route in routes:
        if route["whole_continuous_radius_lower_mm"] <= search.MIN_R:
            raise ValueError("Continuous radius failed")
    (OUT / "dense-points.json").write_text(json.dumps(dense, indent=2) + "\n")
    r["dense_points_sha256"] = sha(OUT / "dense-points.json")
    (OUT / "selected-paths.json").write_text(json.dumps(r, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                radius=[x["whole_continuous_radius_lower_mm"] for x in routes],
                lengths=[x["wire_length_upper_mm_including_prefix_stub_boardtails"] for x in routes],
                pair_length=r["pair_length_upper_mm"],
                pair_clearance=r["dense_pair_clearance_lower_estimate_mm"],
                chord=maximum_chord,
                source_points_sha256=sha(OUT / "selected-paths.json"),
            ),
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
