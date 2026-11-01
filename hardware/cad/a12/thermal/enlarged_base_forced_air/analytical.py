"""Independent nominal/profile volume checks; these are not thermal limits."""

import json
import math

from .stage import OUT, ROOT, sha, write


def circular_area(radius, n=None):
    return math.pi * radius**2 if n is None else n * radius**2 * math.sin(2 * math.pi / n) / 2


def rounded_area(w, h, r, n=None):
    return w * h - 4 * r * r + circular_area(r, n)


def tray_volume(n=None):
    a = rounded_area(334, 188.4, 7, n)
    inner = rounded_area(330, 184.4, 5, n)
    return (
        a * 1.5
        + (a - inner) * 18.5
        + 4 * (circular_area(12, n) - circular_area(10.25, n)) * 16.5
        + 4 * (circular_area(13, n) - circular_area(1.7, n)) * 2
        - 4 * circular_area(10.25, n) * 1.5
        - 2 * circular_area(18.75, n) * 1.5
        - 8 * circular_area(2.2, n) * 1.5
        - 266 * 2 * 14
    )


def perforations():
    return [
        (5.2 * (i + math.fmod(j, 2) / 2), j * 5.2 * math.sqrt(3) / 2)
        for j in range(-4, 5)
        for i in range(-4, 5)
        if (5.2 * (i + math.fmod(j, 2) / 2)) ** 2 + (j * 5.2 * math.sqrt(3) / 2) ** 2 < 16.65**2
    ]


def volumes(nominal=False):
    n = None if nominal else 96
    p = None if nominal else 48
    guard = 2 * (
        rounded_area(44, 44, 3, n) - 4 * circular_area(2.2, n) - len(perforations()) * circular_area(2.1, p)
    )
    spacer = 4 * 6 * (circular_area(9, n) - circular_area(1.7, n))
    fan = 2 * 12.5 * (40.5**2 - 4 * circular_area(2.1, n))
    hardware = 8 * (
        20 * circular_area(1.55, n)
        + 3 * circular_area(3, n)
        + 2 * 0.5 * (circular_area(3.7, n) - circular_area(1.7, n))
        + 2.6 * ((3 * math.sqrt(3) / 2) * 3.4**2 - circular_area(1.56, n))
    )
    return dict(
        tray=tray_volume(n), guards=guard, spacers=spacer, fan_receivers=fan, hardware_receivers=hardware
    )


def analyze():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("Sealed analytical evidence cannot be overwritten")
    exact = volumes(True)
    polygon = volumes(False)
    proof = json.loads((OUT / "verification.json").read_text())
    names = dict(
        tray="fa_tray_geometry",
        guards="fa_guard_geometry",
        spacers="fa_spacer_geometry",
        fan_receivers="fa_fan_gauge_geometry",
        hardware_receivers="fa_fastener_gauge_geometry",
    )
    rows = {}
    for key, name in names.items():
        value = proof["cases"][name]["statistics"]["volume_mm3"]
        rows[key] = dict(
            nominal_exact_curves_mm3=exact[key],
            declared_polygon_profile_mm3=polygon[key],
            actual_native_mm3=value,
            native_minus_polygon_mm3=value - polygon[key],
            expected_tessellation_difference_mm3=polygon[key] - exact[key],
        )
    result = dict(
        scope=__doc__,
        perforations_per_guard=len(perforations()),
        rows=rows,
        whole_pin_volume_removed_mm3=77 * 3 * 3 * 12,
        whole_pin_lateral_area_removed_mm2=77 * 4 * 3 * 12,
        exact_parts_and_receiving_gauges_distinguished=True,
        source_sha256={
            str(ROOT / "analytical.py"): sha(ROOT / "analytical.py"),
            str(OUT / "verification.json"): sha(OUT / "verification.json"),
        },
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    write(OUT / "analytical-geometry.json", result)
    print(json.dumps({k: round(v["native_minus_polygon_mm3"], 7) for k, v in rows.items()}))


if __name__ == "__main__":
    analyze()
