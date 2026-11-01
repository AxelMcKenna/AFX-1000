"""Independent portable EC01 model, native-artifact and sealed-input audit.

This file is intentionally new after the selected geometry was frozen. It never
rewrites any selected input or native source. Geometry pass is not process approval.
"""

import hashlib
import json
import math
import struct
from pathlib import Path

from .bezier import certificate

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
EVIDENCE = ROOT / "native_evidence"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def close(a, b, tol=1e-8):
    return math.dist(a, b) <= tol


def linear(start, finish, n):
    return [[start[j] + (finish[j] - start[j]) * i / n for j in range(3)] for i in range(n + 1)]


def expected_prefix(route):
    p = route["source_prefix_profile"]
    r = p["radius_mm"]
    phi = math.radians(p["angle_deg"])
    start = route["source_face_mm"]
    idx = route["native_boundary_indices"]
    n = idx["source_initial_straight_end"]
    m = idx["source_prefix_end"] - n
    straight = p["initial_straight_mm"]
    end = [start[0], start[1], start[2] + straight]
    pts = linear(start, end, n)
    for i in range(1, m + 1):
        a = math.pi * i / (2 * m)
        pts.append(
            [
                start[0] + r * (1 - math.cos(a)) * math.cos(phi),
                start[1] + r * (1 - math.cos(a)) * math.sin(phi),
                end[2] + r * math.sin(a),
            ]
        )
    return pts


def expected_free(route):
    c = route["connector_model"]
    q = route["sample_contract"]["native"]["free"]
    if c["kind"] == "cubic_bezier":
        controls = c["control_points_mm"]
        n = q["parameter_intervals"]
        pts = []
        for i in range(n + 1):
            t = i / n
            u = 1 - t
            weights = [u**3, 3 * u * u * t, 3 * u * t * t, t**3]
            pts.append([math.fsum(weights[k] * controls[k][j] for k in range(4)) for j in range(3)])
        return pts
    p = c["lift_segment"]
    r = p["radius_mm"]
    alpha = p["half_turn_radians"]
    phi = math.radians(p["heading_deg"])
    h = [math.cos(phi), math.sin(phi), 0]
    start = p["start"]
    n = q["lift_half_intervals"]
    pts = []
    for i in range(n + 1):
        a = alpha * i / n
        pts.append(
            [start[j] + r * math.sin(a) * h[j] + (r * (1 - math.cos(a)) if j == 2 else 0) for j in range(3)]
        )
    midpoint = pts[-1]
    for i in range(1, n + 1):
        a = alpha * i / n
        pts.append(
            [
                midpoint[j]
                + r * (math.sin(alpha) - math.sin(alpha - a)) * h[j]
                + (r * (math.cos(alpha - a) - math.cos(alpha)) if j == 2 else 0)
                for j in range(3)
            ]
        )
    planar = c["start"]
    before = c["initial_straight_mm"]
    arc_start = c["horizontal_arc_start"]
    n_before = max(1, math.ceil(before / 0.25))
    pts += linear(planar, arc_start, n_before)[1:]
    r = c["horizontal_radius_mm"]
    sign = c["turn_sign"]
    phi = math.radians(c["initial_heading_deg"])
    delta = c["horizontal_turn_radians"]
    n = q["horizontal_intervals"]
    for i in range(1, n + 1):
        a = phi + sign * delta * i / n
        pts.append(
            [
                arc_start[0] + sign * r * (math.sin(a) - math.sin(phi)),
                arc_start[1] + sign * r * (math.cos(phi) - math.cos(a)),
                arc_start[2],
            ]
        )
    pts += linear(c["first_join"], c["second_join"], q["straight_intervals"])[1:]
    r = c["vertical_radius_mm"]
    h = c["unit_join_tangent"]
    start = c["second_join"]
    n = q["vertical_intervals"]
    for i in range(1, n + 1):
        a = math.pi * i / (2 * n)
        pts.append(
            [start[j] + r * math.sin(a) * h[j] - (r * (1 - math.cos(a)) if j == 2 else 0) for j in range(3)]
        )
    return pts


def model_errors(data):
    bad = []
    if data["minimum_required_true_centerline_radius_mm"] != 9.6393:
        bad.append("Hard bend radius changed")
    if (
        data["independent_position_allocation_each_wire_mm"] != 0.65
        or data["separate_required_clearance_mm"] != 0.25
        or data["separate_geometry_reserve_mm"] != 0.005
    ):
        bad.append("Position/clearance/reserve weakened")
    if (
        data["physical_fit_verified"]
        or data["strain_relief_qualified"]
        or data["cut_slack_and_fanout_qualified"]
        or data["fabrication_released"]
    ):
        bad.append("Unsupported physical qualification")
    if data["H9_vertical_tool_access_clear"]:
        bad.append("Known H9 tool obstruction erased")
    lengths = []
    global_chord = 0
    for route in data["routes"]:
        pin = route["pin"]
        c = route["connector_model"]
        p = route["source_prefix_profile"]
        s = route["destination_stub"]
        idx = route["native_boundary_indices"]
        full = route["native_points_mm"]
        free = route["native_free_points_mm"]
        q = route["sample_contract"]["native"]
        phi = math.radians(p["angle_deg"])
        heading = [math.cos(phi), math.sin(phi), 0]
        if (
            s["length_mm"] != 7
            or s["bare_length_above_face_mm"] != 3.1
            or s["bare_cut_z_mm"] != 11.2
            or route["source_bare_cut_z_mm"] != 9.72
        ):
            bad.append("Strip or straight stub changed:" + pin)
        expected_finish = [188, 100 if pin == "1" else 104, 15.1]
        if not close(s["start"], expected_finish) or not close(s["finish"], [188, expected_finish[1], 8.1]):
            bad.append("Receiving port moved:" + pin)
        if not close(route["source_face_mm"], [161, 120.5 if pin == "1" else 126.5, 6.62]):
            bad.append("Source port moved:" + pin)
        if abs(p["initial_straight_mm"] - (p["endplane_mm"] - 6.62 - p["radius_mm"])) > 1e-10:
            bad.append("Source circle construction changed:" + pin)
        prefix = expected_prefix(route)
        expected = expected_free(route)
        if len(expected) != len(free) or any(not close(a, b) for a, b in zip(expected, free)):
            bad.append("Native connector points disagree with exact model:" + pin)
        n_stub = len(route["native_stub_points_mm"]) - 1
        stub = linear(s["start"], s["finish"], n_stub)
        combined = prefix + expected[1:] + stub[1:]
        if len(combined) != len(full) or any(not close(a, b) for a, b in zip(combined, full)):
            bad.append("Native full points/boundaries disagree:" + pin)
        if (
            idx["source_prefix_end"] != len(prefix) - 1
            or idx["destination_stub_start"] != len(prefix) + len(expected) - 2
            or idx["destination_face"] != len(full) - 1
        ):
            bad.append("Path boundary index mismatch:" + pin)
        if c["kind"] == "cubic_bezier":
            cp = c["control_points_mm"]
            proof = certificate(cp, 9.6393)
            if not proof["certified"] or proof != route["continuous_radius_certificate"]:
                bad.append("Changed/rejected continuous Bernstein certificate:" + pin)
            initial = [cp[1][j] - cp[0][j] for j in range(3)]
            last = [cp[3][j] - cp[2][j] for j in range(3)]
            if not close(
                [v / math.sqrt(sum(x * x for x in initial)) for v in initial], heading, 1e-12
            ) or not close([v / math.sqrt(sum(x * x for x in last)) for v in last], [0, 0, -1], 1e-12):
                bad.append("Cubic endpoint C1 tangent mismatch:" + pin)
            length = math.fsum(math.dist(a, b) for a, b in zip(cp, cp[1:]))
            radius = proof["radius_lower_mm"]
            v = [[3 * (b - a) for a, b in zip(x, y)] for x, y in zip(cp, cp[1:])]
            accel = [[2 * (b - a) for a, b in zip(x, y)] for x, y in zip(v, v[1:])]
            chord = max(math.sqrt(sum(x * x for x in a)) for a in accel) / (
                8 * q["free"]["parameter_intervals"] ** 2
            )
            analytic_z = min(point[2] for point in cp)
        else:
            lift = c["lift_segment"]
            alpha = lift["half_turn_radians"]
            rh = c["horizontal_radius_mm"]
            rv = c["vertical_radius_mm"]
            rl = lift["radius_mm"]
            radii = [rh, rv, rl]
            radius = min(radii) - 1e-9
            if min(radii) <= 9.6393 or c["initial_straight_mm"] < 0 or c["straight_length_mm"] < 0:
                bad.append("Invalid exact circular primitive:" + pin)
            if abs(2 * rl * (1 - math.cos(alpha)) - lift["total_rise_mm"]) > 1e-10 or not close(
                lift["finish"], c["start"]
            ):
                bad.append("S-lift construction mismatch:" + pin)
            if not close(lift["start"], route["connector_start_mm"]):
                bad.append("Lift/source join moved:" + pin)
            theta = math.radians(c["final_horizontal_heading_deg"])
            h = [math.cos(theta), math.sin(theta), 0]
            if not close(h, c["unit_join_tangent"], 1e-12):
                bad.append("Horizontal/vertical C1 tangent mismatch:" + pin)
            terminal = [c["second_join"][j] + rv * h[j] - (rv if j == 2 else 0) for j in range(3)]
            if not close(terminal, s["start"]):
                bad.append("Circular endpoint moved:" + pin)
            length = (
                2 * rl * alpha
                + c["initial_straight_mm"]
                + rh * c["horizontal_turn_radians"]
                + c["straight_length_mm"]
                + rv * math.pi / 2
            )
            chord = max(
                rl * (alpha / q["free"]["lift_half_intervals"]) ** 2 / 8,
                rh * (c["horizontal_turn_radians"] / q["free"]["horizontal_intervals"]) ** 2 / 8,
                rv * (math.pi / (2 * q["free"]["vertical_intervals"])) ** 2 / 8,
            )
            analytic_z = min(c["start"][2], s["start"][2], lift["start"][2])
        if (
            radius <= 9.6393
            or route["whole_continuous_radius_lower_mm"] > min(p["radius_mm"] - 1e-9, radius) + 1e-10
        ):
            bad.append("Continuous radius lower bound invalid:" + pin)
        prefix_length = p["initial_straight_mm"] + p["radius_mm"] * math.pi / 2
        length += prefix_length + 7 + 2 * (1.76 + 1.5)
        if (
            route["wire_length_upper_mm_including_prefix_stub_boardtails"] + 1e-9 < length
            or route["wire_length_upper_mm_including_prefix_stub_boardtails"] >= 200
        ):
            bad.append("Invalid complete geometric length bound:" + pin)
        lengths.append(route["wire_length_upper_mm_including_prefix_stub_boardtails"])
        m = idx["source_prefix_end"] - idx["source_initial_straight_end"]
        chord = max(chord, p["radius_mm"] * (math.pi / (2 * m)) ** 2 / 8)
        if q["whole_chord_error_bound_mm"] + 1e-12 < chord or q["whole_chord_error_bound_mm"] >= 0.001:
            bad.append("Invalid continuous chord bound:" + pin)
        global_chord = max(global_chord, q["whole_chord_error_bound_mm"])
        min_z = min(6.62 + p["initial_straight_mm"], analytic_z)
        if route["central_minimum_z_mm"] > min_z + 1e-9:
            bad.append("Midpath height bound not conservative:" + pin)
    if abs(sum(lengths) - data["pair_length_upper_mm"]) > 1e-8 or sum(lengths) >= 200:
        bad.append("Pair geometric length target failed")
    height = data["central_height_proof"]
    outer = (data["wire_insulation_OD_max_mm"] / 2 + 0.65 + 0.25 + 0.005) / math.cos(
        math.pi / 64
    ) ** 2 + global_chord
    margin = (
        height["minimum_midpath_center_z_mm"]
        - max(height["source_PCB_max_top_z_mm"], height["receiver_PCB_max_top_z_mm"])
        - outer
    )
    if margin <= 0 or height["minimum_height_margin_mm"] > margin + 1e-9:
        bad.append("Midpath PCB-height proof invalid")
    if not height["endpoint_common_frame_minimum_bore_and_flat_cut_checks_still_required"]:
        bad.append("Endpoint bore obligation erased")
    return bad


def stl(path):
    raw = path.read_bytes()
    if len(raw) < 84:
        raise ValueError("Missing binary native mesh")
    count = struct.unpack_from("<I", raw, 80)[0]
    if count == 0 or len(raw) != 84 + 50 * count:
        raise ValueError("Empty/malformed native mesh")
    vertices = []
    terms = []
    for i in range(count):
        row = struct.unpack_from("<12fH", raw, 84 + 50 * i)
        a, b, c = row[3:6], row[6:9], row[9:12]
        vertices.extend([a, b, c])
        terms.append(
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
    return dict(
        volume_mm3=abs(math.fsum(terms)) / 6,
        triangles=count,
        min_mm=[min(p[j] for p in vertices) for j in range(3)],
        max_mm=[max(p[j] for p in vertices) for j in range(3)],
    )


def case_errors(name, row, folder):
    bad = []
    mesh = folder / (name + ".stl")
    log = folder / (name + ".log")
    if not row.get("clear"):
        bad.append("Rejected native case:" + name)
    if not log.exists():
        return bad + ["Missing native log:" + name]
    text = log.read_text()
    if "WARNING" in text or "ERROR" in text:
        bad.append("Native warning/error:" + name)
    if name.endswith("_collision") and row.get("empty"):
        if mesh.exists() or "Current top level object is empty." not in text:
            bad.append("Forged/inconsistent empty native collision:" + name)
        return bad
    if row.get("empty") or not mesh.exists():
        return bad + ["Missing required actual native solid:" + name]
    actual = stl(mesh)
    if (
        actual["triangles"] != row.get("triangles")
        or abs(actual["volume_mm3"] - row.get("volume_mm3", float("inf"))) > 1e-6
    ):
        bad.append("Native row/STL mismatch:" + name)
    if "NoError" not in text:
        bad.append("Native solid not accepted:" + name)
    if name.endswith("_collision"):
        if actual["volume_mm3"] > 1e-6:
            bad.append("Actual native collision:" + name)
    elif name.endswith("_positive_control"):
        if abs(actual["volume_mm3"] - 0.008) > 1e-6:
            bad.append("Missing actual positive control:" + name)
    elif actual["volume_mm3"] <= 1:
        bad.append("Missing required native geometry:" + name)
    return bad


def packet_errors():
    data = read(OUT / "selected-paths.json")
    bad = model_errors(data)
    for p, h in data["source_sha256"].items():
        if not (ROOT / p).exists() or sha(ROOT / p) != h:
            bad.append("Changed frozen selected source:" + p)
    for p, h in data["captured_input_sha256"].items():
        if not (ROOT / "inputs" / p).exists() or sha(ROOT / "inputs" / p) != h:
            bad.append("Changed captured input:" + p)
    if sha(OUT / "dense-points.json") != data["dense_points_sha256"]:
        bad.append("Changed dense points")
    cap = read(EVIDENCE / "capture.json")
    proof = read(EVIDENCE / "verification.json")
    if cap["selected_paths_sha256"] != sha(OUT / "selected-paths.json"):
        bad.append("Native proof uses different route")
    for p, h in cap["bound_source_evidence_sha256"].items():
        if not (EVIDENCE / "context" / p).exists() or sha(EVIDENCE / "context" / p) != h:
            bad.append("Changed captured ROOT native source:" + p)
    for p, h in cap["copied_raw_artifact_sha256"].items():
        if not (EVIDENCE / p).exists() or sha(EVIDENCE / p) != h:
            bad.append("Changed native raw artifact:" + p)
    if not proof["whole_pair_native_geometry_clear"] or proof["changed_inputs"] or len(proof["cases"]) != 21:
        bad.append("Rejected ROOT21 native proof")
    if (
        proof["H9_tool_access_clear"]
        or proof["physical_fit_verified"]
        or proof["complete_electrical_harness_qualified"]
        or proof["fabrication_released"]
    ):
        bad.append("Unsupported native physical/access promotion")
    for name, row in proof["cases"].items():
        bad += case_errors(name, row, EVIDENCE)
    return bad


def seal_errors():
    saved = read(ROOT / "handoff.json")
    expected = {
        str(p.relative_to(ROOT)): sha(p)
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    }
    return (
        []
        if saved.get("sha256") == expected and saved.get("packet_integrity_accepted") is True
        else ["Changed/rejected connector-search seal"]
    )


def main():
    bad = packet_errors()
    rows = {
        str(p.relative_to(ROOT)): sha(p)
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    }
    saved = dict(
        packet_integrity_accepted=not bad,
        errors=bad,
        sha256=rows,
        external_ROOT21_actual_native_geometry_accepted=not bad,
        physical_fit_verified=False,
        forming_strain_relief_or_solder_process_qualified=False,
        electrical_harness_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(saved, indent=2) + "\n")
    if bad:
        raise SystemExit("\n".join(bad))
    print(
        "EC01 independent model, continuous bounds, frozen inputs and21 native artifacts accepted; no physical qualification."
    )


if __name__ == "__main__":
    main()
