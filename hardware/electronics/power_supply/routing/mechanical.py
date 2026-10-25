"""Independent enlarged supply placement contract; E24 parent is immutable."""

import json
from pathlib import Path

from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import courtyard, transform

ROOT = Path(__file__).resolve().parents[1]


def mechanical(pcb, expected):
    tree = read_sexpr(pcb.read_text())
    assert not children(tree, "segment") and not children(tree, "via") and not children(tree, "zone"), (
        "E24 evidence is placed-only, not routing verification"
    )
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    copper = {
        str(l[1]) for l in first(tree, "layers")[1:] if isinstance(l, list) and str(l[1]).endswith(".Cu")
    }
    assert copper == {"F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"}
    lines = children(tree, "gr_line")
    assert len(lines) == 4
    assert {tuple(map(float, first(l, t)[1:3])) for l in lines for t in ("start", "end")} == {
        (100, 100),
        (190, 100),
        (190, 144),
        (100, 144),
    }
    parts = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
    actual, mounts, bodies, ep, side_counts = {}, {}, [], {}, dict(F=0, B=0)
    positions = {}
    for fp in children(tree, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        pads = children(fp, "pad")
        if ref.startswith("H"):
            assert (
                len(pads) == 1 and pads[0][2] == "np_thru_hole" and float(first(pads[0], "drill")[1]) == 2.4
            )
            x, y = transform(fp, first(pads[0], "at")[1:3])
            mounts[ref] = [round(x - 100, 6), round(y - 100, 6)]
            continue
        assert ref not in actual and fp[1] == parts[ref]["footprint"] and props["Value"] == parts[ref]["part"]
        actual[ref] = {}
        for pad in pads:
            number = str(pad[1])
            if not number:
                assert not children(pad, "net") and not any(
                    str(l).endswith(".Cu") for l in first(pad, "layers")[1:]
                )
                continue
            net = str(first(pad, "net")[-1]).lstrip("/")
            if number in actual[ref]:
                assert actual[ref][number] == net, (ref, "duplicate pad net mismatch")
            actual[ref][number] = net
            if ref in ("U1", "U13", "U7", "U8", "U9", "U10", "U11") and number == (
                "3" if ref == "U8" else "9" if ref in ("U7", "U9") else "11"
            ):
                ep.setdefault(ref, set()).add(net)
        side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
        positions[ref] = list(map(float, first(fp, "at")[1:3]))
        side_counts[side] += 1
        b = courtyard(fp, side + ".CrtYd")
        assert 100 <= b[0] < b[2] <= 190 and 100 <= b[1] < b[3] <= 144, (ref, b)
        bodies.append(
            dict(
                reference=ref,
                side=side,
                courtyard_relative_mm=[
                    round(b[0] - 100, 6),
                    round(b[1] - 100, 6),
                    round(b[2] - b[0], 6),
                    round(b[3] - b[1], 6),
                ],
            )
        )
    assert actual == expected
    assert mounts == {"H1": [4, 4], "H2": [74, 4], "H3": [4, 34], "H4": [74, 34]}
    assert ep == {
        "U1": {"AGND"},
        "U13": {"AGND"},
        "U7": {"P19_SRC"},
        "U8": {"P12_SRC"},
        "U9": {"V5_REG_SRC"},
        "U10": {"RAW_N22"},
        "U11": {"RAW_N17"},
    }
    thermal = {}
    for ref in ("U1", "U2", "U3", "U7", "U8", "U11", "U13"):
        x, y = positions[ref]
        x -= 100
        y -= 100
        w, h = (24, 14) if ref == "U8" else (8, 6) if ref == "U7" else (6, 6)
        if ref == "U8":
            x += 1
            y -= 1
        bounds = [x - w / 2, y - h / 2, x + w / 2, y + h / 2]
        assert 0 <= bounds[0] < bounds[2] <= 90 and 0 <= bounds[1] < bounds[3] <= 44
        for body in bodies:
            if body["side"] != "B" and not (
                body["reference"].startswith("J") or body["reference"] in ("C32", "C33")
            ):
                continue
            px, py, pw, ph = body["courtyard_relative_mm"]
            assert (
                min(px + pw, bounds[2]) - max(px, bounds[0]) <= 0
                or min(py + ph, bounds[3]) - max(py, bounds[1]) <= 0
            ), (ref, "bottom thermal region occupied", body["reference"])
        thermal[ref] = bounds
    return dict(
        revision="positive-linears-in-progress",
        pcb_sha256=sha(pcb),
        board_size_mm=[90, 44, 1.6],
        copper_layers=6,
        circuit_components=157,
        mounts_relative_mm=mounts,
        mount_hole_mm=2.4,
        bodies=bodies,
        component_sides=side_counts,
        exposed_pad_nets={ref: next(iter(n)) for ref, n in ep.items()},
        bottom_thermal_region_allocations_mm=thermal,
        pcb_routed=False,
        housing_datum_proposal_mm=[201, 105, 6.5],
        housing_fit_verified=False,
        current_carrying_or_thermal_verified=False,
        switching_loop_or_emi_verified=False,
        remaining=[
            "all copper routing and actual converter hot-loop geometry",
            "regulator OUT/IN thermal copper, vias and loss/temperature qualification",
            "header/harness and THT tail bounds, actual housing integration",
            "startup, bulk-capacitor loop, fault/SOA, noise and physical assembly checks",
        ],
    )
