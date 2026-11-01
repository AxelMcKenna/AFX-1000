"""Exact horizontal circular turn / tangent line / vertical quarter-turn construction.

All joins have a common unit tangent under arc-length parameterization, hence
are C1. Curvature is exactly1/R on circular pieces and0 on straight pieces;
no sampled minimum is used as the bend-radius certificate.
"""

import math


def connect(start, initial_heading_deg, finish, final_horizontal_heading_deg, turn_sign):
    if turn_sign not in [-1, 1]:
        raise ValueError("Signed horizontal turn required")
    phi, theta = map(math.radians, [initial_heading_deg, final_horizontal_heading_deg])
    delta = turn_sign * (theta - phi)
    if not 1e-7 < delta < math.pi:
        raise ValueError("Bounded nonlooping turn required")
    vertical = start[2] - finish[2]
    if vertical <= 0:
        raise ValueError("This family needs downward quarter-turn")
    tangent = [math.cos(theta), math.sin(theta), 0.0]
    a = [turn_sign * (math.sin(theta) - math.sin(phi)), turn_sign * (math.cos(phi) - math.cos(theta))]
    dx, dy = finish[0] - start[0], finish[1] - start[1]
    determinant = a[0] * tangent[1] - a[1] * tangent[0]
    if abs(determinant) < 1e-10:
        raise ValueError("Degenerate horizontal construction")
    radius = (dx * tangent[1] - dy * tangent[0]) / determinant
    projected = (a[0] * dy - a[1] * dx) / determinant
    straight = projected - vertical
    if radius <= 0 or straight < 0:
        raise ValueError("Negative radius or straight length")
    p1 = [start[0] + radius * a[0], start[1] + radius * a[1], start[2]]
    p2 = [p1[i] + straight * tangent[i] for i in range(3)]
    predicted = [p2[0] + vertical * tangent[0], p2[1] + vertical * tangent[1], p2[2] - vertical]
    residual = math.dist(predicted, finish)
    lower = min(radius, vertical) - 1e-9
    length = radius * delta + straight + vertical * math.pi / 2
    return dict(
        kind="horizontal_arc_tangent_line_vertical_quarter",
        start=list(start),
        finish=list(finish),
        initial_heading_deg=initial_heading_deg,
        final_horizontal_heading_deg=final_horizontal_heading_deg,
        turn_sign=turn_sign,
        horizontal_radius_mm=radius,
        vertical_radius_mm=vertical,
        horizontal_turn_radians=delta,
        horizontal_turn_degrees=math.degrees(delta),
        straight_length_mm=straight,
        first_join=p1,
        second_join=p2,
        unit_join_tangent=tangent,
        numerical_endpoint_residual_mm=residual,
        geometric_model_numerical_reserve_mm=1e-9,
        minimum_continuous_radius_lower_mm=math.nextafter(lower, 0),
        analytic_length_upper_mm=math.nextafter(length + 1e-9, math.inf),
        arc_length_C1=True,
        curvature_continuity_C2=False,
    )


def connect_general(
    start, initial_heading_deg, finish, final_horizontal_heading_deg, turn_sign, horizontal_radius
):
    phi, theta = map(math.radians, [initial_heading_deg, final_horizontal_heading_deg])
    delta = turn_sign * (theta - phi)
    if not 1e-7 < delta < math.pi or horizontal_radius <= 0:
        raise ValueError("Invalid nonlooping circular turn")
    rv = start[2] - finish[2]
    if rv <= 0:
        raise ValueError("This family needs downward quarter turn")
    h0 = [math.cos(phi), math.sin(phi), 0.0]
    h = [math.cos(theta), math.sin(theta), 0.0]
    a = [turn_sign * (math.sin(theta) - math.sin(phi)), turn_sign * (math.cos(phi) - math.cos(theta))]
    rem = [finish[i] - start[i] - horizontal_radius * a[i] - rv * h[i] for i in range(2)]
    det = h0[0] * h[1] - h0[1] * h[0]
    if abs(det) < 1e-10:
        raise ValueError("Degenerate heading pair")
    before = (rem[0] * h[1] - rem[1] * h[0]) / det
    after = (h0[0] * rem[1] - h0[1] * rem[0]) / det
    if before < 0 or after < 0:
        raise ValueError("Negative tangent line length")
    turn_start = [start[i] + before * h0[i] for i in range(3)]
    first = [turn_start[0] + horizontal_radius * a[0], turn_start[1] + horizontal_radius * a[1], start[2]]
    second = [first[i] + after * h[i] for i in range(3)]
    predicted = [second[0] + rv * h[0], second[1] + rv * h[1], second[2] - rv]
    lower = min(horizontal_radius, rv) - 1e-9
    length = before + horizontal_radius * delta + after + rv * math.pi / 2
    return dict(
        kind="tangent_line_horizontal_arc_tangent_line_vertical_quarter",
        start=list(start),
        finish=list(finish),
        initial_heading_deg=initial_heading_deg,
        final_horizontal_heading_deg=final_horizontal_heading_deg,
        turn_sign=turn_sign,
        horizontal_radius_mm=horizontal_radius,
        vertical_radius_mm=rv,
        horizontal_turn_radians=delta,
        horizontal_turn_degrees=math.degrees(delta),
        initial_straight_mm=before,
        horizontal_arc_start=turn_start,
        straight_length_mm=after,
        first_join=first,
        second_join=second,
        unit_join_tangent=h,
        numerical_endpoint_residual_mm=math.dist(predicted, finish),
        geometric_model_numerical_reserve_mm=1e-9,
        minimum_continuous_radius_lower_mm=math.nextafter(lower, 0),
        analytic_length_upper_mm=math.nextafter(length + 1e-9, math.inf),
        arc_length_C1=True,
        curvature_continuity_C2=False,
    )


def evaluate_base(row, maximum_arc_step=0.05, arc_intervals=None):
    import numpy as np

    start = np.array(row["start"])
    phi = math.radians(row["initial_heading_deg"])
    sign = row["turn_sign"]
    r = row["horizontal_radius_mm"]
    rv = row["vertical_radius_mm"]
    delta = row["horizontal_turn_radians"]
    line = row["straight_length_mm"]
    tangent = np.array(row["unit_join_tangent"])
    na = arc_intervals or max(1, math.ceil(r * delta / maximum_arc_step))
    nb = max(1, math.ceil(line / maximum_arc_step))
    nc = arc_intervals or max(1, math.ceil(rv * math.pi / 2 / maximum_arc_step))
    angles = phi + sign * np.linspace(0, delta, na + 1)
    turn_start = np.array(row.get("horizontal_arc_start", row["start"]))
    first = turn_start + np.column_stack(
        (
            sign * r * (np.sin(angles) - math.sin(phi)),
            sign * r * (math.cos(phi) - np.cos(angles)),
            np.zeros(na + 1),
        )
    )
    second = np.array(row["first_join"]) + np.linspace(0, line, nb + 1)[:, None] * tangent
    alpha = np.linspace(0, math.pi / 2, nc + 1)
    third = (
        np.array(row["second_join"])
        + rv * np.sin(alpha)[:, None] * tangent
        + np.column_stack((np.zeros(nc + 1), np.zeros(nc + 1), -rv * (1 - np.cos(alpha))))
    )
    before = row.get("initial_straight_mm", 0.0)
    n_before = max(1, math.ceil(before / maximum_arc_step))
    phi_heading = np.array([math.cos(phi), math.sin(phi), 0.0])
    prior = start + np.linspace(0, before, n_before + 1)[:, None] * phi_heading
    points = np.vstack([prior, first[1:], second[1:], third[1:]])
    points = points[np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-12]]
    true_step = max(before / n_before, r * delta / na, line / nb, rv * math.pi / 2 / nc)
    chord = max(r * (delta / na) ** 2 / 8, rv * (math.pi / (2 * nc)) ** 2 / 8)
    return points, dict(
        maximum_arc_length_step_mm=true_step,
        continuous_nearest_sample_cover_mm=true_step / 2,
        chord_error_bound_mm=chord,
        point_count=len(points),
        horizontal_intervals=na,
        straight_intervals=nb,
        vertical_intervals=nc,
    )


def lift_connect(
    start,
    initial_heading_deg,
    finish,
    final_horizontal_heading_deg,
    turn_sign,
    horizontal_radius,
    lift_mm,
    lift_radius,
):
    if not 0 < lift_mm < 2 * lift_radius:
        raise ValueError("Invalid upward S lift")
    phi = math.radians(initial_heading_deg)
    alpha = math.acos(1 - lift_mm / (2 * lift_radius))
    run = 2 * lift_radius * math.sin(alpha)
    end = [start[0] + run * math.cos(phi), start[1] + run * math.sin(phi), start[2] + lift_mm]
    row = connect_general(
        end, initial_heading_deg, finish, final_horizontal_heading_deg, turn_sign, horizontal_radius
    )
    row["lift_segment"] = dict(
        start=list(start),
        finish=end,
        radius_mm=lift_radius,
        total_rise_mm=lift_mm,
        half_turn_radians=alpha,
        heading_deg=initial_heading_deg,
        length_upper_mm=2 * lift_radius * alpha + 1e-9,
    )
    row["overall_connector_start_mm"] = list(start)
    row["minimum_continuous_radius_lower_mm"] = min(
        row["minimum_continuous_radius_lower_mm"], lift_radius - 1e-9
    )
    row["analytic_length_upper_mm"] += 2 * lift_radius * alpha + 1e-9
    return row


def evaluate(row, maximum_arc_step=0.05, arc_intervals=None):
    import numpy as np

    if row.get("kind") == "cubic_bezier":
        from .bezier import chord_contract, points

        c = chord_contract(row["control_points_mm"], 1)
        n = arc_intervals or max(1, math.ceil(c["maximum_parameter_speed_upper"] / maximum_arc_step))
        c = chord_contract(row["control_points_mm"], n)
        p = points(row["control_points_mm"], np.linspace(0, 1, n + 1))
        return p, dict(
            maximum_arc_length_step_mm=2 * c["continuous_sample_cover_bound_mm"],
            continuous_nearest_sample_cover_mm=c["continuous_sample_cover_bound_mm"],
            chord_error_bound_mm=c["chord_error_bound_mm"],
            point_count=len(p),
            parameter_intervals=n,
        )
    pts, contract = evaluate_base(row, maximum_arc_step, arc_intervals)
    if "lift_segment" not in row:
        return pts, contract
    lift = row["lift_segment"]
    radius = lift["radius_mm"]
    alpha = lift["half_turn_radians"]
    phi = math.radians(lift["heading_deg"])
    heading = np.array([math.cos(phi), math.sin(phi), 0.0])
    start = np.array(lift["start"])
    n = arc_intervals or max(1, math.ceil(radius * alpha / maximum_arc_step))
    a = np.linspace(0, alpha, n + 1)
    first = (
        start
        + radius * np.sin(a)[:, None] * heading
        + np.column_stack((np.zeros(n + 1), np.zeros(n + 1), radius * (1 - np.cos(a))))
    )
    second = (
        first[-1]
        + radius * (math.sin(alpha) - np.sin(alpha - a))[:, None] * heading
        + np.column_stack((np.zeros(n + 1), np.zeros(n + 1), radius * (np.cos(alpha - a) - math.cos(alpha))))
    )
    joined = np.vstack([first, second[1:], pts[1:]])
    true_step = max(contract["maximum_arc_length_step_mm"], radius * alpha / n)
    contract.update(
        maximum_arc_length_step_mm=true_step,
        continuous_nearest_sample_cover_mm=true_step / 2,
        chord_error_bound_mm=max(contract["chord_error_bound_mm"], radius * (alpha / n) ** 2 / 8),
        point_count=len(joined),
        lift_half_intervals=n,
    )
    return joined, contract


def prefix(profile, maximum_step=0.05):
    import numpy as np

    phi = math.radians(profile["angle_deg"])
    r = profile["radius_mm"]
    straight = profile["initial_straight_mm"]
    start = np.array([161, 120.5 if profile["pin"] == "1" else 126.5, 6.62])
    n = max(1, math.ceil(straight / maximum_step))
    m = max(1, math.ceil(r * math.pi / 2 / maximum_step))
    line = start + np.linspace(0, straight, n + 1)[:, None] * [0, 0, 1]
    a = np.linspace(0, math.pi / 2, m + 1)
    arc = start + np.column_stack(
        (r * (1 - np.cos(a)) * math.cos(phi), r * (1 - np.cos(a)) * math.sin(phi), straight + r * np.sin(a))
    )
    points = np.vstack([line, arc[1:]])
    return points, dict(
        length_upper_mm=profile["curve_length_mm"] + 1e-9,
        radius_lower_mm=r - 1e-9,
        continuous_nearest_sample_cover_mm=max(straight / n, r * math.pi / (2 * m)) / 2,
        chord_error_bound_mm=r * (math.pi / (2 * m)) ** 2 / 8,
    )
