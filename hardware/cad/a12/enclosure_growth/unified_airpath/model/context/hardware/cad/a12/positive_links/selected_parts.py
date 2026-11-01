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
    "C3225X7R1E106K250AC": {
        "footprint": "Capacitor_SMD:C_1210_3225Metric",
        "body_max_mm": [3.60, 2.80, 2.80],
        "seat_mm": 0.10,
        "source_locations": "TDK exact-part Size table: L3.20+/-0.40,W/T2.50+/-0.30mm",
    },
    "C2012X7S2A105K125AE": {
        "footprint": "Capacitor_SMD:C_0805_2012Metric",
        "body_max_mm": [2.45, 1.50, 1.50],
        "seat_mm": 0.10,
        "source_locations": "TDK exact-part Size table: soft termination L2.00+0.45/-0.20,W/T1.25+0.25/-0.20mm",
    },
    "C0603C103J3GACTU": {
        "footprint": "Capacitor_SMD:C_0603_1608Metric",
        "body_max_mm": [1.75, 0.95, 0.90],
        "seat_mm": 0.10,
        "manufacturer": "KEMET",
        "primary_source": "https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
        "source_locations": "C1003_C0G2025-02-20: p3 0603L/W,p6 Table1A103/25V=CG,p10 Table2A CG0.80+/-0.10mm",
    },
}


def requirement(footprint, part):
    for mpn, row in PARTS.items():
        if not re.search(r"(?<![A-Z0-9])" + mpn + r"(?![A-Z0-9])", part.upper()):
            continue
        if footprint != row["footprint"]:
            raise ValueError((mpn, footprint, "Selected part/native footprint mismatch"))
        result = dict(
            mpn=mpn,
            manufacturer=row.get("manufacturer", "TDK"),
            manufacturer_body_maximum_mm=list(row["body_max_mm"]),
            project_seating_allocation_mm=row["seat_mm"],
            assembled_projection_requirement_mm=row["body_max_mm"][2] + row["seat_mm"],
            primary_source=row.get(
                "primary_source",
                "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=" + mpn,
            ),
            physical_verified=False,
            basis="Exact selected MPN body maximum plus explicit PROJECT seat; no generic-case height inheritance",
        )
        if "source_locations" in row:
            result["primary_source_locations"] = row["source_locations"]
        return result
    return None
