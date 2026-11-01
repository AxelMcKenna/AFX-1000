"""Captured T01 geometry helpers, unchanged math; no live native source dependency."""

import math


def pin_centres(d):
    feet = d["feet"]["centres"]
    bolts = d["shell_fasteners"]
    answer = []
    for x in range(d["base"]["fin_border"], 334 - d["base"]["fin_border"] + 1, d["base"]["fin_pitch"]):
        for y in range(d["base"]["fin_border"], 157 - d["base"]["fin_border"] + 1, d["base"]["fin_pitch"]):
            if any(math.dist((x, y), c) < 12 for c in feet):
                continue
            if any(math.dist((x, y), c) < 6 for c in bolts):
                continue
            if any(
                math.dist((x, y), c)
                < d["return_support_attachments"]["fin_exclusion_radius"] + math.sqrt(2) * 1.5
                for c in d.get("return_support_attachments", {}).get("centres", [])
            ):
                continue
            answer.append((x, y))
    return answer


def mounts(d):
    return [
        (d["p03_datum"][0] + p[0], d["p03_datum"][1] + p[1])
        for p in d["board_mounts_relative"] + d["proposed_local_mounts_relative"]
    ]


def lands(d):
    result = []
    inset = d["tim"]["metal_land_inset_each_edge"]
    for row in d["thermal_lands"]:
        x, y, w, h = row["cut_relative"]
        x += d["p03_datum"][0]
        y += d["p03_datum"][1]
        site = dict(
            row,
            cut_global=[x, y, w, h],
            metal_global=[x + inset, y + inset, w - 2 * inset, h - 2 * inset],
        )
        if "corner_relief" in row:
            rx, ry = row["corner_relief"]["centre_relative"]
            site["relief_centre_global"] = [rx + d["p03_datum"][0], ry + d["p03_datum"][1]]
        site["metal_contact_area_mm2"] = contact_area(site, "metal")
        site["tim_cut_area_mm2"] = contact_area(site, "cut")
        result.append(site)
    return result


def circle_rect_area(rect, centre, radius):
    """Exact area of an axis-aligned rectangle intersecting a circle."""
    x, y, w, h = rect
    cx, cy = centre
    low, high = max(-radius, x - cx), min(radius, x + w - cx)
    if high <= low:
        return 0.0
    breaks = [low, high]
    for yy in (y - cy, y + h - cy):
        if abs(yy) < radius:
            a = math.sqrt(radius**2 - yy**2)
            breaks += [z for z in (-a, a) if low < z < high]

    def primitive(z):
        return (
            z * math.sqrt(max(0, radius**2 - z**2)) + radius**2 * math.asin(max(-1, min(1, z / radius)))
        ) / 2

    answer = 0.0
    for a, b in zip(sorted(breaks), sorted(breaks)[1:]):
        root = math.sqrt(max(0, radius**2 - ((a + b) / 2) ** 2))
        lower, upper = max(y - cy, -root), min(y + h - cy, root)
        if upper <= lower:
            continue
        upper_integral = (y + h - cy) * (b - a) if y + h - cy < root else primitive(b) - primitive(a)
        lower_integral = (y - cy) * (b - a) if y - cy > -root else -primitive(b) + primitive(a)
        answer += upper_integral - lower_integral
    return answer


def contact_area(site, kind="metal"):
    rect = site[kind + "_global"]
    area = rect[2] * rect[3]
    if "corner_relief" in site:
        radius = site["corner_relief"]["metal_radius_mm" if kind == "metal" else "tim_radius_mm"]
        area -= circle_rect_area(rect, site["relief_centre_global"], radius)
    return area
