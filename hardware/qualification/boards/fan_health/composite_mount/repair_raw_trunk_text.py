"""Literal RAW5 reroute; keep all footprint trees and unrelated copper exact."""

import copy
import hashlib
import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(node):
    return tuple(float(v) for v in node[1:3])


def main():
    assert not (ROOT / "handoff.json").exists()
    path = ROOT / "fan_power_health.kicad_pcb"
    original = ROOT / "history/clip-keepout-force-conflict" / path.name
    assert sha(path) == sha(original), "Preserve every later routing candidate"
    tree = read_sexpr(path.read_text())
    footprints = copy.deepcopy(children(tree, "footprint"))
    other_copper = copy.deepcopy([n for tag in ["segment", "via"] for n in children(tree, tag)
                                 if first(n, "net")[1] != "/FAN5V_IN"])
    moves = {(18.2, 1.9): (18.2, 2.4), (18.2, 36.6): (18.2, 35.6)}
    changed = []
    vias = 0
    for node in children(tree, "via"):
        if first(node, "net")[1] == "/FAN5V_IN":
            at = first(node, "at")
            old = point(at)
            if old in moves:
                at[1:3] = [a(v) for v in moves[old]]
                changed.append(dict(role="via", old_mm=old, new_mm=moves[old]))
                vias += 1
    removed = []
    template = None
    for node in list(children(tree, "segment")):
        if first(node, "net")[1] != "/FAN5V_IN":
            continue
        start, end = first(node, "start"), first(node, "end")
        if first(node, "layer")[1] == "B.Cu" and {point(start), point(end)} == {(25., 36.6), (18.2, 36.6)}:
            assert float(first(node, "width")[1]) == 1.
            template = copy.deepcopy(node)
            removed.append(sexpr(node))
            tree.remove(node)
            continue
        for role, at in [("start", start), ("end", end)]:
            old = point(at)
            if old in moves:
                at[1:3] = [a(v) for v in moves[old]]
                changed.append(dict(role="track_" + role, layer=first(node, "layer")[1],
                                    old_mm=old, new_mm=moves[old], width_mm=float(first(node, "width")[1])))
    assert vias == 2 and len(removed) == 1 and template is not None
    new_path = [(18.2, 35.6), (21.2, 35.6), (22.2, 36.6), (25., 36.6)]
    for start, end in zip(new_path, new_path[1:]):
        node = copy.deepcopy(template)
        first(node, "start")[1:3] = [a(v) for v in start]
        first(node, "end")[1:3] = [a(v) for v in end]
        first(node, "uuid")[1] = str(uuid.uuid4())
        tree.append(node)
    assert children(tree, "footprint") == footprints
    assert [n for tag in ["segment", "via"] for n in children(tree, tag)
            if first(n, "net")[1] != "/FAN5V_IN"] == other_copper
    path.write_text(sexpr(tree) + "\n")
    assert children(read_sexpr(path.read_text()), "footprint") == footprints
    report = dict(scope="Literal RAW5 force-trunk clip-keepout repair; all unrelated copper and footprints exact",
                  source_script_sha256=sha(Path(__file__)), input_pcb_sha256=sha(original),
                  output_before_native_refill_sha256=sha(path), changed=changed,
                  removed_segment=removed, added_B_Cu_1mm_path=new_path,
                  all84_complete_footprint_trees_unchanged=True, all_unrelated_copper_trees_unchanged=True,
                  any_track_or_via_dimension_reduced=False,
                  original_RAW5_literal_paths_inherited=False, fresh_native_DRC_and_refill_required=True,
                  source_PDN_and_current_qualified=False, physical_qualified=False, fabrication_released=False)
    (ROOT / "raw-trunk-text-repair.json").write_text(json.dumps(report, indent=2) + "\n")
    print("RAW5 reroute authored;84FPs/unrelatedcopperexact; dimensionsretained; nativeDRCrequired")


if __name__ == "__main__":
    main()
