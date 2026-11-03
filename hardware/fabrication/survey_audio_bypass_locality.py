"""Screen supervisor placements near the existing LOCAL_OK root; emit no CAD."""

import copy
import json
import shutil
from pathlib import Path

from shapely.geometry import Point
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import read_sexpr
from hardware.fabrication.audio_main_global_controls import SignalScreen
from hardware.fabrication.audio_main_local_repack import ReceivingSpace, mapper, poses
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audio_main_settle_repack import translate_object
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-controls-06"
OUT = ROOT / "staging/audio-main-bypass-locality-survey-02"
REFS = {"U605", "C606"}
PRIVATE = {
    "cc214893-89fe-51f3-9ab0-dffa88e844df", "78995919-a9ad-5c85-88e9-99c1fd71a7e1",
    "ddc84dd6-8d93-55fe-98e6-a0b37cbff079", "049dbe51-db18-5966-81e9-ce7e94c1ec8a",
    "04423b7f-39c8-5628-8e10-d68ccd302ec7", "5f7d4c1a-1a82-58dc-92ce-a27b69357d6f",
}
OLD_ENTRIES = {
    "725132df-fc3d-511f-aeaa-2f7e178f5fac", "c5015426-9b2c-5fce-8c30-4c9bf7b0e109",
    "f4851338-4a24-5ac9-8e47-80c0b47eb1f3", "a2605fbd-cb20-5bc0-b487-eef218346a38",
}


def run():
    OUT.mkdir(exist_ok=False)
    dest = OUT / "supervisor-space-survey.json"
    assert not dest.exists()
    applied = OUT / "applied-supervisor-space-survey.py.txt"
    assert not applied.exists()
    shutil.copyfile(Path(__file__), applied)
    capture = ROOT / "staging/audio-main-bypass-repack-01/native-inputs.json"
    inputs = [Path(__file__), applied, capture, SOURCE / "audio_core.kicad_pcb",
              ROOT / "audio_main_local_repack.py", ROOT / "audio_main_settle_repack.py",
              ROOT / "audio_main_global_controls.py", ROOT / "route_nf_surface.py"]
    before = relative_hashes(inputs)
    captured = json.loads(capture.read_text())
    verify_hashes(captured["source_sha256"])
    assert captured["native_uncapped_opens"] == 208
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    old = poses(board)
    receiving = ReceivingSpace(board, REFS)
    fixed = [o for o in captured["objects"] if o.get("ref") not in REFS and o["uuid"] not in PRIVATE | OLD_ENTRIES]
    layers = captured["copper_layers"]
    geometry = {layer: [(o, shape(o["layers"][layer])) for o in fixed if o["layers"].get(layer)] for layer in layers}
    trees = {layer: STRtree([g for _, g in rows]) for layer, rows in geometry.items()}
    results = []
    for x, y in [(x, y) for y in (4, 8, 12) for x in range(20, 96, 5)]:
        move = mapper(old["U605"], (x, y, 90))
        updated = {"U605": [x, y, 90], "C606": [*move(old["C606"][:2]), 270]}
        if not receiving.accepts(updated):
            results.append(dict(proposed_poses=updated, receiving_screen_passed=False,
                                preliminary_space_screen_passed=False))
            continue
        moved = [copy.deepcopy(o) for o in captured["objects"] if o.get("ref") in REFS or o["uuid"] in PRIVATE]
        for obj in moved:
            translate_object(obj, move)
        collisions = []
        for obj in moved:
            for layer, ps in obj["layers"].items():
                if not ps:
                    continue
                copper = shape(ps)
                for i in trees[layer].query(copper.buffer(.201)):
                    other, existing = geometry[layer][int(i)]
                    if obj["net"] != other["net"] and copper.distance(existing) < .2:
                        collisions.append(dict(moved_uuid=obj["uuid"], existing_uuid=other["uuid"], layer=layer))
        via = next(o for o in moved if o["kind"] == "PCB_VIA")
        # Test the relocated hole rather than accepting the unchanged-centre
        # shortcut. Its intended, rigidly moved AGND spurs connect at the hole;
        # retain every solder land and all other-net copper in the screen.
        context = dict(captured, objects=fixed+[o for o in moved if o["kind"] == "PAD" or o["net"] != "AGND"])
        legal_via = SignalScreen(context).via_legal("AGND", via["position_mm"])
        smd = [shape(ps) for o in context["objects"] if o["kind"] == "PAD" and not any(o["drill_mm"])
               for layer, ps in o["layers"].items() if layer in ("F.Cu", "B.Cu") and ps]
        gap = min(Point(via["position_mm"]).distance(g)-.15 for g in smd)
        accepted = receiving.accepts(updated)
        results.append(dict(proposed_poses=updated, receiving_screen_passed=accepted,
                            foreign_copper_collisions=collisions, relocated_ground_via_screen_passed=legal_via,
                            minimum_proposed_drill_edge_to_SMD_mm=round(gap, 9),
                            preliminary_space_screen_passed=accepted and not collisions and legal_via and gap >= .16))
    for row in results:
        if row["preliminary_space_screen_passed"]:
            print("Viable near-root placement", row["proposed_poses"], flush=True)
    verify_hashes(before)
    report = dict(source_sha256=before, proposed_private_copper_to_move=sorted(PRIVATE),
                  old_source_entries_requiring_replacement=sorted(OLD_ENTRIES), proposals=results,
                  intended_moved_AGND_spurs_excluded_from_new_drill_obstacle_test=True,
                  receiving_is_a_geometric_screen_only=True, source_connections_restored=False,
                  whole_unit_mating_height_and_harness_qualified=False, native_candidate_emitted=False,
                  fabrication_released=False)
    dest.write_text(json.dumps(report, indent=2)+"\n")
    print("Unused-space options:", sum(r["preliminary_space_screen_passed"] for r in results), "/", len(results), "; no board emitted")


if __name__ == "__main__":
    run()
