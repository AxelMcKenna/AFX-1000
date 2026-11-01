"""Actual-courtyard placement feasibility for a NEW, unrouted NF03 PCB.

This tests a receiving outline, not electrical layout or manufactured fit.
"""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "compact"
GAP = .4


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def intersects(a, b):
    return a[0] < b[0] + b[2] - 1e-9 and b[0] < a[0] + a[2] - 1e-9 and a[1] < b[1] + b[3] - 1e-9 and b[1] < a[1] + a[3] - 1e-9


def subtract(free, used):
    result = []
    for x, y, w, h in free:
        if not intersects([x, y, w, h], used):
            result.append([x, y, w, h])
            continue
        ux, uy, uw, uh = used
        for box in [[x, y, ux - x, h], [ux + uw, y, x + w - ux - uw, h],
                    [x, y, w, uy - y], [x, uy + uh, w, y + h - uy - uh]]:
            if box[2] > 1e-8 and box[3] > 1e-8:
                result.append(box)
    # MaxRects may overlap; discard only wholly contained free rectangles.
    return [a for i, a in enumerate(result) if not any(
        i != j and b[0] <= a[0] + 1e-9 and b[1] <= a[1] + 1e-9 and
        b[0] + b[2] >= a[0] + a[2] - 1e-9 and b[1] + b[3] >= a[1] + a[3] - 1e-9 and
        (a != b or j < i) for j, b in enumerate(result)
    )]


def dimensions(row, rotation):
    b = row["courtyard_bbox_mm"]
    w, h = b[2] - b[0], b[3] - b[1]
    return (h, w) if rotation == 90 else (w, h)


def pack(rows, order):
    by_ref = {r["ref"]: r for r in rows}
    free = [[2., 2., 145., 35.]]
    placements = {}

    def add(ref, x, y, rotation):
        w, h = dimensions(by_ref[ref], rotation)
        actual = [x, y, w, h]
        if any(intersects(actual, p["courtyard_rect_mm"]) for p in placements.values()):
            raise ValueError(f"Fixed anchor overlaps another courtyard: {ref}")
        placements[ref] = dict(rotation_deg=rotation, courtyard_rect_mm=actual)
        return subtract(free, [x, y, w + GAP, h + GAP])

    # N12 uses the left deep bay; lower-current N19 uses worldX282..320,
    # beyond the right floor inlet. These are receiving placements only.
    anchors = [
        ("U22", 2.5, 2.25, 0), ("U17", 110., 2.25, 0),
        ("C50", 2.5, 12., 0), ("C51", 11., 12., 0),
        ("C26", 110., 12., 0), ("C27", 118.5, 12., 0),
        ("U23", 2.5, 21.5, 90), ("U18", 110., 21.5, 90),
        ("J1", 49., 2., 90), ("Q2", 26., 18., 0), ("Q1", 128., 18., 0),
        ("R86", 16., 31., 0), ("R69", 119., 31., 0),
        ("J4", 24.5, 30., 0), ("J2", 127.5, 30., 0),
        ("U11", 13.5, 21., 0), ("U12", 45., 23., 0),
        ("U5", 97.3, 21., 0), ("U6", 83.5, 23., 0),
        ("J5", 59., 30., 0), ("J3", 97.3, 30., 0),
        ("U13", 49., 10.5, 0), ("U14", 59., 10.5, 0), ("U15", 69., 10.5, 0),
    ]
    parts = json.loads((SOURCE / "components.json").read_text())
    for rail, x0 in [("N12", 24.5), ("N19", 129.)]:
        array = [c for c in parts if c["ref"].startswith("C") and
                 {p["net"] for p in c["pins"]} == {rail + "_CR_TOP", rail + "_E28_SRC"}]
        assert len(array) == (9 if rail == "N12" else 12)
        for i, c in enumerate(array):
            w, h = dimensions(by_ref[c["ref"]], 0)
            anchors.append((c["ref"], x0 + (i % 3) * (w + GAP), 2 + (i // 3) * (h + GAP), 0))
    for ref, x, y, rotation in anchors:
        free = add(ref, x, y, rotation)
    remaining = [r for r in rows if r["ref"] not in placements]
    remaining.sort(key=order, reverse=True)
    for row in remaining:
        choices = []
        for rotation in (0, 90):
            w, h = dimensions(row, rotation)
            for x, y, fw, fh in free:
                if w + GAP <= fw + 1e-8 and h + GAP <= fh + 1e-8:
                    choices.append((min(fw - w - GAP, fh - h - GAP), max(fw - w - GAP, fh - h - GAP), y, x, rotation))
        if not choices:
            return None, row["ref"]
        _, _, y, x, rotation = min(choices)
        free = add(row["ref"], x, y, rotation)
    return placements, None


def main():
    assert not (ROOT / "handoff.json").exists(), "Create a successor to a sealed placement"
    handoff = json.loads((SOURCE / "handoff.json").read_text())
    for name, digest in handoff["files_sha256"].items():
        assert sha(SOURCE / name) == digest, name
    area = json.loads((SOURCE / "generated/footprint-area.json").read_text())
    all_rows = area["rows"]
    parts = json.loads((SOURCE / "components.json").read_text())
    backside_refs = [c["ref"] for c in parts if c.get("note") == "Actual local front bypass required in PCB implementation."]
    rows = [r for r in all_rows if r["ref"] not in backside_refs]
    attempts = []
    orders = [
        lambda r: r["courtyard_area_mm2"],
        lambda r: max(dimensions(r, 0)),
        lambda r: sum(dimensions(r, 0)),
        lambda r: min(dimensions(r, 0)),
    ]
    placements = None
    for n, order in enumerate(orders):
        candidate, failed = pack(rows, order)
        attempts.append(dict(sort_order=n, first_unplaced=failed))
        if candidate is not None:
            placements = candidate
            break
    out = ROOT / "generated"
    out.mkdir(parents=True, exist_ok=True)
    (out / "packing-attempts.json").write_text(json.dumps(attempts, indent=2) + "\n")
    if placements is None:
        raise SystemExit("No full placement found; failures preserved, no native PCB claimed")
    for row in rows:
        p = placements[row["ref"]]
        x, y, _, _ = p["courtyard_rect_mm"]
        xmin, ymin, xmax, _ = row["courtyard_bbox_mm"]
        p["anchor_mm"] = [x - ymin, y + xmax] if p["rotation_deg"] == 90 else [x - xmin, y - ymin]
    source = ROOT / "sources"
    source.mkdir(exist_ok=True)
    for name in ["components.json", "generated/footprint-area.json", "handoff.json"]:
        shutil.copyfile(SOURCE / name, source / Path(name).name)
    shutil.copytree(SOURCE / "sources/footprints", source / "footprints", dirs_exist_ok=True)
    boxes = [p["courtyard_rect_mm"] for p in placements.values()]
    for box in boxes:
        x, y, w, h = box
        assert x >= 2 and y >= 2 and x + w <= 147 + 1e-8 and y + h <= 37 + 1e-8
    for i, a in enumerate(boxes):
        assert not any(intersects(a, b) for b in boxes[i + 1:])
    bbox_sum = sum(dimensions(r, 0)[0] * dimensions(r, 0)[1] for r in all_rows)
    report = dict(
        scope="Actual-library courtyard packing only; not an accepted electrical layout",
        board_mm=[149, 39, 1.6], edge_margin_mm=2, additional_courtyard_gap_mm=GAP,
        component_exclusion_rect_mm=None,
        proposed_world_datum_mm=[172, 180.5, 3.5],
        component_side_proposal="toward decreasing worldY; local PCB Y maps to increasing worldZ",
        placements=placements, parts=len(all_rows), front_courtyards_placed=len(placements),
        pending_backside_bypass_refs=backside_refs, sum_courtyard_bbox_mm2=bbox_sum,
        usable_rectangular_area_after_edges_and_post_band_mm2=5075,
        area_ratio_to_courtyard_bboxes=5075 / bbox_sum,
        source_handoff_sha256=sha(SOURCE / "handoff.json"),
        electrical_placement_reviewed=False, board_routed=False,
        mounting_hardware_selected=False, connector_mating_implemented=False,
        actual_body_heights_and_THT_tails_qualified=False, whole_unit_fit_verified=False,
        physical_qualified=False, fabrication_released=False,
    )
    (out / "placement.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Packed", len(placements), "courtyards; usable area / bbox sum", round(5075 / bbox_sum, 4))


if __name__ == "__main__":
    main()
