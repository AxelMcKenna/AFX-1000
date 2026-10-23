#!/usr/bin/env python3
"""Check partial supply copper against native DRC and independent path limits."""

import argparse
import datetime
import heapq
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import transform
from ..check_placement import mechanical
from ..verify import contract

ROOT = Path(__file__).resolve().parent
SUPPLY = ROOT.parent
OUT = ROOT / "generated"


def local_paths(tree):
    """Measure actual connected segment/via graphs, independently of route instructions."""
    footprints = {
        next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
        for fp in children(tree, "footprint")
    }
    net_names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}

    def pad(ref, number, net, allowed):
        fp = footprints[ref]
        layer = str(first(fp, "layer")[1])
        assert layer in allowed
        p = next(p for p in children(fp, "pad") if str(p[1]) == str(number))
        assert str(first(p, "net")[-1]).lstrip("/") == net
        return (*[round(v, 6) for v in transform(fp, first(p, "at")[1:3])], layer)

    front = ("F.Cu",)
    results = {}
    for name, net, start, end, limit, allowed in [
        ("input_bypass_vin", "VIN_PROTECTED", ("U2", 3), ("C22", 1), 4, front),
        ("input_bypass_ground", "AGND", ("U2", 4), ("C22", 2), 4, front),
        ("bootstrap_drive", "DIG_BST", ("U2", 6), ("C16", 1), 3, front),
        ("bootstrap_return", "DIG_SW", ("U2", 5), ("C16", 2), 7, front),
        ("switch_to_inductor", "DIG_SW", ("U2", 5), ("L4", 1), 9, front),
        ("feedback_to_pin", "DIG_FB", ("R51", 2), ("U2", 8), 6, front),
        ("feedback_lower_arm", "DIG_FB", ("R11", 1), ("R51", 2), 8, front),
        ("feedback_trim", "DIG_FB_TRIM", ("R10", 2), ("R51", 1), 3, front),
        ("feedback_ground", "AGND", ("R11", 2), ("U2", 4), 28, ("F.Cu", "In4.Cu")),
        ("output_kelvin", "5V_DIG_SRC", ("J3", 1), ("R10", 1), 38, ("F.Cu", "In2.Cu")),
        ("bulk_input_local", "VIN_PROTECTED", ("C20", 1), ("U2", 3), 8, front),
        ("bulk_input_pair", "VIN_PROTECTED", ("C21", 1), ("C20", 1), 6, front),
        ("input_feed", "VIN_PROTECTED", ("J1", 1), ("C21", 1), 15, ("F.Cu", "In4.Cu")),
        ("output_cap_1", "5V_DIG_SRC", ("L4", 2), ("C18", 1), 13, front),
        ("output_cap_2", "5V_DIG_SRC", ("L4", 2), ("C19", 1), 6, front),
        ("output_header", "5V_DIG_SRC", ("C19", 1), ("J3", 1), 12, front),
        ("ground_input_pair", "AGND", ("C21", 2), ("C20", 2), 9, front),
        ("ground_input_local", "AGND", ("C20", 2), ("U2", 4), 22, ("F.Cu", "In1.Cu")),
        ("ground_input_header", "AGND", ("J1", 2), ("C20", 2), 6, front),
        ("ground_output_pair", "AGND", ("C18", 2), ("C19", 2), 30, ("F.Cu", "In1.Cu")),
        ("ground_output_header", "AGND", ("C19", 2), ("J3", 2), 22, ("F.Cu", "In1.Cu")),
        ("soft_start", "DIG_SS", ("U2", 7), ("C17", 1), 9, ("F.Cu", "In3.Cu")),
        ("soft_start_ground", "AGND", ("C17", 2), ("U2", 4), 18, ("F.Cu", "In1.Cu")),
        ("enable_pin", "SUPPLY_ENABLE", ("R8", 2), ("U2", 2), 11, ("F.Cu", "B.Cu", "In3.Cu")),
        ("enable_pulldown", "SUPPLY_ENABLE", ("R8", 2), ("R9", 1), 7, ("B.Cu",)),
        ("power_ready", "POWER_READY", ("J5", 2), ("R8", 1), 38, ("F.Cu", "B.Cu", "In3.Cu")),
        ("enable_ground", "AGND", ("R9", 2), ("C22", 2), 8, ("F.Cu", "B.Cu", "In1.Cu")),
        ("guard_ground", "AGND", ("J5", 1), ("R9", 2), 28, ("F.Cu", "B.Cu", "In1.Cu")),
        ("pre_input_bypass", "VIN_PROTECTED", ("U3", 3), ("C29", 1), 5, front),
        ("pre_bypass_ground", "AGND", ("U3", 4), ("C29", 2), 3, front),
        ("pre_bootstrap", "PRE_BST", ("U3", 6), ("C23", 1), 6, front),
        ("pre_switch", "PRE_SW", ("U3", 5), ("L5", 1), 9, front),
        ("pre_bulk_input", "VIN_PROTECTED", ("C27", 1), ("C28", 1), 5, front),
        ("pre_input_feed", "VIN_PROTECTED", ("J1", 1), ("C27", 1), 55, ("F.Cu", "In4.Cu")),
        ("pre_input_to_bypass", "VIN_PROTECTED", ("C27", 1), ("C29", 1), 24, ("F.Cu", "In4.Cu")),
        ("pre_output_cap_1", "V5_PRE", ("L5", 2), ("C25", 1), 20, front),
        ("pre_output_cap_2", "V5_PRE", ("L5", 2), ("C26", 1), 15, front),
        ("pre_linear_feed", "V5_PRE", ("C26", 1), ("U9", 7), 20, ("F.Cu", "B.Cu", "In3.Cu")),
        ("pre_test_header", "V5_PRE", ("C26", 1), ("J4", 6), 45, ("F.Cu", "In3.Cu")),
        ("pre_output_sense", "V5_PRE", ("U9", 7), ("R14", 1), 12, ("F.Cu", "B.Cu", "In2.Cu")),
        ("pre_feedback_mid", "PRE_RMID", ("R14", 2), ("R15", 1), 4, front),
        ("pre_feedback_upper", "PRE_FB", ("R15", 2), ("U3", 8), 35, ("F.Cu", "In2.Cu")),
        ("pre_feedback_lower", "PRE_FB", ("R16", 1), ("U3", 8), 20, ("F.Cu", "In2.Cu")),
        ("pre_quiet_ground", "AGND", ("R16", 2), ("U3", 4), 23, ("F.Cu", "In4.Cu")),
        ("pre_bulk_ground", "AGND", ("C27", 2), ("C29", 2), 20, ("F.Cu", "In1.Cu")),
        ("pre_output_ground", "AGND", ("C25", 2), ("C26", 2), 15, ("F.Cu", "In1.Cu")),
        ("pre_soft_start", "PRE_SS", ("U3", 7), ("C24", 1), 13, ("F.Cu", "In3.Cu")),
        ("pre_soft_ground", "AGND", ("C24", 2), ("J3", 2), 13, ("F.Cu", "In1.Cu")),
        ("pre_enable_pin", "SUPPLY_ENABLE", ("U2", 2), ("U3", 2), 22, ("F.Cu", "In3.Cu")),
        (
            "pre_enable_network",
            "SUPPLY_ENABLE",
            ("R12", 2),
            ("U3", 2),
            20,
            ("F.Cu", "B.Cu", "In2.Cu", "In3.Cu"),
        ),
        ("pre_enable_pulldown", "SUPPLY_ENABLE", ("R12", 2), ("R13", 1), 4, ("B.Cu",)),
        ("pre_ready", "POWER_READY", ("J5", 2), ("R12", 1), 34, ("F.Cu", "B.Cu", "In2.Cu", "In3.Cu")),
        ("pre_enable_ground", "AGND", ("R13", 2), ("J3", 2), 6, ("F.Cu", "B.Cu", "In1.Cu")),
        ("raw_input_feed", "VIN_PROTECTED", ("J1", 1), ("C70", 1), 55, ("F.Cu", "In4.Cu")),
        ("raw_boost_input", "VIN_PROTECTED", ("C70", 1), ("L6", 1), 6, front),
        ("raw_cuk_input", "VIN_PROTECTED", ("C70", 1), ("L7", 1), 16, front),
        ("raw_ic_input_feed", "VIN_PROTECTED", ("C70", 1), ("C71", 1), 45, ("F.Cu", "In4.Cu")),
        ("raw_ic_bypass", "VIN_PROTECTED", ("C71", 1), ("U13", 8), 4, front),
        ("raw_boost_switch", "LO_P_SW", ("U13", 10), ("L6", 2), 14, front),
        ("raw_boost_diode", "LO_P_SW", ("U13", 10), ("D3", 2), 6, front),
        ("raw_positive_bulk_1", "RAW_P17", ("D3", 1), ("C64", 1), 20, front),
        ("raw_positive_bulk_2", "RAW_P17", ("D3", 1), ("C65", 1), 16, front),
        ("raw_positive_bypass", "RAW_P17", ("D3", 1), ("C66", 1), 12, front),
        ("raw_cuk_switch", "LO_N_SW", ("U13", 6), ("L7", 2), 26, front),
        ("raw_cuk_transfer", "LO_N_SW", ("U13", 6), ("C63", 1), 9, front),
        ("raw_cuk_diode", "LO_CUK_NODE", ("D4", 2), ("C63", 2), 6, front),
        ("raw_cuk_choke", "LO_CUK_NODE", ("C63", 2), ("L8", 1), 22, front),
        ("raw_negative_bulk_1", "RAW_N17", ("L8", 2), ("C67", 1), 35, ("F.Cu", "B.Cu", "In3.Cu")),
        ("raw_negative_bulk_2", "RAW_N17", ("L8", 2), ("C68", 1), 25, ("F.Cu", "B.Cu", "In3.Cu")),
        ("raw_negative_bypass", "RAW_N17", ("L8", 2), ("C69", 1), 20, ("F.Cu", "B.Cu", "In3.Cu")),
        ("raw_negative_linear_input_cap", "RAW_N17", ("L8", 2), ("C56", 1), 12, ("F.Cu", "B.Cu")),
        ("raw_bulk_ground_1", "AGND", ("C64", 2), ("U13", 11), 40, ("F.Cu", "In1.Cu")),
        ("raw_bulk_ground_2", "AGND", ("C65", 2), ("U13", 11), 30, ("F.Cu", "In1.Cu")),
        ("raw_bypass_ground", "AGND", ("C66", 2), ("U13", 11), 24, ("F.Cu", "In1.Cu")),
        ("raw_input_ground", "AGND", ("C70", 2), ("U13", 11), 40, ("F.Cu", "In1.Cu")),
        ("raw_ic_ground", "AGND", ("C71", 2), ("U13", 11), 20, ("F.Cu", "In1.Cu")),
        ("raw_diode_ground", "AGND", ("D4", 1), ("U13", 11), 20, ("F.Cu", "In1.Cu")),
        ("raw_negative_ground_1", "AGND", ("C67", 2), ("C20", 2), 10, ("F.Cu", "B.Cu", "In1.Cu")),
        ("raw_negative_ground_2", "AGND", ("C68", 2), ("U13", 11), 15, ("F.Cu", "B.Cu", "In1.Cu")),
        ("raw_negative_ground_3", "AGND", ("C69", 2), ("C22", 2), 10, ("F.Cu", "B.Cu", "In1.Cu")),
        ("raw_reference_pins", "LO_REF_1V", ("U13", 2), ("U13", 3), 3, front),
        ("raw_reference_bypass", "LO_REF_1V", ("U13", 2), ("C72", 1), 15, ("F.Cu", "B.Cu")),
        ("raw_reference_divider", "LO_REF_1V", ("C72", 1), ("R46", 1), 12, ("F.Cu", "B.Cu")),
        ("raw_feedback_reference", "AGND", ("U13", 5), ("U13", 11), 4, front),
        ("raw_quiet_divider_ground", "AGND", ("R45", 2), ("U13", 11), 18, ("F.Cu", "In3.Cu")),
        ("raw_quiet_bypass_ground", "AGND", ("C72", 2), ("U13", 11), 25, ("F.Cu", "B.Cu", "In3.Cu")),
        ("raw_positive_sense", "RAW_P17", ("C66", 1), ("R44", 1), 30, ("F.Cu", "In2.Cu")),
        ("raw_positive_feedback", "LO_P_FB", ("R44", 2), ("U13", 1), 25, ("F.Cu", "In2.Cu")),
        ("raw_positive_lower_arm", "LO_P_FB", ("R44", 2), ("R45", 1), 4, front),
        ("raw_positive_feedforward_upper", "RAW_P17", ("R44", 1), ("C73", 1), 30, ("F.Cu", "B.Cu")),
        ("raw_positive_feedforward_lower", "LO_P_FB", ("R44", 2), ("C73", 2), 30, ("F.Cu", "B.Cu")),
        ("raw_negative_feedback", "LO_N_FB", ("R47", 1), ("U13", 4), 10, ("F.Cu", "In2.Cu")),
        ("raw_negative_reference_arm", "LO_N_FB", ("R46", 2), ("R47", 1), 4, front),
        ("raw_negative_mid_arm", "LO_N_RMID", ("R47", 2), ("R48", 1), 22, ("F.Cu", "B.Cu", "In2.Cu")),
        ("raw_negative_sense", "RAW_N17", ("C69", 1), ("R48", 2), 20, ("B.Cu",)),
        ("raw_negative_feedforward_upper", "RAW_N17", ("R48", 2), ("C75", 1), 55, ("B.Cu",)),
        ("raw_negative_feedforward_lower", "LO_N_FB", ("R47", 1), ("C75", 2), 45, ("F.Cu", "B.Cu")),
        ("raw_positive_enable_feed", "5V_DIG_SRC", ("C18", 1), ("R49", 1), 45, ("F.Cu", "B.Cu", "In4.Cu")),
        ("raw_negative_enable_feed", "5V_DIG_SRC", ("R49", 1), ("R50", 1), 10, ("B.Cu",)),
        ("raw_positive_enable", "LO_P_SS", ("R49", 2), ("U13", 9), 20, ("F.Cu", "B.Cu")),
        ("raw_positive_start_cap", "LO_P_SS", ("C74", 1), ("U13", 9), 30, ("F.Cu", "B.Cu")),
        ("raw_negative_enable", "LO_N_SS", ("R50", 2), ("U13", 7), 28, ("F.Cu", "B.Cu")),
        ("raw_negative_start_cap", "LO_N_SS", ("C76", 1), ("U13", 7), 40, ("F.Cu", "B.Cu")),
        ("raw_positive_start_ground", "AGND", ("C74", 2), ("U13", 11), 22, ("F.Cu", "B.Cu", "In1.Cu")),
        ("raw_negative_start_ground", "AGND", ("C76", 2), ("C20", 2), 12, ("F.Cu", "B.Cu", "In1.Cu")),
    ]:
        minimum_width = {
            "raw_input_feed": 0.8,
            "raw_boost_input": 0.8,
            "raw_cuk_input": 0.8,
            "raw_ic_input_feed": 0.35,
            "raw_ic_bypass": 0.35,
            "raw_boost_switch": 0.3,
            "raw_boost_diode": 0.3,
            "raw_positive_bulk_1": 0.8,
            "raw_positive_bulk_2": 0.8,
            "raw_positive_bypass": 0.8,
            "raw_cuk_switch": 0.3,
            "raw_cuk_transfer": 0.3,
            "raw_cuk_diode": 0.5,
            "raw_cuk_choke": 0.5,
            "raw_negative_bulk_1": 0.5,
            "raw_negative_bulk_2": 0.5,
            "raw_negative_bypass": 0.5,
            "raw_negative_linear_input_cap": 0.5,
            "raw_bulk_ground_1": 0.5,
            "raw_bulk_ground_2": 0.5,
            "raw_bypass_ground": 0.5,
            "raw_input_ground": 0.5,
            "raw_ic_ground": 0.35,
            "raw_diode_ground": 0.5,
            "raw_negative_ground_1": 0.5,
            "raw_negative_ground_2": 0.5,
            "raw_negative_ground_3": 0.26,
            "pre_test_header": 0.5,
            "pre_bulk_input": 0.8,
            "pre_input_feed": 0.8,
            "pre_input_to_bypass": 0.5,
            "pre_output_cap_1": 0.8,
            "pre_output_cap_2": 0.8,
            "pre_linear_feed": 0.35,
            "pre_bulk_ground": 0.35,
            "pre_output_ground": 0.8,
            "bulk_input_pair": 0.8,
            "input_feed": 0.8,
            "output_cap_1": 1.2,
            "output_cap_2": 1.2,
            "output_header": 1.2,
            "ground_input_pair": 0.8,
            "ground_input_header": 0.8,
            "ground_output_pair": 0.8,
            "ground_output_header": 0.8,
        }.get(name, 0.26)
        graph = {}

        def edge(a, b, distance):
            graph.setdefault(a, []).append((b, distance))
            graph.setdefault(b, []).append((a, distance))

        for s in children(tree, "segment"):
            if float(first(s, "width")[1]) < minimum_width - 1e-9:
                continue
            layer = str(first(s, "layer")[1])
            if layer not in allowed or net_names[str(first(s, "net")[1])] != net:
                continue
            a, b = [tuple(round(float(v), 6) for v in first(s, tag)[1:3]) for tag in ("start", "end")]
            edge((*a, layer), (*b, layer), math.dist(a, b))
        for via in children(tree, "via"):
            if net_names[str(first(via, "net")[1])] != net:
                continue
            xy = tuple(round(float(v), 6) for v in first(via, "at")[1:3])
            assert list(first(via, "layers")[1:]) == ["F.Cu", "B.Cu"]
            for a in allowed:
                for b in allowed:
                    if a != b:
                        edge((*xy, a), (*xy, b), 0)
        for fp in footprints.values():
            for p in children(fp, "pad"):
                if (
                    p[2] != "thru_hole"
                    or not children(p, "net")
                    or str(first(p, "net")[-1]).lstrip("/") != net
                ):
                    continue
                xy = tuple(round(v, 6) for v in transform(fp, first(p, "at")[1:3]))
                for a in allowed:
                    for b in allowed:
                        if a != b:
                            edge((*xy, a), (*xy, b), 0)
        begin, target = pad(*start, net, allowed), pad(*end, net, allowed)
        costs, queue = {begin: 0}, [(0, begin)]
        while queue:
            distance, node = heapq.heappop(queue)
            if distance > costs[node]:
                continue
            if node == target:
                break
            for neighbor, delta in graph.get(node, []):
                cost = distance + delta
                if cost < costs.get(neighbor, math.inf):
                    costs[neighbor] = cost
                    heapq.heappush(queue, (cost, neighbor))
        length = costs.get(target, math.inf)
        assert 0 < length < limit, (name, "missing or excessive local path", length, limit)
        results[name] = dict(
            net=net,
            from_pad=list(start),
            to_pad=list(end),
            length_mm=length,
            limit_mm=limit,
            allowed_layers=list(allowed),
            minimum_track_width_mm=minimum_width,
        )
    return results


def front_buck(tree):
    expected = {
        "U2",
        "L4",
        "C16",
        "C17",
        "C18",
        "C19",
        "C20",
        "C21",
        "C22",
        "R10",
        "R11",
        "R51",
        "U3",
        "L5",
        "C23",
        "C24",
        "C25",
        "C26",
        "C27",
        "C28",
        "C29",
        "R14",
        "R15",
        "R16",
    }
    found = set()
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in expected:
            assert first(fp, "layer")[1] == "F.Cu", (ref, "buck component moved off front")
            if ref in ("U2", "U3"):
                rt = next(p for p in children(fp, "pad") if str(p[1]) == "1")
                assert first(rt, "net")[-1] == f"unconnected-({ref}-RT-Pad1)", (
                    "floating RT pin lost reserved net name"
                )
            found.add(ref)
    assert found == expected
    return len(found)


def via_lands(tree):
    """Conventional drills must clear every solder land, including their own net."""
    lands = []
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        pos = first(fp, "at")
        angle = float(pos[3]) if len(pos) > 3 else 0
        for pad in children(fp, "pad"):
            x, y = transform(fp, first(pad, "at")[1:3])
            at = first(pad, "at")
            rotation = angle + (float(at[3]) if len(at) > 3 else 0)
            assert math.isclose(rotation / 90, round(rotation / 90), abs_tol=1e-6)
            w, h = map(float, first(pad, "size")[1:3])
            if abs(math.sin(math.radians(rotation))) > 0.5:
                w, h = h, w
            lands.append((ref, x - w / 2, y - h / 2, x + w / 2, y + h / 2))
    minimum = math.inf
    for via in children(tree, "via"):
        x, y = map(float, first(via, "at")[1:3])
        radius = float(first(via, "drill")[1]) / 2
        for ref, x0, y0, x1, y1 in lands:
            clearance = math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) - radius
            assert clearance >= 0.25 - 1e-6, (
                "conventional via drill too close to solder land",
                ref,
                x,
                y,
                clearance,
            )
            minimum = min(minimum, clearance)
    return minimum


def front_raw(tree):
    expected = {
        "U13",
        "L6",
        "L7",
        "L8",
        "D3",
        "D4",
        "C63",
        "C64",
        "C65",
        "C66",
        "C70",
        "C71",
        "R44",
        "R45",
        "R46",
        "R47",
    }
    found = set()
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        if ref in expected:
            assert first(fp, "layer")[1] == "F.Cu", (ref, "raw supply component moved off front")
            found.add(ref)
    assert found == expected
    return len(found)


def ground_layout(tree):
    zones = children(tree, "zone")
    keepouts = [z for z in zones if children(z, "keepout") and children(z, "layers")]
    quiet = [z for z in zones if children(z, "keepout") and children(z, "layer")]
    planes = [z for z in zones if not children(z, "keepout")]
    assert len(keepouts) == 4 and len(planes) == 1 and len(quiet) == 7
    centers = {(104, 104), (174, 104), (104, 134), (174, 134)}
    seen = set()
    for zone in keepouts:
        assert set(first(zone, "layers")[1:]) == {"F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"}
        assert all(
            first(first(zone, "keepout"), k)[1] == "not_allowed" for k in ("tracks", "vias", "copperpour")
        )
        points = [tuple(map(float, p[1:3])) for p in children(first(first(zone, "polygon"), "pts"), "xy")]
        center = min(
            centers,
            key=lambda c: math.dist(
                c, (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
            ),
        )
        assert center not in seen
        seen.add(center)
        for a, b in zip(points, points[1:] + points[:1]):
            distance = abs(
                (b[0] - a[0]) * (a[1] - center[1]) - (a[0] - center[0]) * (b[1] - a[1])
            ) / math.dist(a, b)
            assert distance >= 3.7 - 1e-5, ("mount copper clearance reduced", center, distance)
    assert seen == centers
    quiet_layers = {
        (165, 104.75): {"F.Cu", "In4.Cu"},
        (158, 115.2): {"F.Cu", "In4.Cu"},
        (163.4, 118.2): {"F.Cu", "In4.Cu"},
        (174.3, 121.6125): {"F.Cu", "In4.Cu"},
        (135.4125, 110.8): {"F.Cu", "In3.Cu"},
        (144.6, 109.9): {"F.Cu", "In3.Cu"},
        (136.35, 102.9): {"B.Cu", "In3.Cu"},
    }
    quiet_centers = set(quiet_layers)
    seen_quiet = set()
    for zone in quiet:
        assert first(zone, "layer")[1] == "In1.Cu"
        rules = first(zone, "keepout")
        assert first(rules, "copperpour")[1] == "not_allowed" and all(
            first(rules, k)[1] == "allowed" for k in ("tracks", "vias")
        )
        points = [tuple(map(float, p[1:3])) for p in children(first(first(zone, "polygon"), "pts"), "xy")]
        center = min(
            quiet_centers,
            key=lambda c: math.dist(
                c, (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
            ),
        )
        assert center not in seen_quiet
        seen_quiet.add(center)
        for a, b in zip(points, points[1:] + points[:1]):
            distance = abs(
                (b[0] - a[0]) * (a[1] - center[1]) - (a[0] - center[0]) * (b[1] - a[1])
            ) / math.dist(a, b)
            assert distance >= 0.75 - 1e-5, ("quiet return plane isolation reduced", center, distance)
        for segment in children(tree, "segment"):
            layer = first(segment, "layer")[1]
            if layer in quiet_layers[center]:
                continue
            a, b = [tuple(map(float, first(segment, tag)[1:3])) for tag in ("start", "end")]
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = max(0, min(1, ((center[0] - a[0]) * dx + (center[1] - a[1]) * dy) / (dx * dx + dy * dy)))
            distance = math.dist(center, (a[0] + t * dx, a[1] + t * dy))
            assert distance >= 0.3 + float(first(segment, "width")[1]) / 2 + 0.15, (
                "quiet via shunted by In1 track"
                if layer == "In1.Cu"
                else "quiet via shunted on reserved layer"
            )
    assert seen_quiet == quiet_centers
    plane = planes[0]
    assert first(plane, "layer")[1] == "In1.Cu" and first(plane, "net_name")[1] == "/AGND"
    assert first(plane, "connect_pads")[1] == "yes", "Ground plane needs solid pad/via connections"
    return dict(
        ground_layer="In1.Cu",
        mounting_copper_clearance_mm=3.7,
        mount_keepouts=4,
        solid_pad_connections=True,
        quiet_return_plane_antipads=7,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True, type=Path)
    args = parser.parse_args()
    cli = args.kicad_cli.resolve()
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    pcb = ROOT / "power_supply.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    paths = local_paths(tree)
    assert len(children(tree, "via")) == 87
    front_count = front_buck(tree)
    raw_front_count = front_raw(tree)
    drill_clearance = via_lands(tree)
    ground = ground_layout(tree)
    inputs = json.loads((OUT / "routing-inputs.json").read_text())
    assert inputs["source_placement_sha256"] == sha(SUPPLY / "power_supply.kicad_pcb")
    assert inputs["source_poses_sha256"] == sha(SUPPLY / "generated/placement-inputs.json")
    with tempfile.TemporaryDirectory(prefix="rmx-power-local-") as folder:
        temp = Path(folder)
        font = temp / "fonts.conf"
        font.write_text(
            f"<fontconfig><dir>/System/Library/Fonts</dir><cachedir>{temp}/cache</cachedir></fontconfig>"
        )
        env = dict(
            os.environ,
            FONTCONFIG_FILE=str(font),
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )
        for name in ("power_supply.kicad_sch", "sym-lib-table", "RMX_E14.kicad_sym"):
            # Embedded schematic library symbols suffice; table paths are copied for parity resolution.
            if (SUPPLY / name).exists():
                shutil.copy2(SUPPLY / name, temp / name)
        shutil.copy2(ROOT / "power_supply.kicad_pro", temp / "power_supply.kicad_pro")
        shutil.copytree(SUPPLY / "RMX_Power.pretty", temp / "RMX_Power.pretty")
        (temp / "fp-lib-table").write_text(
            (ROOT / "fp-lib-table")
            .read_text()
            .replace("${KIPRJMOD}/../RMX_Power.pretty", "${KIPRJMOD}/RMX_Power.pretty")
        )
        shutil.copy2(pcb, temp / "power_supply.kicad_pcb")

        def run(*args):
            p = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, text=True)
            assert p.returncode == 0, (args, p.stdout, p.stderr)
            return p.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            temp / "netlist.xml",
            SUPPLY / "power_supply.kicad_sch",
        )
        parts, pins = netlist(temp / "netlist.xml")
        contract(parts, pins)
        # Reuse independent full 157-part/net, EP, outline/hole and thermal-reserve checks,
        # with copper removed only in a temporary copy for that placed-only checker.
        bare = [x for x in tree if not isinstance(x, list) or not x or x[0] not in ("segment", "via", "zone")]
        bare_path = temp / "placement.kicad_pcb"
        bare_path.write_text(sexpr(bare) + "\n")
        packet = mechanical(bare_path, pins)
        packet.update(
            revision="dual-buck-and-raw-17V-routing-in-progress",
            pcb_sha256=sha(pcb),
            pcb_partially_routed=True,
            pcb_routed=False,
            source_placement_sha256=sha(SUPPLY / "power_supply.kicad_pcb"),
            remaining=[
                "remaining supply circuitry and return/shielding layout",
                "actual copper/reference drop, feedback loop and thermal/EMI qualification",
                "lead/harness/height bounds, housing integration and physical tests",
            ],
        )
        (OUT / "placement.json").write_text(json.dumps(packet, indent=2) + "\n")
        run(
            "pcb",
            "drc",
            "--refill-zones",
            "--save-board",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            temp / "power_supply.kicad_pcb",
        )
        drc = json.loads((OUT / "drc.json").read_text())
        assert not drc["violations"] and not drc["schematic_parity"], (
            drc["violations"],
            drc["schematic_parity"],
        )
        assert drc["unconnected_items"], "This stage is intentionally incomplete"
        filled = temp / "power_supply.kicad_pcb"
        saved = read_sexpr(filled.read_text())
        planes = [z for z in children(saved, "zone") if not children(z, "keepout")]
        assert len(planes) == 1 and str(first(planes[0], "net")[-1]) == "/AGND"
        assert first(planes[0], "layer")[1] == "In1.Cu" and children(planes[0], "filled_polygon")
        shutil.copy2(filled, OUT / "filled.kicad_pcb")
        for name, layers in [
            ("top", "F.Cu,F.Fab,F.SilkS,Edge.Cuts"),
            ("copper", "F.Cu,Edge.Cuts"),
            ("ground", "In1.Cu,Edge.Cuts"),
            ("bottom", "B.Cu,B.Fab,B.SilkS,Edge.Cuts"),
        ]:
            run(
                "pcb",
                "export",
                "svg",
                "--mode-single",
                "--page-size-mode",
                "2",
                "--exclude-drawing-sheet",
                "--layers",
                layers,
                "-o",
                OUT / (name + ".svg"),
                temp / "power_supply.kicad_pcb",
            )
    files = [
        *ROOT.glob("*.py"),
        ROOT / "README.md",
        ROOT / "power_supply.kicad_pro",
        ROOT / "fp-lib-table",
        pcb,
        OUT / "routing-inputs.json",
        OUT / "placement.json",
        OUT / "drc.json",
        OUT / "filled.kicad_pcb",
        SUPPLY / "power_supply.kicad_sch",
        SUPPLY / "power_supply.kicad_pcb",
        SUPPLY / "power_supply.kicad_pro",
        SUPPLY / "components.json",
        SUPPLY / "check_placement.py",
        SUPPLY / "verify.py",
        SUPPLY / "fp-lib-table",
        SUPPLY / "generated/placement-inputs.json",
    ]
    files += list((SUPPLY / "RMX_Power.pretty").glob("*.kicad_mod"))
    files += list((SUPPLY.parent / "dac_receiver").glob("*.py"))
    files += list((SUPPLY.parent / "common").glob("*.py"))
    files += [
        SUPPLY.parent / "control_inputs/board.py",
        SUPPLY.parent / "output_stage/check_placement.py",
        SUPPLY.parent / "input_protection/route_grid.py",
    ]
    record = dict(
        stage="dual-buck-and-raw-17V-paths",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kicad_version=version,
        components=157,
        native_drc_violations=0,
        schematic_parity_issues=0,
        unconnected_items=len(drc["unconnected_items"]),
        segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        local_paths=paths,
        saved_ground_planes_filled=1,
        digital_buck_bulk_parts_front=True,
        analog_pre_buck_bulk_parts_front=True,
        analog_pre_sense_pad=list(paths["pre_output_sense"]["from_pad"]),
        analog_pre_reference_pad=list(paths["pre_quiet_ground"]["to_pad"]),
        front_buck_components=front_count,
        front_raw_components=raw_front_count,
        minimum_via_drill_to_land_mm=drill_clearance,
        ground_layout=ground,
        exposed_pad_nets=packet["exposed_pad_nets"],
        source_sense_pad=list(paths["output_kelvin"]["from_pad"]),
        feedback_ground_reference_pad=list(paths["feedback_ground"]["to_pad"]),
        ground_drop_budget_verified=False,
        feedback_loop_stability_verified=False,
        fully_routed=False,
        thermal_or_ampacity_qualified=False,
        switching_or_emi_qualified=False,
        housing_fit_verified=False,
        build_ready=False,
        source_sha256={os.path.relpath(p, ROOT): sha(p) for p in files},
    )
    (OUT / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        f"Partial supply copper: {record['segments']} segments, zero native DRC/parity issues, {record['unconnected_items']} open connections"
    )
    for name, result in paths.items():
        print(f"  {name}: {result['length_mm']:.3f} mm")


if __name__ == "__main__":
    main()
