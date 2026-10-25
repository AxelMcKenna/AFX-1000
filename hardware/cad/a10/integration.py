"""Build housing reserves from the actual supply PCB, with explicit height budgets.

Courtyards and lead locations come from KiCad. Heights are assembly allocations,
not measured or supplier-qualified dimensions. Electrical qualification is unfinished.
"""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SUPPLY = REPO / "hardware/electronics/power_supply"
PCB = SUPPLY / "routing/power_supply.kicad_pcb"
DATUM = (201.0, 105.0, 6.5)

# Maximum permitted assembled body height above its PCB face, before the
# additional seat/board tolerances below. Unselected parts must meet these
# limits or trigger another integration check; these are not catalogue facts.
HEIGHT_LIMITS = {
    "Capacitor_SMD:C_0805_2012Metric": 2.0,
    "Capacitor_SMD:C_1210_3225Metric": 3.2,
    "Capacitor_THT:C_Rect_L7.2mm_W5.0mm_P5.00mm": 10.5,
    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical": 13.0,
    "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical": 13.0,
    "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical": 13.0,
    "Diode_SMD:D_SMA": 2.5,
    "Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm": 1.2,
    "Package_SO:MSOP-8-1EP_3x3mm_P0.65mm_EP1.68x1.88mm": 1.2,
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm": 2.0,
    "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm": 2.0,
    "Package_TO_SOT_SMD:SOT-583-8": 1.2,
    "Package_TO_SOT_SMD:TO-263-5_TabPin3": 4.8,
    "RMX_Power:SRP1050WA": 5.5,
    "RMX_Power:SRP7050WA": 5.5,
    "Resistor_SMD:R_0805_2012Metric": 0.8,
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assignments(path):
    result = {}
    for line in path.read_text().splitlines():
        if " = " in line and line.endswith(";") and not line.startswith("//"):
            key, value = line.removesuffix(";").split(" = ", 1)
            result[key] = json.loads(value)
    return result


def overlap(a, b):
    """Positive intersection of two [id,x,y,z,w,d,h,...] boxes only."""
    return all(min(a[i] + a[i + 3], b[i] + b[i + 3]) - max(a[i], b[i]) > 1e-6 for i in (1, 2, 3))


def electronics_clearance(actual, obstacles, minimum=0.25):
    """Conservative axis-aligned clearance, independently of native CAD solids."""
    closest = None
    for a in [actual["board"], *actual["reserves"]]:
        for b in obstacles:
            gap = max(max(b[i] - a[i] - a[i + 3], a[i] - b[i] - b[i + 3]) for i in (1, 2, 3))
            if closest is None or gap < closest[0]:
                closest = (gap, a[0], b[0])
    assert closest is not None and closest[0] >= minimum, (
        "Insufficient supply-to-electronics clearance",
        closest,
        minimum,
    )
    return dict(minimum_axis_gap_mm=round(closest[0], 6), pair=list(closest[1:]), required_mm=minimum)


def packet(pcb=PCB, datum=DATUM):
    tree = read_sexpr(pcb.read_text())
    x0, y0, z0 = datum
    thickness = float(first(first(tree, "general"), "thickness")[1])
    assert thickness == 1.6
    outline = {
        tuple(map(float, first(line, end)[1:3]))
        for line in children(tree, "gr_line")
        if first(line, "layer")[1] == "Edge.Cuts"
        for end in ("start", "end")
    }
    assert outline == {(100, 100), (190, 100), (190, 144), (100, 144)}, (
        "Supply outline changed; update the housing interface"
    )
    parts = {p["ref"]: p for p in json.loads((SUPPLY / "components.json").read_text())}
    reserves, mounts, records, positions = [], [], [], {}
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        positions[ref] = [float(v) for v in first(fp, "at")[1:3]]
        pads = children(fp, "pad")
        if ref.startswith("H"):
            assert len(pads) == 1 and pads[0][2] == "np_thru_hole"
            assert float(first(pads[0], "drill")[1]) == 2.4
            x, y = transform(fp, first(pads[0], "at")[1:3])
            mounts.append(["power_carrier", x0 + x - 100, y0 + y - 100, z0, 2.2])
            reserves.append(
                [
                    f"power_{ref}_head",
                    x0 + x - 102.8,
                    y0 + y - 102.8,
                    z0 + thickness,
                    5.6,
                    5.6,
                    2.31,
                    "M2 head/washer allocation: OD<=5.6, assembled height<=2 plus 0.31 seat allowance; hardware unselected",
                ]
            )
            continue
        footprint = str(fp[1])
        assert ref in parts and footprint == parts[ref]["footprint"]
        side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
        x, y, xmax, ymax = courtyard(fp, side + ".CrtYd")
        assert 100 <= x < xmax <= 190 and 100 <= y < ymax <= 144
        extra = 0.5 if ref.startswith("J") else 0
        height = HEIGHT_LIMITS[footprint] + (0.15 if side == "B" else 0.31)
        body = [
            f"power_{ref}",
            x0 + x - 100 - extra,
            y0 + y - 100 - extra,
            z0 - height if side == "B" else z0 + thickness,
            xmax - x + 2 * extra,
            ymax - y + 2 * extra,
            height,
            "Actual KiCad courtyard; conditional assembled height and header/harness allowance; supplier/physical qualification open",
        ]
        reserves.append(body)
        records.append(
            dict(
                reference=ref,
                footprint=footprint,
                side=side,
                box_mm=body[1:7],
                height_limit_mm=HEIGHT_LIMITS[footprint],
            )
        )
        for pad in pads:
            if pad[2] != "thru_hole":
                continue
            assert side == "F", "Bottom through-hole parts need a separate lead/body allocation"
            px, py = transform(fp, first(pad, "at")[1:3])
            reserves.append(
                [
                    f"power_{ref}_lead_{pad[1]}",
                    x0 + px - 101,
                    y0 + py - 101,
                    z0 - 1.65,
                    2,
                    2,
                    1.65,
                    "Trimmed THT lead/solder must project <=1.5 mm below the PCB, plus 0.15 allowance",
                ]
            )
    assert {r["reference"] for r in records} == set(parts) and len(records) == 157
    assert sorted((round(m[1] - x0, 6), round(m[2] - y0, 6)) for m in mounts) == [
        (4, 4),
        (4, 34),
        (74, 4),
        (74, 34),
    ]
    # This excludes tall hardware beneath the existing thermal-copper reserves.
    # Air space is not a thermal or heatsink qualification.
    thermal = []
    for ref in ("U1", "U2", "U3", "U7", "U8", "U11", "U13"):
        x, y = positions[ref]
        w, d = (24, 14) if ref == "U8" else (8, 6) if ref == "U7" else (6, 6)
        if ref == "U8":
            x, y = x + 1, y - 1
        thermal.append(
            [
                f"power_{ref}_thermal_air",
                x0 + x - 100 - w / 2,
                y0 + y - 100 - d / 2,
                z0 - 1,
                w,
                d,
                1,
                "1 mm unobstructed air allocation beneath existing thermal copper region; cooling unqualified",
            ]
        )
    return dict(
        board=[
            "power_carrier",
            x0,
            y0,
            z0,
            90,
            44,
            thickness,
            "actual 157-part supply PCB; routing closed, electrical qualification open",
        ],
        mounts=mounts,
        reserves=reserves,
        components=records,
        thermal=thermal,
        pcb_sha256=digest(pcb),
    )


def write_packet():
    data = assignments(ROOT / "reference-components.scad")
    actual = packet()
    data["boards"] = [actual["board"] if b[0] == "power_carrier" else b for b in data["boards"]]
    data["envelopes"] = [e for e in data["envelopes"] if e[0] != "power_components"] + actual["reserves"]
    data["board_mounts"] = [m for m in data["board_mounts"] if m[0] != "power_carrier"] + actual["mounts"]
    data["power_thermal_air"] = actual["thermal"]
    obstacles = (
        [b for b in data["boards"] if b[0] != "power_carrier"]
        + [e for e in data["envelopes"] if not e[0].startswith("power_")]
        + data["port_envelopes"]
    )
    collisions = [
        (a[0], b[0])
        for a in [actual["board"], *actual["reserves"], *actual["thermal"]]
        for b in obstacles
        if overlap(a, b)
    ]
    assert not collisions, ("Power assembly hits another electronics reserve", collisions)
    clearance = electronics_clearance(actual, obstacles)
    assert all(e[3] >= 2.8 for e in actual["reserves"]), "Power component/lead reaches the chassis floor"
    assert all(not overlap(t, e) for t in actual["thermal"] for e in actual["reserves"]), (
        "Power underside thermal allocation obstructed"
    )
    out = ROOT / "generated"
    out.mkdir(exist_ok=True)
    (out / "components.scad").write_text(
        "// Generated A10 actual-supply integration; heights remain conditional allocations.\n"
        + "\n".join(k + " = " + json.dumps(v) + ";" for k, v in data.items())
        + "\n"
    )
    report = dict(
        revision="A10",
        pcb_sha256=actual["pcb_sha256"],
        sources_sha256={
            str(p.relative_to(REPO)): digest(p)
            for p in [
                PCB,
                SUPPLY / "components.json",
                ROOT / "integration.py",
                ROOT / "reference-components.scad",
            ]
        },
        board=actual["board"],
        mounts=actual["mounts"],
        components=actual["components"],
        leads_and_heads=[e for e in actual["reserves"] if "_lead_" in e[0] or e[0].endswith("_head")],
        thermal_air=actual["thermal"],
        minimum_allocated_floor_gap_mm=round(min(e[3] - 2.8 for e in actual["reserves"]), 6),
        electronics_box_collisions=collisions,
        electronics_clearance=clearance,
        pcb_electrical_verified=False,
        physical_fit_verified=False,
        height_limits_qualified=False,
    )
    (out / "power-integration.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    report = write_packet()
    print(
        f"A10: {len(report['components'])} actual components; allocated floor gap {report['minimum_allocated_floor_gap_mm']} mm; no electronics-box collisions"
    )
