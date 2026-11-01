"""Resolve the preserved RAW5/TACH clash without moving TACH or other nets."""

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pt(node):
    return tuple(float(v) for v in node[1:3])


def main():
    path = ROOT / "fan_power_health.kicad_pcb"
    hist = ROOT / "history/first-RAW5-dogleg-TACH-clash"
    hist.mkdir(parents=True, exist_ok=False)
    for name in [path.name, "drc-raw-repair.json", "drc-raw-repair.log", "raw-trunk-text-repair.json"]:
        shutil.copyfile(ROOT / name, hist / name)
    tree = read_sexpr(path.read_text())
    footprints = copy.deepcopy(children(tree, "footprint"))
    other = copy.deepcopy([s for tag in ["segment", "via"] for s in children(tree, tag)
                           if first(s, "net")[1] != "/FAN5V_IN"])
    removed = []
    templates = {}
    shortened = []
    for s in list(children(tree, "segment")):
        if first(s, "net")[1] != "/FAN5V_IN":
            continue
        layer = first(s, "layer")[1]
        start, end = first(s, "start"), first(s, "end")
        points = {pt(start), pt(end)}
        if layer == "B.Cu" and points == {(25., 21.), (25., 36.6)}:
            if pt(start) == (25., 36.6):
                start[1:3] = [a(25.), a(34.2)]
            else:
                end[1:3] = [a(25.), a(34.2)]
            shortened.append("Removed now-unused2.4mmRAW5trunkstub")
        remove = layer == "B.Cu" and points in [
            {(18.2, 35.6), (21.2, 35.6)}, {(21.2, 35.6), (22.2, 36.6)}, {(22.2, 36.6), (25., 36.6)}]
        remove = remove or layer == "In2.Cu" and points in [
            {(18.2, 35.6), (25.4328, 36.6)}, {(25.4328, 36.6), (27.9069, 34.1259)}]
        if remove:
            templates[layer] = copy.deepcopy(s)
            removed.append(sexpr(s))
            tree.remove(s)
    assert len(removed) == 5 and len(shortened) == 1
    paths = {"B.Cu": [(18.2, 35.6), (19.6, 34.2), (25., 34.2)],
             "In2.Cu": [(18.2, 35.6), (19.6, 34.2), (27.9069, 34.1259)]}
    for layer, points in paths.items():
        for start, end in zip(points, points[1:]):
            s = copy.deepcopy(templates[layer])
            first(s, "start")[1:3] = [a(v) for v in start]
            first(s, "end")[1:3] = [a(v) for v in end]
            first(s, "uuid")[1] = str(uuid.uuid4())
            tree.append(s)
    assert children(tree, "footprint") == footprints
    assert [s for tag in ["segment", "via"] for s in children(tree, tag)
            if first(s, "net")[1] != "/FAN5V_IN"] == other
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "raw-tach-clearance-repair.json").write_text(json.dumps(dict(
        scope="RAW5-only literal routing repair; TACH and all other nets untouched",
        source_script_sha256=sha(Path(__file__)), input_pcb_sha256=sha(hist / path.name),
        output_before_native_refill_sha256=sha(path), removed_segments=removed,
        shortened=shortened, new_paths_mm=paths, track_widths_B_In2_mm=[1., .2],
        all84_footprints_and_all_unrelated_copper_exact=True,
        native_DRC_required=True, physical_qualified=False, fabrication_released=False), indent=2) + "\n")
    print("RAW5 bypasses fixedTACHbarrel; allunrelatedcopper and84FPsexact; nativeDRC required")


if __name__ == "__main__":
    main()
