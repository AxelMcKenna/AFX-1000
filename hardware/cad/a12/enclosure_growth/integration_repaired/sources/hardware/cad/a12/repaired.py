"""Native repaired-PCB geometry with explicit, unapproved height allocations.

Both PCB faces and protruding leads matter. Courtyard extraction is actual;
unselected component/mate heights remain requirements, not supplier facts.
"""

import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard, transform

from .generate import OUT, REPO, ROOT, sha
from .positive_links.selected_parts import requirement as selected_part_requirement


def height(footprint, ref, part):
    """Maximum assembled projection allocated above the relevant board face."""
    selected = selected_part_requirement(footprint, part)
    if selected is not None:
        return (
            selected["assembled_projection_requirement_mm"],
            selected["basis"] + ": " + selected["mpn"],
        )
    if ref.startswith("H"):
        return 2.31, "Selected fixing-head/washer reserve remains to be approved"
    if "Probe2" in footprint:
        return 0.2, "Unfitted probe copper/solder allowance; no mating body"
    if "7466003R" in footprint:
        return (
            5.4,
            "Wurth5mm nominal body plus0.2mm dimensional/0.2mm seat allocations; DIN ISO2768-1m and assembled process approval remain open",
        )
    if "AWG14_Force" in footprint:
        return 3, "Pad/solder only; operating wire bend and restraint are separate"
    if "PinHeader" in footprint:
        return 13.31, "Engineering header with conditional mated reserve; production mate unselected"
    if "JST_XH" in footprint:
        return 12.31, "Conditional complete vertical XH mating/seat reserve"
    if "JST_VH" in footprint:
        return 11, "Conditional side-entry VH mating/seat reserve"
    if "C_Rect_L7.2mm" in footprint:
        return 10.5, "WIMA MKS2 body10mm plus0.5mm assembly allocation"
    if "CP_Radial" in footprint:
        if "EEUFR1C472" in part:
            return 27.41, "Retained C24 maximum-body/seat/vent envelope from A11"
        if "EEUFR1C152" in part or "EEUFR1V152" in part:
            return 22.41, "Retained Panasonic20mm body plus stated assembly/vent allocation"
        if "EEUFR1V221" in part:
            return 13.41, "Retained Panasonic11.5mm body plus stated assembly/vent allocation"
        raise ValueError((ref, part, "Unknown radial capacitor height"))
    # KEMET C1003_C0G, 2025-02-20, Tables 1A/1B and 2A. External PDF
    # SHA256 02d179914aeb9585eb2229ba8e18ef9d6b01c77c056de2af295d6950a2a5cc0d.
    # The 0.10 mm seating addition is a project allocation, not a supplier
    # guarantee. Match the full selected MPN before the generic package limit.
    if "C1210C104J5GACTU" in part:
        return 1.5, "Selected KEMET FG body maximum1.40mm plus0.10mm seat allocation"
    if "C1206C473J5GACTU" in part:
        return 1.3, "Selected KEMET EE body maximum1.20mm plus0.10mm seat allocation"
    if "C1206C104J3GACTU" in part:
        return 1.9, "Selected KEMET EH body maximum1.80mm plus0.10mm seat allocation"
    if any(mpn in part for mpn in ("C3225X7R1H226M250AC", "C3225X7S1E476M250AC")):
        return (
            2.9,
            "Selected TDK2.50+/-0.30mm body plus0.10mm seat allocation; assembly process approval open",
        )
    if "C_1210" in footprint or "C_1206" in footprint:
        return 2.8, "Maximum permitted capacitor/seat projection; actual MPN approval required"
    if "C_0805" in footprint or "C_0603" in footprint:
        return 1.5, "Maximum permitted capacitor/seat projection; actual MPN approval required"
    if "Resistor_SMD" in footprint:
        return 0.9, "Maximum permitted resistor/seat projection; actual MPN approval required"
    if "SOIC" in footprint:
        return 1.85, "SOIC maximum1.75mm plus0.10mm assembly allowance; exact package must be checked"
    if "TSSOP" in footprint or "PW0014A" in footprint:
        return 1.3, "TSSOP maximum1.2mm plus0.10mm assembly allowance; exact package must be checked"
    if "SSOP" in footprint:
        return 1.85, "SSOP maximum/seat allocation; exact package must be checked"
    if "TO-263" in footprint:
        return 4.8, "TO263 assembly projection allocation"
    if "SRP1050" in footprint or "SRP7050" in footprint:
        return 5.8, "Selected inductor maximum-body/seat allocation; MPN/process approval open"
    if "XAL7030" in footprint:
        return 3.5, "Selected inductor maximum-body/seat allocation; MPN/process approval open"
    if "D_SMA" in footprint or "D_SMB" in footprint:
        return 2.8, "Rectifier/TVS maximum-body/seat allocation; exact MPN approval open"
    if "SOT-23" in footprint:
        return 1.6, "SOT23 maximum1.45mm plus0.15mm assembly allocation; exact package approval required"
    if any(
        name in footprint
        for name in (
            "DFN",
            "QFN",
            "MSOP",
            "SOT-",
            "LFPAK",
            "Q5B",
            "RPY0014A",
            "YWP0012A",
            "DSE0006A",
            "DCU0008A",
        )
    ):
        return 1.4, "Low-profile semiconductor maximum-body/seat allocation; exact package approval required"
    raise ValueError((ref, footprint, "No assembled-height requirement declared"))


def outline(tree):
    adjacency = {}
    for edge in children(tree, "gr_line"):
        if first(edge, "layer")[1] != "Edge.Cuts":
            continue
        a, b = [tuple(round(float(v) - 100, 6) for v in first(edge, key)[1:3]) for key in ("start", "end")]
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    assert adjacency and all(len(points) == 2 for points in adjacency.values())
    start = min(adjacency)
    ordered, previous, current = [], None, start
    while True:
        assert current not in ordered
        ordered.append(current)
        following = next(point for point in adjacency[current] if point != previous)
        previous, current = current, following
        if current == start:
            break
    assert len(ordered) == len(adjacency), "Disconnected board-outline loop"
    return ordered


def same_board_intersections(boxes, cylinders):
    """Exact intersections of the declared box/cylinder envelopes, including tails.

    Same-board Z displacement is correlated. Do not independently sweep the
    whole board in opposite directions and invent component-to-component hits.
    """
    rows = [("box", row) for row in boxes] + [("cylinder", row) for row in cylinders]
    hits = []
    for index, (kind_a, a) in enumerate(rows):
        for kind_b, b in rows[index + 1 :]:
            if a[0].split("_", 1)[0] != b[0].split("_", 1)[0]:
                continue
            if a[0].split("_tail_", 1)[0] == b[0].split("_tail_", 1)[0]:
                continue
            za = a[3] + a[6 if kind_a == "box" else 5]
            zb = b[3] + b[6 if kind_b == "box" else 5]
            if min(za, zb) - max(a[3], b[3]) <= 1e-5:
                continue
            if kind_a == kind_b == "box":
                hit = all(
                    min(a[k + 1] + a[k + 4], b[k + 1] + b[k + 4]) - max(a[k + 1], b[k + 1]) > 1e-5
                    for k in range(2)
                )
            elif kind_a == kind_b == "cylinder":
                hit = math.dist(a[1:3], b[1:3]) < (a[4] + b[4]) / 2 - 1e-5
            else:
                cylinder, box = (a, b) if kind_a == "cylinder" else (b, a)
                distance2 = sum(
                    max(box[k + 1] - cylinder[k + 1], 0, cylinder[k + 1] - box[k + 1] - box[k + 4]) ** 2
                    for k in range(2)
                )
                hit = distance2 < (cylinder[4] / 2) ** 2 - 1e-8
            if hit:
                hits.append([a[0], b[0]])
    return hits


def validate_changed_parts(parts, baseline, selections):
    """Changed candidate MPNs require exact geometry and matching selection data.

    Role/net/face changes do not change a part's dimensions. Changed parts and
    newly added parts cannot inherit a generic case height from the baseline.
    """
    for ref, part in parts.items():
        old = baseline.get(ref)
        if old is not None and all(part[k] == old[k] for k in ("part", "footprint")):
            continue
        exact = selected_part_requirement(part["footprint"], part["part"])
        assert exact is not None, (ref, "Changed part needs an independent exact geometry resolver")
        selected = [row for row in selections if ref in row["refs"]]
        assert len(selected) == 1 and selected[0]["mpn"] == exact["mpn"], (
            ref, "Changed part/selection MPN mismatch"
        )
        assert selected[0]["native_footprint"] == part["footprint"], (
            ref, "Changed part/selection footprint mismatch"
        )


def packet(board_overrides=None):
    """Extract actual source geometry; optional isolated board project folders.

    Datums, thickness allocations and the shared exact-part height resolver
    remain the declared A12 interface. An override changes native source files,
    never component coordinates inferred from a different PCB.
    """
    board_overrides = {} if board_overrides is None else board_overrides
    assert not (set(board_overrides) - {"P03", "E28"}), "Unknown board override"
    boards, boxes, cylinders, records = [], [], [], []
    mount_fasteners = []
    sources = [
        Path(__file__),
        ROOT / "positive_links/selected_parts.py",
        ROOT / "interface.json",
        ROOT / "generate.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(path.relative_to(REPO)): sha(path) for path in sources}
    contract = json.loads((ROOT / "interface.json").read_text())
    for identity, folder, basename, datum, thickness_range in [
        (
            "P03",
            "power_distribution/p03",
            "power_p03",
            contract["power_candidate"]["datum"],
            contract["power_candidate"]["fabrication_thickness_range"],
        ),
        (
            "E28",
            "rail_disconnect/revision28",
            "rail_disconnect",
            contract["disconnect_terminals"]["board_datum"],
            [1.5, 1.7],
        ),
    ]:
        root = Path(board_overrides.get(identity, REPO / "hardware/electronics" / folder)).resolve()
        root.relative_to(REPO)
        pcb, components = root / (basename + ".kicad_pcb"), root / "components.json"
        sources += [pcb, components]
        hashes.update({str(path.relative_to(REPO)): sha(path) for path in (pcb, components)})
        tree = read_sexpr(pcb.read_text())
        thickness = float(first(first(tree, "general"), "thickness")[1])
        assert thickness_range[0] <= thickness <= thickness_range[1]
        parts = {part["ref"]: part for part in json.loads(components.read_text())}
        if identity == "P03":
            selections_file = root / "component-selections.json"
            hashes[str(selections_file.relative_to(REPO))] = sha(selections_file)
            selections = json.loads(selections_file.read_text())["selections"]
            if identity in board_overrides:
                baseline_file = REPO / "hardware/electronics" / folder / "components.json"
                hashes[str(baseline_file.relative_to(REPO))] = sha(baseline_file)
                baseline = {p["ref"]: p for p in json.loads(baseline_file.read_text())}
                validate_changed_parts(parts, baseline, selections)
        holes = []
        for fp in children(tree, "footprint"):
            props = {p[1]: p[2] for p in children(fp, "property")}
            ref, footprint = props["Reference"], str(fp[1])
            side = "B" if first(fp, "layer")[1] == "B.Cu" else "F"
            if ref.startswith("H"):
                for pad in children(fp, "pad"):
                    if pad[2] == "np_thru_hole":
                        xy = transform(fp, first(pad, "at")[1:3])
                        holes.append([xy[0] - 100, xy[1] - 100, float(first(pad, "drill")[1])])
                        name = identity + "_" + ref + "_mount_head"
                        projection, basis = height(footprint, ref, "unselected M2 head/washer")
                        cylinders.append(
                            [
                                name,
                                datum[0] + xy[0] - 100,
                                datum[1] + xy[1] - 100,
                                datum[2] + thickness_range[0],
                                5.6,
                                projection + thickness_range[1] - thickness_range[0],
                            ]
                        )
                        mount_fasteners.append(
                            dict(
                                name=name,
                                diameter_requirement_mm=5.6,
                                projection_requirement_mm=projection,
                                basis=basis,
                                selected_fastener_and_engagement_approved=False,
                            )
                        )
                continue
            part = parts[ref]
            assert footprint == part["footprint"], (identity, ref, "Native footprint/BOM mismatch")
            assert props["Value"] == part["part"], (identity, ref, "Native value/BOM mismatch")
            x0, y0, x1, y1 = courtyard(fp, side + ".CrtYd")
            projection, basis = height(footprint, ref, part["part"])
            z = datum[2] - projection if side == "B" else datum[2] + thickness_range[0]
            h = projection if side == "B" else projection + thickness_range[1] - thickness_range[0]
            name = identity + "_" + ref
            row = [name, datum[0] + x0 - 100, datum[1] + y0 - 100, z, x1 - x0, y1 - y0, h]
            if "CP_Radial" in footprint and side == "F":
                cylinders.append(
                    [
                        name,
                        row[1] + row[4] / 2,
                        row[2] + row[5] / 2,
                        z,
                        max(row[4:6]),
                        h,
                    ]
                )
            else:
                boxes.append(row)
            records.append(
                dict(
                    board=identity,
                    ref=ref,
                    face=side,
                    actual_footprint=footprint,
                    part=part["part"],
                    maximum_projection_allocation_mm=projection,
                    height_basis=basis,
                    component_and_mate_height_approved=False,
                )
            )
            for pad in children(fp, "pad"):
                if pad[2] != "thru_hole":
                    continue
                xy = transform(fp, first(pad, "at")[1:3])
                # The solder/lead trimming requirement is independent of body
                # height. It is not inferred from the pad or drill diameter.
                boxes.append(
                    [
                        name + "_tail_" + str(pad[1]),
                        datum[0] + xy[0] - 101.4,
                        datum[1] + xy[1] - 101.4,
                        datum[2] - 1.5,
                        2.8,
                        2.8,
                        1.5,
                    ]
                )
        boards.append(
            dict(
                id=identity,
                datum=datum,
                nominal_thickness_mm=thickness,
                thickness_range_allocation_mm=thickness_range,
                outline_relative_mm=outline(tree),
                mounting_holes_relative_mm=holes,
            )
        )
    assert all(sha(REPO / name) == value for name, value in hashes.items()), (
        "PCB source changed during envelope extraction"
    )
    return dict(
        boards=boards,
        boxes=boxes,
        cylinders=cylinders,
        component_records=records,
        mounting_fastener_requirements=mount_fasteners,
        same_board_component_overlap_candidates=same_board_intersections(boxes, cylinders),
        source_sha256=hashes,
        all_component_and_mate_heights_approved=False,
        actual_source_snapshot=True,
        physical_fit_verified=False,
        fabrication_released=False,
    )


def main():
    result = packet()
    OUT.mkdir(exist_ok=True)
    (OUT / "repaired-components.json").write_text(json.dumps(result, indent=2) + "\n")
    boards = [
        [
            b["id"],
            b["datum"],
            b["nominal_thickness_mm"],
            b["outline_relative_mm"],
            b["mounting_holes_relative_mm"],
        ]
        for b in result["boards"]
    ]
    (OUT / "repaired-components.scad").write_text(
        "// Actual native courtyards; conditional assembled heights, no physical approval.\n"
        + "\n".join(
            key + "=" + json.dumps(value) + ";"
            for key, value in [
                ("repaired_boards", boards),
                ("repaired_boxes", result["boxes"]),
                ("repaired_cylinders", result["cylinders"]),
            ]
        )
        + "\n"
    )
    print(
        "A12 repaired PCB envelopes:",
        len(result["component_records"]),
        "parts; all height/mate approvals remain open",
    )
    return result


if __name__ == "__main__":
    main()
