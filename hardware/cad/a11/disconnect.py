"""E25 actual PCB courtyard/lead reserves and capacitor body/vent cylinders."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
E25 = REPO / "hardware/electronics/rail_disconnect/placement"
DATUM = (8, 108.5, 4.6)


def packet():
    record = json.loads((E25 / "generated/verification.json").read_text())
    for name, h in record["source_sha256"].items():
        assert hashlib.sha256((E25 / name).read_bytes()).hexdigest() == h, (
            "Stale disconnect placement",
            name,
        )
    assert (
        record["physical_components"] == 164
        and record["native_nonrouting_drc_violations"] == record["schematic_parity_issues"] == 0
    )
    p = json.loads((E25 / "generated/placement.json").read_text())
    x0, y0, z0 = DATUM
    top = z0 + 1.6
    boxes = []
    cylinders = []
    vents = []
    for c in p["components"]:
        x, y, w, d = c["courtyard_relative_mm"]
        h = c["height_allocation_mm"]
        ref = c["reference"]
        z = z0 - h if c["side"] == "B" else top
        if ref in p["bulk_caps"]:
            cap = p["bulk_caps"][ref]
            diameter = cap["maximum_diameter_mm"]
            assert abs(w - diameter) < 1e-6 and abs(d - diameter) < 1e-6
            cylinders.append(["disconnect_" + ref, x0 + x + w / 2, y0 + y + d / 2, z, diameter, h])
            vents.append(
                ["disconnect_" + ref + "_vent", x0 + x + w / 2, y0 + y + d / 2, z + h, diameter, 2.0]
            )
        else:
            boxes.append(
                [
                    "disconnect_" + ref,
                    x0 + x,
                    y0 + y,
                    z,
                    w,
                    d,
                    h,
                    "Actual E25 courtyard; conditional assembled height/harness allowance",
                ]
            )
    for lead in p["leads"]:
        x, y = lead["center_relative_mm"]
        w = lead["reserve_width_mm"]
        h = lead["maximum_protrusion_mm"]
        boxes.append(
            [
                "disconnect_" + lead["reference"] + "_tail_" + lead["pin"],
                x0 + x - w / 2,
                y0 + y - w / 2,
                z0 - h,
                w,
                w,
                h,
                "Trimmed lead/solder allocation <=1.5mm",
            ]
        )
    mounts = []
    for ref, (x, y) in p["mounts_relative_mm"].items():
        mounts.append(["disconnect_carrier", x0 + x, y0 + y, z0, 2.2])
        boxes.append(
            [
                "disconnect_" + ref + "_head",
                x0 + x - 2.8,
                y0 + y - 2.8,
                top,
                5.6,
                5.6,
                2.31,
                "M2 head/washer allocation <=5.6mm OD, height<=2mm plus seat tolerance",
            ]
        )
    sources = [
        *(E25 / name for name in record["source_sha256"]),
        E25 / "rail_disconnect.kicad_pcb",
        E25 / "generated/verification.json",
        E25 / "generated/placement.json",
        ROOT / "disconnect.py",
    ]
    return dict(
        revision="E25/A11",
        datum_mm=DATUM,
        board=[
            "disconnect_carrier",
            *DATUM,
            156,
            45.25,
            1.6,
            "E25 placed-only rail-disconnect candidate; routing/qualification open",
        ],
        outline_mm=p["outline_relative_mm"],
        components=p["components"],
        reserves=boxes,
        cylinders=cylinders,
        vent_air=vents,
        mounts=mounts,
        pcb_sha256=p["pcb_sha256"],
        sources_sha256={
            str(f.resolve().relative_to(REPO)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sources
        },
        minimum_allocated_floor_gap_mm=round(min(b[3] - 2.8 for b in boxes), 6),
        vent_air_allocation_mm=2.0,
        pcb_routed=False,
        physical_fit_verified=False,
        height_limits_qualified=False,
        physical_protection_verified=False,
    )
