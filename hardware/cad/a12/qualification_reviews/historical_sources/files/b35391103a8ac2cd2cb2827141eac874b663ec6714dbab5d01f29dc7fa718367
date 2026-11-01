"""Exact selected-part geometry requirements; project seating is not a guarantee."""

import re

PARTS = {
    "C1005X7R1H104K050BB": {
        "footprint": "Capacitor_SMD:C_0402_1005Metric",
        "body_max_mm": [1.05, 0.55, 0.55],
        "seat_mm": 0.10,
    },
    "C2012X7R1H225K125AC": {
        "footprint": "Capacitor_SMD:C_0805_2012Metric",
        "body_max_mm": [2.20, 1.45, 1.45],
        "seat_mm": 0.10,
    },
    "C2012X7R1E475K125AB": {
        "footprint": "Capacitor_SMD:C_0805_2012Metric",
        "body_max_mm": [2.20, 1.45, 1.45],
        "seat_mm": 0.10,
    },
}


def requirement(footprint, part):
    for mpn, row in PARTS.items():
        if not re.search(r"(?<![A-Z0-9])" + mpn + r"(?![A-Z0-9])", part.upper()):
            continue
        if footprint != row["footprint"]:
            raise ValueError((mpn, footprint, "Selected part/native footprint mismatch"))
        return dict(
            mpn=mpn,
            manufacturer="TDK",
            manufacturer_body_maximum_mm=row["body_max_mm"],
            project_seating_allocation_mm=row["seat_mm"],
            assembled_projection_requirement_mm=row["body_max_mm"][2] + row["seat_mm"],
            primary_source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=" + mpn,
            physical_verified=False,
            basis="Exact selected MPN body maximum plus explicit PROJECT seat; no generic-case height inheritance",
        )
    return None
