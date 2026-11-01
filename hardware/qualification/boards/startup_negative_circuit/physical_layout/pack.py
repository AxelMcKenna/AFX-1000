"""Two-face courtyard study with explicit connector, force and module anchors.

No native PCB, routing or physical fit is implied by a successful packing run.
"""

import hashlib
import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
GAP = .2


def overlaps(a, b):
    return (a[0] < b[0] + b[2] - 1e-9 and b[0] < a[0] + a[2] - 1e-9
            and a[1] < b[1] + b[3] - 1e-9 and b[1] < a[1] + a[3] - 1e-9)


def subtract(free, used):
    result = []
    for x, y, w, h in free:
        if not overlaps([x, y, w, h], used):
            result.append([x, y, w, h])
            continue
        ux, uy, uw, uh = used
        for b in [[x, y, ux - x, h], [ux + uw, y, x + w - ux - uw, h],
                  [x, y, w, uy - y], [x, uy + uh, w, y + h - uy - uh]]:
            if b[2] > 1e-8 and b[3] > 1e-8:
                result.append(b)
    return [a for i, a in enumerate(result) if not any(
        i != j and b[0] <= a[0] + 1e-9 and b[1] <= a[1] + 1e-9
        and b[0] + b[2] >= a[0] + a[2] - 1e-9
        and b[1] + b[3] >= a[1] + a[3] - 1e-9
        and (a != b or j < i) for j, b in enumerate(result))]


def rotate(point, angle):
    x, y = point
    return {0: [x, y], 90: [y, -x], 180: [-x, -y], 270: [-y, x]}[angle]


def transformed(box, angle, side="F"):
    pts = [rotate([x, -y if side == "B" else y], angle)
           for x in [box[0], box[2]] for y in [box[1], box[3]]]
    return [min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts) - min(p[0] for p in pts),
            max(p[1] for p in pts) - min(p[1] for p in pts)]


def attempt(rows, parts, ports, order):
    by = {r["ref"]: r for r in rows}
    part = {c["ref"]: c for c in parts}
    free = {s: [[2., 2., 145., 35.]] for s in ["F", "B"]}
    placed = {}
    # Independent strain-post copper exclusions on both populated faces. The
    # square reserve conservatively encloses the actual radius3.7mm rule area.
    for x, y in [(61., 21.), (90., 21.)]:
        for side in ["F", "B"]:
            free[side] = subtract(free[side], [x - 3.9, y - 3.9, 7.8, 7.8])
    backside = {c["ref"] for c in parts if c["ref"].startswith("C")
                and c["footprint"].endswith("C_0603_1608Metric")}
    backside |= {"R" + str(n) for n in range(15, 56)}
    backside |= {"R" + str(n) for n in range(90, 100)}
    backside |= {"R1", "R8"}
    local_rear_1p9_caps = {"C4", "C5", "C6", "C7", "C9", "C11", "C13",
                          "C31", "C32", "C33", "C34", "C36", "C38", "C40"}
    backside |= local_rear_1p9_caps
    assert len(backside) == 111

    def add(ref, x, y, angle, side="F"):
        b = transformed(by[ref]["courtyard_bbox_mm"], angle, side)
        rect = [x, y, b[2], b[3]]
        if x < 2 or y < 2 or x + b[2] > 147 + 1e-8 or y + b[3] > 37 + 1e-8:
            raise ValueError((ref, "out of receiving inset", rect))
        for other, p in placed.items():
            if p["side"] == side and overlaps(rect, p["courtyard_rect_mm"]):
                raise ValueError((ref, "courtyard overlap", other, rect, p["courtyard_rect_mm"]))
        for px, py in [(61., 21.), (90., 21.)]:
            # The two declared pigtail courts can enter this abstract square;
            # their real copper is checked against the actual R3.7 circular
            # native KO, and the maxR3.05 post/solder volumes are checked in
            # NC265's separate3D receiving test. No other part gets this rule.
            if ref not in ["J2", "J4"] and overlaps(rect, [px - 3.9, py - 3.9, 7.8, 7.8]):
                raise ValueError((ref, "strain-post reserve overlap", rect))
        placed[ref] = dict(side=side, anchor_mm=[x - b[0], y - b[1]],
                           rotation_deg=angle, courtyard_rect_mm=rect)
        free[side] = subtract(free[side], [x - GAP / 2, y - GAP / 2, b[2] + GAP, b[3] + GAP])
        # THT part projections are excluded on the back, including real pad
        # and tail space. This is deliberately larger than individual lands.
        if side == "F" and (part[ref]["footprint"].startswith(("Connector_", "Converter_", "Capacitor_THT:", "Package_DIP:"))
                            or ref in ["J2", "J4"]):
            free["B"] = subtract(free["B"], [x - GAP / 2, y - GAP / 2, b[2] + GAP, b[3] + GAP])

    def add_anchor(ref, x, y, angle=0, side="F"):
        b = transformed(by[ref]["courtyard_bbox_mm"], angle, side)
        add(ref, x + b[0], y + b[1], angle, side)

    for p in ports:
        b = transformed(by[p["ref"]]["courtyard_bbox_mm"], p["rotation_deg"])
        add(p["ref"], p["anchor_mm"][0] + b[0], p["anchor_mm"][1] + b[1], p["rotation_deg"])
    for ref, x, y, angle in [
        ("U22", 2.5, 2.25, 0), ("U17", 110., 2.25, 0),
        ("C50", 36., 2.5, 0), ("C51", 44.5, 2.5, 0),
        ("C26", 91.5, 2.5, 0), ("C27", 100., 2.5, 0),
        ("Q2", 37., 20.8, 0), ("Q1", 130., 20.8, 0),
        ("U23", 20., 26.5, 90), ("U18", 119.2, 26.5, 90),
        ("U13", 49., 10.5, 0), ("U14", 60., 10.5, 0), ("U15", 71., 8., 0),
        ("U19", 110., 18.1, 0), ("U24", 11.5, 23., 90),
        ("R73", 10., 10.7, 180), ("R74", 2.5, 10.7, 180),
        ("R56", 110., 11., 180), ("R57", 110., 14.5, 0),
    ]:
        add(ref, x, y, angle)
    for ref, x, y, angle in [("R69", 134.5, 34.4, 180), ("R86", 41.5, 34.4, 180),
                             ("U20", 121.5, 23.5, 0), ("U21", 125., 23.5, 0),
                             ("U25", 18.3, 24., 0), ("U26", 18.3, 26.5, 0)]:
        add_anchor(ref, x, y, angle)
    for rail, x0, y0, expected in [("N12", 21., 2.5, 9), ("N19", 94.2, 12., 12)]:
        array = [c for c in parts if c["ref"].startswith("C")
                 and {p["net"] for p in c["pins"]} == {rail + "_CR_TOP", rail + "_E28_SRC"}]
        assert len(array) == expected
        for i, c in enumerate(array):
            b = transformed(by[c["ref"]]["courtyard_bbox_mm"], 0)
            add(c["ref"], x0 + (i % 3) * (b[2] + GAP), y0 + (i // 3) * (b[3] + GAP), 0)
    # Taller1206 filters are explicit local rear receiving exceptions, below
    # the upper seat and away from carrier columns; whole-unit native body/tail
    # clearance must verify their1.9mm complete normal projection separately.
    # The two module filter pairs lie behind the SIP body, beyond its pin row;
    # actual through-hole land/drill/tail checks remain mandatory.
    for ref, x, y, angle in [("C4", 113.82, 7.8, 180), ("C5", 122.71, 7.8, 0),
                             ("C31", 6.32, 7.8, 180), ("C32", 15.21, 7.8, 0),
                             ("C6", 126.3, 30.1, 270), ("C33", 27.1, 30.1, 270),
                             ("C7", 125.99, 34.9, 0), ("C34", 26.79, 34.9, 0)]:
        add_anchor(ref, x, y, angle, "B")
    # The RAW5 UV monitor, switched LED-energy stage and its three1206 caps
    # form an actual local cell. Their old generic packing positions were not
    # accepted as a bypass, CT or switch-input layout.
    for ref, x, y, angle in [("U56", 134.8, 17.8, 90), ("U57", 140.2, 17.8, 0),
                             ("C97", 137.2, 15.3, 90), ("C98", 143.45, 15.3, 90),
                             ("C99", 131.35, 15.3, 90)]:
        add_anchor(ref, x, y, angle)
    for ref, x, y in [("R92", 134.2, 15.2), ("R93", 134.2, 17.35),
                       ("R94", 134.2, 19.5), ("R95", 138.1, 19.5),
                       ("R96", 141.6, 19.5), ("R97", 141.5, 14.4)]:
        add_anchor(ref, x, y, side="B")
    remaining = sorted([r for r in rows if r["ref"] not in placed and r["ref"] not in backside],
                       key=order, reverse=True)
    for row in remaining:
        choices = []
        for angle in [0, 90]:
            b = transformed(row["courtyard_bbox_mm"], angle)
            for x, y, w, h in free["F"]:
                if b[2] + GAP <= w + 1e-8 and b[3] + GAP <= h + 1e-8:
                    choices.append((min(w - b[2], h - b[3]), max(w - b[2], h - b[3]), y, x, angle))
        if not choices:
            return None, dict(ref=row["ref"], side="F", reason="No remaining rectangle")
        _, _, y, x, angle = min(choices)
        add(row["ref"], x + GAP / 2, y + GAP / 2, angle)
    original_owners = ["U1", "U2", "U3", "U7", "U8", "U9", "U13", "U14", "U15", "U16",
                       "U27", "U28", "U29", "U30", "U31", "U32", "U33", "U34",
                       *["U" + str(n) for n in range(35, 49)]]
    owners = {"C" + str(56 + i): ref for i, ref in enumerate(original_owners)}
    owners.update(C3="U4", C12="U10", C39="U19", C55="U24", C88="U49", C89="U50",
                  C90="U51", C91="U52", C93="U53", C94="U54", C96="U55", C100="U58")
    owners.update(C9="U20", C11="U21", C13="U19", C36="U25", C38="U26", C40="U24")
    owners.update(C4="U17", C5="U17", C31="U22", C32="U22",
                  C6="U18", C33="U23", C7="U18", C34="U23")
    assert set(owners) == {r for r in backside if r.startswith("C")} and len(owners) == 58

    def pad_xy(ref, number):
        path = ROOT / "NF06P.pretty" / (by[ref]["proposed_footprint"].split(":")[1] + ".kicad_mod")
        fp = read_sexpr(path.read_text())
        pad = next(p for p in children(fp, "pad") if str(p[1]) == str(number))
        return list(map(float, first(pad, "at")[1:3]))

    def power_xy(cap):
        owner = owners[cap]
        power_net = next(p["net"] for p in part[cap]["pins"] if p["number"] == "1")
        pins = [p["number"] for p in part[owner]["pins"]
                if p["kind"] in ["power_in", "power_out", "output"] and p["net"] == power_net]
        assert len(pins) == 1, (cap, owner, power_net, pins)
        pin = pins[0]
        pos = placed[owner]
        delta = rotate(pad_xy(owner, pin), pos["rotation_deg"])
        return [pos["anchor_mm"][i] + delta[i] for i in [0, 1]]

    assignments = []
    for ref in sorted(owners, key=lambda c: by[owners[c]]["courtyard_area_mm2"]):
        desired = power_xy(ref)
        if ref in placed:
            pos = placed[ref]
            delta = rotate(pad_xy(ref, "1"), pos["rotation_deg"])
            actual = [pos["anchor_mm"][i] + delta[i] for i in [0, 1]]
            assignments.append(dict(cap=ref, owner=owners[ref], power_pad_mm=desired,
                                    projected_power_pad_separation_mm=math.dist(desired, actual),
                                    explicit_local_rear_height_receiving_mm=1.9,
                                    actual_via_and_return_loop_qualified=False))
            continue
        choices = []
        for angle in [0, 90, 180, 270]:
            b = transformed(by[ref]["courtyard_bbox_mm"], angle, "B")
            pin = rotate(pad_xy(ref, "1"), angle)
            for x, y, w, h in free["B"]:
                if b[2] + GAP <= w + 1e-8 and b[3] + GAP <= h + 1e-8:
                    ax = min(max(desired[0] - pin[0], x + GAP / 2 - b[0]), x + w - GAP / 2 - b[0] - b[2])
                    ay = min(max(desired[1] - pin[1], y + GAP / 2 - b[1]), y + h - GAP / 2 - b[1] - b[3])
                    distance = math.dist(desired, [ax + pin[0], ay + pin[1]])
                    choices.append((distance, ay + b[1], ax + b[0], angle))
        if not choices:
            return None, dict(ref=ref, side="B", reason="No local capacitor rectangle")
        distance, y, x, angle = min(choices)
        add(ref, x, y, angle, "B")
        assignments.append(dict(cap=ref, owner=owners[ref], power_pad_mm=desired,
                                projected_power_pad_separation_mm=distance,
                                actual_via_and_return_loop_qualified=False))
    back = sorted([by[r] for r in backside if not r.startswith("C") and r not in placed], key=lambda r: -r["courtyard_area_mm2"])

    def analog_target(ref):
        excluded = {"AGND", "AUX2V6", "DIG5_FORCE", "GUARDED_12V_FORCE", "MODULE_INPUT_GND",
                    "N19_P03_SRC", "N12_P03_SRC", "N19_INTVCC", "N12_INTVCC"}
        nets = {p["net"] for p in part[ref]["pins"] if p["net"] and p["net"] not in excluded}
        points = []
        for c in parts:
            if not c["ref"].startswith("U") or c["ref"] not in placed:
                continue
            pos = placed[c["ref"]]
            for pin in c["pins"]:
                if pin["net"] in nets:
                    delta = rotate(pad_xy(c["ref"], pin["number"]), pos["rotation_deg"])
                    points.append([pos["anchor_mm"][i] + delta[i] for i in [0, 1]])
        return [math.fsum(p[i] for p in points) / len(points) for i in [0, 1]] if points else None

    for row in back:
        choices = []
        desired = analog_target(row["ref"])
        for angle in [0, 90]:
            b = transformed(row["courtyard_bbox_mm"], angle, "B")
            for x, y, w, h in free["B"]:
                if b[2] + GAP <= w + 1e-8 and b[3] + GAP <= h + 1e-8:
                    cx = x + GAP / 2 if desired is None else min(max(desired[0] - b[2] / 2, x + GAP / 2), x + w - GAP / 2 - b[2])
                    cy = y + GAP / 2 if desired is None else min(max(desired[1] - b[3] / 2, y + GAP / 2), y + h - GAP / 2 - b[3])
                    score = min(w - b[2], h - b[3]) if desired is None else math.dist(desired, [cx + b[2] / 2, cy + b[3] / 2])
                    choices.append((score, cy, cx, angle))
        if not choices:
            return None, dict(ref=row["ref"], side="B", reason="No remaining rectangle")
        _, y, x, angle = min(choices)
        add(row["ref"], x, y, angle, "B")
    assert len(placed) == 265
    placed["_bypass_assignments"] = assignments
    return placed, None


def main():
    assert not (ROOT / "handoff.json").exists()
    inputs = json.loads((ROOT / "land-inventory.json").read_text())
    rows = inputs["rows"]
    parts = json.loads((ROOT / "sources/NF05R/components.json").read_text())
    # This file must be bound to the selected connector/force geometry, not a
    # handwritten stand-in for a different pitch or pin numbering convention.
    ports = json.loads((ROOT / "connector-placement.json").read_text())["ports"]
    assert {p["ref"] for p in ports} == {"J" + str(n) for n in range(1, 7)}
    trials = []
    result = None
    for label, order in [("area", lambda r: r["courtyard_area_mm2"]),
                         ("longest", lambda r: max(transformed(r["courtyard_bbox_mm"], 0)[2:])),
                         ("perimeter", lambda r: sum(transformed(r["courtyard_bbox_mm"], 0)[2:]))]:
        try:
            result, failed = attempt(rows, parts, ports, order)
        except ValueError as e:
            result, failed = None, str(e)
        trials.append(dict(order=label, failure=failed))
        if result is not None:
            break
    path = ROOT / "packing-attempts.json"
    if path.exists():
        old = path.read_bytes()
        history = ROOT / "history/packing-attempts"
        history.mkdir(exist_ok=True)
        (history / (hashlib.sha256(old).hexdigest() + ".json")).write_bytes(old)
    path.write_text(json.dumps(trials, indent=2) + "\n")
    if result is None:
        raise SystemExit("No placement; failures retained, no native PCB inferred")
    assignments = result.pop("_bypass_assignments")
    areas = {side: math.fsum(r["courtyard_area_mm2"] for r in rows if result[r["ref"]]["side"] == side)
             for side in ["F", "B"]}
    report = dict(board_mm=[149, 39, 1.6], component_inset_mm=2,
                  explicit_courtyard_gap_mm=GAP, placements=result, parts=265,
                  front_parts=sum(p["side"] == "F" for p in result.values()),
                  back_parts=sum(p["side"] == "B" for p in result.values()),
                  courtyard_area_each_face_mm2=areas,
                  front_area_ratio_before_post_reserves=5075 / areas["F"],
                  front_post_square_reserved_area_mm2=2 * 7.8**2,
                  front_area_ratio=(5075 - 2 * 7.8**2) / areas["F"],
                  backside_bypass_assignments=assignments,
                  local_rear_1p9_mm_receiving_caps=["C4", "C5", "C6", "C7", "C9", "C11", "C13", "C31", "C32", "C33", "C34", "C36", "C38", "C40"],
                  local_rear_1p9_mm_whole_unit_body_tail_mount_fit_verified=False,
                  maximum_projected_bypass_power_pad_distance_mm=max(a["projected_power_pad_separation_mm"] for a in assignments),
                  backside_bypass_native_geometry_and_PDN_qualified=False,
                  current_loops_and_routing_qualified=False,
                  physical_qualified=False, fabrication_released=False)
    (ROOT / "placement.json").write_text(json.dumps(report, indent=2) + "\n")
    assert report["front_area_ratio"] >= 1.2, "Front area reserve after post exclusions below20%"
    print("265 actual-courtyard placements; front receiving area ratio", report["front_area_ratio"])


if __name__ == "__main__":
    main()
