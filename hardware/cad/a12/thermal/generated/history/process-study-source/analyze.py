"""Reproducible conditional thermal/compression screens; never a qualification pass."""

import json
import math

from .generate import OUT, REPO, circle_rect_area, contact_contains, lands, load, mounts, pin_centres, sha

HEAT = {
    "U1": (86.8, 10.3, 0.762667),
    "U7": (77.5, 32, 0.122448),
    "U8": (109.5, 32, 1.006249),
    "U10": (92.5, 28.5, 0.214184),
    "U11": (122.5, 17, 0.704935),
    "U13": (109, 8.2, 2.133384),
    "U20": (47, 13, 2.170157),
    "U22": (56, 36, 0.283618),
    "U23": (135, 28, 0.28),
    "U101": (19, 12, 0.848),
    "U102": (25, 20, 0.7),
    "Q101": (10, 13, 0.64),
}


def native_heat_and_vias(d, pcb_path=None):
    from hardware.electronics.common.sexpr import children, first, read_sexpr

    pcb = (
        pcb_path
        if pcb_path is not None
        else REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    )
    tree = read_sexpr(pcb.read_text())
    wall = 25
    construction = pcb.with_name("construction.json")
    if construction.exists():
        from .u13_path import read_construction

        wall = read_construction(construction, sha(pcb))["via_wall_minimum_required_um"]
    actual = {}
    for fp in children(tree, "footprint"):
        props = {str(p[1]): str(p[2]) for p in children(fp, "property")}
        ref = props.get("Reference")
        at = first(fp, "at")
        if ref in HEAT:
            actual[ref] = [float(at[1]) - 100, float(at[2]) - 100, HEAT[ref][2]]
    assert set(actual) == set(HEAT)
    nets = {str(p[1]): str(p[2]).lstrip("/") for p in children(tree, "net") if len(p) > 2}
    fields = []
    for site in lands(d):
        x, y, w, h = site["metal_global"]
        vias = []
        for via in children(tree, "via"):
            at = first(via, "at")
            px, py = float(at[1]) + 68, float(at[2]) + 8
            net = first(via, "net")
            node = nets.get(str(net[1]), str(net[1]).lstrip("/"))
            layer_pair = list(map(str, first(via, "layers")[1:3]))
            if (
                x <= px <= x + w
                and y <= py <= y + h
                and node == site["electrical_node"]
                and layer_pair == ["F.Cu", "B.Cu"]
                and contact_contains(site, px, py)
            ):
                drill = float(first(via, "drill")[1])
                vias.append(dict(x_global_mm=px, y_global_mm=py, finished_bore_mm=drill))
        conductance = sum(1 / via_resistance(drill_mm=v["finished_bore_mm"], plating_um=wall) for v in vias)
        fields.append(
            dict(
                id=site["id"],
                node=site["electrical_node"],
                actual_vias_inside_metal_contact=vias,
                count=len(vias),
                barrel_only_conditional_c_per_w=1 / conductance if conductance else None,
                via_wall_input_um=wall,
                construction_requirement_sha256=sha(construction) if construction.exists() else None,
                assumptions=f"Every counted native through-via is connected top/bottom without spreading/contact penalty;{wall:g}um Cu wall requirement/assumption,385W/mK assumed;resin addsno solid-Cu credit. Required minimum is not received microsection evidence.",
                actual_bore_plating_stackup_and_spreading_verified=False,
            )
        )
    return actual, fields


def compression(d, thicknesses):
    """Worst allocated bondline error around a selected shared board datum."""
    if len(thicknesses) != len(d["thermal_lands"]):
        raise ValueError("Exactly one thickness per actual thermal land is required")
    t = d["tim"]
    b = d["base"]
    if any(x <= 0 for x in thicknesses):
        raise ValueError("Pad thickness must be positive")
    mean = sum(thicknesses) / len(thicknesses)
    desired = b["thermal_land_top_z"] + mean * (1 - t["target_compression_fraction"])
    low, high = b["board_height_shim_range"]
    step = b["board_height_shim_step"]
    shim = min(high, max(low, round((desired - b["board_support_top_z"]) / step) * step))
    gap = b["board_support_top_z"] + shim - b["thermal_land_top_z"]
    error = t["contact_bondline_allocation_uncertainty"]
    corners = [(1 - (gap + error) / x, 1 - (gap - error) / x) for x in thicknesses]
    allowed_low, allowed_high = t["compression_allocation_range"]
    matched = max(thicknesses) - min(thicknesses) <= t["maximum_matched_pad_thickness_spread_mm"] + 1e-9
    domain = (
        t["nominal_thickness"] * (1 - t["thickness_tolerance_fraction"]),
        t["nominal_thickness"] * (1 + t["thickness_tolerance_fraction"]),
    )
    return dict(
        thicknesses_mm=thicknesses,
        selected_equal_shim_mm=shim,
        nominal_gap_mm=gap,
        minimum_compression=min(x[0] for x in corners),
        maximum_compression=max(x[1] for x in corners),
        matched_set=matched,
        compression_allocation_satisfied=matched
        and all(domain[0] - 1e-9 <= x <= domain[1] + 1e-9 for x in thicknesses)
        and all(allowed_low <= x[0] <= x[1] <= allowed_high for x in corners),
        contact_force_compression_set_and_life_verified=False,
    )


def via_resistance(drill_mm=0.3, plating_um=25, count=1, thickness_mm=1.6, copper_k=385):
    if min(drill_mm, plating_um, count, thickness_mm, copper_k) <= 0:
        raise ValueError("Positive via dimensions/material/count required")
    # Drill is finished bore: wall annulus, not a solid copper cylinder.
    r = drill_mm / 2000
    wall = plating_um / 1e6
    area = math.pi * ((r + wall) ** 2 - r**2)
    return thickness_mm / 1000 / (copper_k * area * count)


def overlaps(a, b, clearance=0):
    return min(a[2], b[2]) - max(a[0], b[0]) > -clearance and min(a[3], b[3]) - max(a[1], b[1]) > -clearance


def point_segment_distance(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    norm = vx * vx + vy * vy
    u = min(1, max(0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / norm)) if norm else 0
    return math.dist(p, (a[0] + u * vx, a[1] + u * vy))


def in_polygon(p, points):
    inside = False
    for a, b in zip(points, points[1:] + points[:1]):
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def support_copper_screen(d):
    from hardware.electronics.common.sexpr import children, first, read_sexpr
    from hardware.electronics.output_stage.check_placement import transform

    pcb = REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    features = []
    pad_polygons = []
    unsupported = []
    filled_count = 0
    for via in children(tree, "via"):
        at = first(via, "at")
        p = tuple(map(float, at[1:3]))
        features.append(("via", p, p, float(first(via, "size")[1]) / 2))
    for seg in children(tree, "segment"):
        features.append(
            (
                "segment",
                tuple(map(float, first(seg, "start")[1:3])),
                tuple(map(float, first(seg, "end")[1:3])),
                float(first(seg, "width")[1]) / 2,
            )
        )
    for fp in children(tree, "footprint"):
        for pad in children(fp, "pad"):
            if pad[2] == "np_thru_hole":
                continue
            if not any(str(v).endswith(".Cu") for v in first(pad, "layers")[1:]):
                continue
            pad_at = first(pad, "at")
            p = transform(fp, pad_at[1:3])
            size = list(map(float, first(pad, "size")[1:3]))
            if str(pad[3]) == "circle":
                features.append(("circular-pad", p, p, max(size) / 2))
            elif str(pad[3]) in ("rect", "roundrect", "oval", "custom"):
                angle = math.radians(float(pad_at[3]) if len(pad_at) > 3 else 0)
                polygon = []
                for xx, yy in [
                    (-size[0] / 2, -size[1] / 2),
                    (size[0] / 2, -size[1] / 2),
                    (size[0] / 2, size[1] / 2),
                    (-size[0] / 2, size[1] / 2),
                ]:
                    local = (
                        float(pad_at[1]) + xx * math.cos(angle) + yy * math.sin(angle),
                        float(pad_at[2]) - xx * math.sin(angle) + yy * math.cos(angle),
                    )
                    polygon.append(transform(fp, local))
                pad_polygons.append(polygon)
                if str(pad[3]) == "custom":

                    def world(q):
                        xx, yy = map(float, q)
                        return transform(
                            fp,
                            (
                                float(pad_at[1]) + xx * math.cos(angle) + yy * math.sin(angle),
                                float(pad_at[2]) - xx * math.sin(angle) + yy * math.cos(angle),
                            ),
                        )

                    primitives = first(pad, "primitives")
                    for primitive in primitives[1:]:
                        if primitive[0] == "gr_poly":
                            points = [world(q[1:3]) for q in children(first(primitive, "pts"), "xy")]
                            width = float(first(primitive, "width")[1])
                            if width != 0:
                                unsupported.append("custom-poly-stroke")
                            pad_polygons.append(points)
                        elif primitive[0] == "gr_circle":
                            centre = world(first(primitive, "center")[1:3])
                            end = world(first(primitive, "end")[1:3])
                            # Conservative outer disk for an unfilled copper annulus.
                            features.append(
                                (
                                    "custom-circle-envelope",
                                    centre,
                                    centre,
                                    math.dist(centre, end) + float(first(primitive, "width")[1]) / 2,
                                )
                            )
                        else:
                            unsupported.append(str(primitive[0]))
            else:
                unsupported.append(str(pad[3]))
    polygons = []
    for zone in children(tree, "zone"):
        for fill in children(zone, "filled_polygon"):
            pts = first(fill, "pts")
            poly = [tuple(map(float, p[1:3])) for p in children(pts, "xy")]
            if len(poly) > 2:
                polygons.append(poly)
                filled_count += 1
    answer = []
    for x, y in mounts(d):
        p = (x - 68, y - 8)
        nearest = 1e9
        kind = None
        for name, a, b, r in features:
            gap = point_segment_distance(p, a, b) - r - 3
            if gap < nearest:
                nearest = gap
                kind = name
        for name, poly in [("native-filled-copper", q) for q in polygons] + [
            ("pad-rectangle-envelope", q) for q in pad_polygons
        ]:
            distance = min(point_segment_distance(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))
            gap = (-distance if in_polygon(p, poly) else distance) - 3
            if gap < nearest:
                nearest = gap
                kind = name
        answer.append(
            dict(
                support_global_xy_mm=[x, y],
                nearest_conservative_copper_gap_mm=nearest,
                nearest_feature=kind,
                nominal_metal_contact_free=nearest > 0,
            )
        )
    return dict(
        actual_native_pcb_sha256=sha(pcb),
        checked_filled_polygons=filled_count,
        unsupported_pad_shapes=unsupported,
        unsupported_native_copper_arcs=len(children(tree, "arc")),
        all_ten_nominal_metal_faces_free_of_actual_native_copper=not unsupported
        and not children(tree, "arc")
        and filled_count > 0
        and all(r["nominal_metal_contact_free"] for r in answer),
        supports=answer,
        scope="Actual circle pads and bounding rotated rectangles for rect/roundrect/oval pads,segments,vias and saved filled polygons on all layers against Ø6 support; no solder-mask insulation credit.",
        manufacturer_and_registration_tolerance_approved=False,
        physical_isolation_verified=False,
    )


def geometry_screen(d):
    from hardware.electronics.adc_driver.qualification.audit import REPO
    from hardware.electronics.common.sexpr import children, first, read_sexpr
    from hardware.electronics.output_stage.check_placement import courtyard

    pcb = REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    issues = []
    actual_bottom = []
    supports = mounts(d)
    holes = []
    for fp in children(tree, "footprint"):
        props = {str(p[1]): str(p[2]) for p in children(fp, "property")}
        ref = props.get("Reference", "?")
        at = first(fp, "at")
        # Native P03 origin is100,100; enclosure origin168,108.
        origin = (float(at[1]) - 100 + 168, float(at[2]) - 100 + 108)
        if ref.startswith("H"):
            holes.append((ref, origin))
            continue
        if str(first(fp, "layer")[1]) != "B.Cu":
            continue
        try:
            box = courtyard(fp, "B.CrtYd")
        except AssertionError:
            issues.append(dict(ref=ref, reason="Missing actual bottom courtyard"))
            continue
        # courtyard() already transforms actual native footprint primitives.
        placed = [box[0] + 68, box[1] + 8, box[2] + 68, box[3] + 8]
        actual_bottom.append(dict(ref=ref, courtyard_global_mm=placed))
        for site in lands(d):
            x, y, w, h = site["cut_global"]
            overlap_rect = [
                max(placed[0], x),
                max(placed[1], y),
                min(placed[2], x + w),
                min(placed[3], y + h),
            ]
            interference = overlaps(placed, [x, y, x + w, y + h])
            if interference and "corner_relief" in site:
                a, b, aa, bb = overlap_rect
                relief_area = circle_rect_area(
                    [a, b, aa - a, bb - b],
                    site["relief_centre_global"],
                    site["corner_relief"]["tim_radius_mm"],
                )
                interference = (aa - a) * (bb - b) - relief_area > 1e-8
            if interference:
                issues.append(
                    dict(
                        ref=ref,
                        interference=site["id"],
                        reason="Bottom courtyard intersects compressed TIM prism",
                    )
                )
        for x, y in supports:
            if overlaps(placed, [x - 3, y - 3, x + 3, y + 3]):
                issues.append(
                    dict(
                        ref=ref,
                        interference=[x, y],
                        reason="Bottom courtyard intersects metal support envelope",
                    )
                )
    missing = [list(p) for p in supports if not any(math.dist(p, xy) < 0.01 for _, xy in holes)]
    return dict(
        native_p03_sha256=sha(pcb),
        bottom_courtyards=actual_bottom,
        collisions=issues,
        missing_native_support_holes=missing,
        actual_native_prism_screen_pass=not issues and not missing,
        scope="Actual bottom courtyard/TIM/support prism envelope; excludes component height, copper clearance and full shell. Bottom flip is already in native courtyard geometry.",
        physical_fit_verified=False,
    )


def plate_scenario(d, h, emissivity, ambient=40, radiation_view_factor=0.5, grid=(67, 32)):
    """2D finite-volume aluminum screen, nonlinear radiation, explicit assumed h.

    All10.1W is deliberately assigned to the plate: no invented internal-air
    cooling credit. It assumes perfect board-to-base transfer for unlanded heat,
    and therefore is not a junction prediction. Every edge is adiabatic; only
    outside lower projected area radiates. Pin side area participates in
    convection; no catalog orientation or radiation view-factor proof is used.
    """
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve

    nx, ny = grid
    dx, dy = 0.334 / nx, 0.157 / ny
    area = dx * dy
    k = 167.0  # manufacturer typical, not a certified minimum
    thick = d["base"]["plate_thickness"] / 1000
    pocket_web = min(thick, (1.6 - (d["base"]["plate_top_z"] - d["base"]["plate_thickness"])) / 1000)
    n = nx * ny
    conv = np.full(n, area)
    rad = np.full(n, area)

    def rect_weights(x, y, w, hh):
        xx = np.maximum(0, np.minimum((np.arange(nx) + 1) * dx, x + w) - np.maximum(np.arange(nx) * dx, x))
        yy = np.maximum(0, np.minimum((np.arange(ny) + 1) * dy, y + hh) - np.maximum(np.arange(ny) * dy, y))
        result = np.outer(yy, xx).reshape(n)
        assert result.sum() > 0
        return result / result.sum()

    m = math.sqrt(h * 0.012 / (k * 0.003 * 0.003))
    fin_mL = m * (d["base"]["fin_height"] / 1000 + 0.003 / 4)
    eta = math.tanh(fin_mL) / fin_mL
    for x, y in pin_centres(d):
        weights = rect_weights(x / 1000 - 0.0015, y / 1000 - 0.0015, 0.003, 0.003)
        # Axial square-pin fin efficiency under declared constant h.
        conv += weights * eta * 4 * 0.003 * d["base"]["fin_height"] / 1000
    covered = np.zeros((ny, nx))
    for x, y in d["feet"]["centres"]:
        for a in range(8):
            for b in range(8):
                xx = (np.arange(nx) + (a + 0.5) / 8) * dx - x / 1000
                yy = (np.arange(ny) + (b + 0.5) / 8) * dy - y / 1000
                covered += (xx[None, :] ** 2 + yy[:, None] ** 2 <= 0.009**2) / 64
    # Foot disks suppress outside plate area; no foot conduction/cooling credit.
    covered = np.minimum(1, covered).reshape(n)
    conv -= covered * area
    rad -= covered * area
    q = np.zeros(n)
    native_heat, _ = native_heat_and_vias(d)
    for ref, (x, y, watts) in native_heat.items():
        site = next((s for s in lands(d) if ref in s["refs"]), None)
        if site is not None:
            px, py, w, hh = site["metal_global"]
        else:
            # Declared idealized3x3mm source only; no actual unlanded thermal path is asserted.
            px, py, w, hh = 168 + x - 1.5, 108 + y - 1.5, 3, 3
        weights = rect_weights(px / 1000, py / 1000, w / 1000, hh / 1000)
        if site is not None and "corner_relief" in site:
            weights = weights.reshape(ny, nx) * (w * hh)
            for j in range(ny):
                for i in range(nx):
                    if weights[j, i] <= 0:
                        continue
                    xa, ya = max(px, i * dx * 1000), max(py, j * dy * 1000)
                    xb, yb = min(px + w, (i + 1) * dx * 1000), min(py + hh, (j + 1) * dy * 1000)
                    weights[j, i] -= circle_rect_area(
                        [xa, ya, xb - xa, yb - ya],
                        site["relief_centre_global"],
                        site["corner_relief"]["metal_radius_mm"],
                    )
            weights = weights.reshape(n) / site["metal_contact_area_mm2"]
            assert abs(weights.sum() - 1) < 1e-8 and weights.min() > -1e-10
        q += watts * weights
    reserve = d["design_allocations"]["total_heat_w"] - sum(x[2] for x in HEAT.values())
    assert reserve >= 0
    # Unallocated feedback/supervisor reserve goes to the hottest cluster.
    q += reserve * rect_weights(0.273, 0.112, 0.008, 0.008)
    conduction = lil_matrix((n, n))
    for j in range(ny):
        for i in range(nx):
            p = j * nx + i
            local_t = (
                pocket_web if 0.2065 < (i + 0.5) * dx < 0.2875 and 0.0405 < (j + 0.5) * dy < 0.0735 else thick
            )
            for di, dj in ((1, 0), (0, 1)):
                ii, jj = i + di, j + dj
                if ii >= nx or jj >= ny:
                    continue
                pp = jj * nx + ii
                other_t = (
                    pocket_web
                    if 0.2065 < (ii + 0.5) * dx < 0.2875 and 0.0405 < (jj + 0.5) * dy < 0.0735
                    else thick
                )
                t_eff = 2 / (1 / local_t + 1 / other_t)
                g = k * t_eff * (dy / dx if di else dx / dy)
                conduction[p, p] += g
                conduction[pp, pp] += g
                conduction[p, pp] -= g
                conduction[pp, p] -= g
    sigma = 5.670374419e-8
    temp = np.full(n, ambient + 20)
    for iteration in range(100):
        kelvin = temp + 273.15
        ambk = ambient + 273.15
        grad = h * conv + 4 * emissivity * radiation_view_factor * sigma * rad * kelvin**3
        f = h * conv * (temp - ambient) + emissivity * radiation_view_factor * sigma * rad * (
            kelvin**4 - ambk**4
        )
        matrix = conduction.tocsr()
        matrix.setdiag(matrix.diagonal() + grad)
        new = spsolve(matrix, q - f + grad * temp)
        if float(np.max(np.abs(new - temp))) < 1e-8:
            temp = new
            break
        temp = new
    reject = not bool(np.all(np.isfinite(temp))) or iteration == 99
    actual_w = float(
        np.sum(
            h * conv * (temp - ambient)
            + emissivity
            * radiation_view_factor
            * sigma
            * rad
            * ((temp + 273.15) ** 4 - (ambient + 273.15) ** 4)
        )
    )
    assert not reject and abs(actual_w - d["design_allocations"]["total_heat_w"]) < 1e-6
    maximum = float(np.max(temp))
    return dict(
        h_assumed_w_per_m2k=h,
        emissivity_assumed=emissivity,
        radiation_projected_view_factor_assumed=radiation_view_factor,
        nonlinear_iterations=iteration + 1,
        converged=True,
        aluminum_k_typical_w_per_mk=k,
        grid=[nx, ny],
        pin_fin_efficiency_conditional=eta,
        outside_convection_effective_area_m2=float(conv.sum()),
        lower_projected_radiation_area_m2=float(rad.sum()),
        heat_source_area_scope="Four landed heat sources uniformly over exact metal lands; others idealized3x3mm sources with perfect transfer to plate. Neither models PCB thermal paths.",
        total_w=actual_w,
        plate_max_c=maximum,
        plate_mean_c=float(np.mean(temp)),
        conditional_peak_base_rtheta_c_per_w=(maximum - ambient) / actual_w,
        conditional_60c_coldplate_allocation_satisfied=maximum <= 60,
        convection_or_assembly_qualified=False,
    )


def analytical(d):
    t = d["tim"]
    nominal = t["nominal_thickness"]
    tol = t["thickness_tolerance_fraction"]
    spread = t["maximum_matched_pad_thickness_spread_mm"]
    compression_sweep = [
        compression(d, [nominal * (1 - tol) + (nominal * 2 * tol) * i / 1000] * 4) for i in range(1001)
    ]
    # Exercise a matched set at the permitted spread at both incoming extremes.
    compression_sweep += [
        compression(d, [nominal * (1 - tol), nominal * (1 - tol) + spread] * 2),
        compression(d, [nominal * (1 + tol) - spread, nominal * (1 + tol)] * 2),
    ]
    for i in range(1001):
        a = nominal * (1 - tol) + (nominal * 2 * tol - spread) * i / 1000
        for n in (1, 2, 3):
            compression_sweep.append(compression(d, [a] * n + [a + spread] * (4 - n)))
    sites = []
    for row in lands(d):
        _, _, w, height = row["metal_global"]
        a = row["metal_contact_area_mm2"] * 1e-6
        gap = (6.5 - d["base"]["thermal_land_top_z"]) / 1000
        sites.append(
            dict(
                id=row["id"],
                electrical_node=row["electrical_node"],
                metal_contact_area_mm2=a * 1e6,
                nominal_typical_tim_bulk_c_per_w=gap / 6 / a,
                nominal_typical_aluminum_land_axial_c_per_w=(
                    d["base"]["thermal_land_top_z"] - d["base"]["plate_top_z"]
                )
                / 1000
                / (167 * a),
                interface_contact_resistance_included=False,
                nominal_typical_capacitance_pf=8.8541878128e-12 * 6.5 * a / gap * 1e12,
                nominal_typical_volume_leakage_ohm=1e10 * gap / a,
                isolation_or_thermal_qualified=False,
            )
        )
    return dict(
        total_component_heat_allocation_w=sum(x[2] for x in HEAT.values()),
        total_provision_w=d["design_allocations"]["total_heat_w"],
        required_peak_base_to_ambient_c_per_w=20 / d["design_allocations"]["total_heat_w"],
        compression_sweep_count=len(compression_sweep),
        matched_compression_screen_all_pass=all(
            x["compression_allocation_satisfied"] for x in compression_sweep
        ),
        matched_compression_min=min(x["minimum_compression"] for x in compression_sweep),
        matched_compression_max=max(x["maximum_compression"] for x in compression_sweep),
        unmatched_full_tolerance_extremes=compression(d, [nominal * (1 - tol), nominal * (1 + tol)] * 2),
        naive_4mm_pad_min_thickness_mm=4 * 0.9,
        naive_4mm_pad_over_3p7mm_gap_has_no_guaranteed_contact=4 * 0.9 < 3.7,
        selected_tim_screens=sites,
        via_barrel_only_c_per_w={str(n): via_resistance(count=n) for n in (1, 6, 12, 36)},
        via_copper_k_is_assumed_w_per_mk=385,
        via_finished_bore_mm=0.3,
        via_plating_thickness_allocation_um=25,
        via_resin_fill_thermal_credit=0,
        fr4_under_U8_without_copper_vias_c_per_w=0.0016 / (0.3 * 0.0094 * 0.0108),
        fr4_k_assumed_w_per_mk=0.3,
        all_assumptions_require_material_and_assembly_measurements=True,
        physical_fit_verified=False,
        thermal_qualified=False,
    )


def main():
    d = load()
    pcb = REPO / "hardware/electronics/power_distribution/p03/power_p03.kicad_pcb"
    start_pcb_sha = sha(pcb)
    result = analytical(d)
    result["actual_geometry_screen"] = geometry_screen(d)
    result["actual_support_copper_screen"] = support_copper_screen(d)
    native_heat, fields = native_heat_and_vias(d)
    result["actual_native_heat_assignment"] = native_heat
    result["actual_native_via_field_screens"] = fields
    package_theta = {"P12_U8": 3.0, "N12_U11": 5.5, "RAW17_U13": 3.0}
    tim = {r["id"]: r for r in result["selected_tim_screens"]}
    result["junction_path_screens"] = []
    for field in fields:
        site = next(s for s in d["thermal_lands"] if s["id"] == field["id"])
        ref = site["refs"][0]
        power = HEAT[ref][2]
        ceiling = 85 if ref in ("U1", "U13") else 110
        barrel = field["barrel_only_conditional_c_per_w"]
        package = package_theta.get(field["id"])
        known = (
            package
            + barrel
            + tim[field["id"]]["nominal_typical_tim_bulk_c_per_w"]
            + tim[field["id"]]["nominal_typical_aluminum_land_axial_c_per_w"]
            if package is not None and barrel is not None
            else None
        )
        result["junction_path_screens"].append(
            dict(
                ref=ref,
                power_allocation_w=power,
                project_junction_ceiling_c=ceiling,
                package_theta_jc_c_per_w=package,
                optimistic_known_series_c_per_w=known,
                local_base_assumed_c=60,
                conditional_junction_before_contacts_spreading_uncertainty_c=60 + power * known
                if known is not None
                else None,
                remaining_budget_for_contacts_spreading_and_uncertainty_c_per_w=(ceiling - 60) / power - known
                if known is not None
                else None,
                all_heat_assumed_downward_to_same_field=True,
                filled_copper_spreading_contact_and_uncertainty_included=False,
                thermal_path_qualified=False,
            )
        )
    result["conditional_plate_scenarios"] = [
        plate_scenario(d, h, e) for h, e in ((1, 0.8), (2, 0.8), (3, 0.8), (5, 0.8), (3, 0.05))
    ]
    result["numerical_grid_sensitivity_at_h3"] = [
        plate_scenario(d, 3, 0.8, grid=g) for g in ((134, 64), (268, 128))
    ]
    result["numerical_grid_peak_span_c"] = max(
        x["plate_max_c"]
        for x in result["numerical_grid_sensitivity_at_h3"] + [result["conditional_plate_scenarios"][2]]
    ) - min(
        x["plate_max_c"]
        for x in result["numerical_grid_sensitivity_at_h3"] + [result["conditional_plate_scenarios"][2]]
    )
    initial = json.loads(json.dumps(d))
    initial["base"].update(plate_thickness=3.2, fin_height=8, fin_pitch=9)
    result["rejected_smaller_base_counterfactual"] = dict(
        plate_thickness_mm=3.2,
        fin_height_mm=8,
        fin_pitch_mm=9,
        scope="Recomputed at the same current native XY heat sources and10.1W provision; rejected against60C allocation",
        scenario=plate_scenario(initial, 5, 0.8),
    )
    result["loss_allocation_status"] = (
        "Corrected per-device allocations from P03 heatmap include Q1010.64W and actual negative14V change. Total10.1W remains a conservative provision above9.865642W allocated heat; reserve goes to U13 cluster. No converter external losses counted twice."
    )
    result["all_heat_source_losses_independently_measured"] = False
    result["scope"] = (
        "Conditional allocation/sensitivity screens; TIM interfaces and package junction spreading are not solved; no assumed h is a natural-convection guarantee. All internal heat is placed at its native component footprint onto a 2D coldplate grid."
    )
    assert start_pcb_sha == sha(pcb), "P03 changed during numerical run; reject and rerun"
    (OUT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("actual_geometry_screen",)}, indent=2))


if __name__ == "__main__":
    main()
