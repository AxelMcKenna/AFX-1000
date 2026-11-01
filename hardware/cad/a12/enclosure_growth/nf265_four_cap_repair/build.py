"""Captured NR01 successor with only four native-proved rear capacitor moves."""

import copy
import json
from pathlib import Path

from hardware.cad.a12.enclosure_growth.nf265_fpc91.capture import ROOT as PARENT
from hardware.cad.a12.enclosure_growth.nf265_fpc91.capture import sha, write
from hardware.cad.a12.enclosure_growth.nf265_fpc91.model import world_box
from hardware.cad.a12.enclosure_growth.nf265_fpc91.replay import stage
from hardware.electronics.common.sexpr import children, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
SOURCE = REPO / "hardware/qualification/boards/startup_negative_circuit/physical_layout/receiving_repair"
REFS = {"C4", "C5", "C31", "C32"}


def main():
    assert not (ROOT / "four-cap-model.json").exists(), "Never overwrite derived geometry"
    work = ROOT / "workspace"
    if work.exists():
        # A failed API-argument check stopped before any staged file changed.
        # Reuse only if the complete original replay closure is still exact.
        original = json.loads((work / "replay.json").read_text())
        assert "receiving_repair" not in original
        assert all(sha(Path(n)) == h for n, h in original["rebound_source_sha256"].items())
    else:
        stage(work)
    parent_model = PARENT / "tail_shape/model.json"
    model = json.loads(parent_model.read_text())
    before_boxes = copy.deepcopy(model["boxes"])
    tree = read_sexpr((SOURCE / "negative_startup_physical.kicad_pcb").read_text())
    fps = {next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
           for f in children(tree, "footprint")}
    proof = json.loads((SOURCE / "generated/construction.json").read_text())
    assert proof["all_other263_complete_identities_unchanged"]
    assert proof["parent_PCB_sha256"] == model["boards"][0]["source_PCB_sha256"]
    assert proof["output_PCB_sha256"] == sha(SOURCE / "negative_startup_physical.kicad_pcb")
    changed = []
    for row in model["boxes"]:
        ref = row[0].removeprefix("NF265_")
        if row[0].startswith("NF265_") and ref in REFS:
            old = list(row)
            bb = courtyard(fps[ref], "B.CrtYd")
            actual = world_box([172, 180.5, 3.5], bb, -3.66, -1.76)
            # Existing receiving box has1.9mm rear assembly extent, with no
            # new nominal height or pad/lead receiver adopted here.
            expected = old[1:]
            expected[2] += .6
            assert all(abs(a-b) < 1e-7 for a, b in zip(actual, expected)), (ref, actual, expected)
            row[1:] = actual
            changed.append(dict(ref=ref, old_box=old, new_box=list(row)))
    assert {r["ref"] for r in changed} == REFS
    replay_path = work / "replay.json"
    replay = json.loads(replay_path.read_text())
    original_replay = copy.deepcopy(replay)
    needle = "fr_boxes=" + json.dumps(before_boxes) + ";"
    replacement = "fr_boxes=" + json.dumps(model["boxes"]) + ";"
    edited = []
    for name, digest in list(replay["rebound_source_sha256"].items()):
        p = Path(name)
        assert sha(p) == digest
        if p.suffix == ".scad" and needle in p.read_text():
            text = p.read_text()
            assert text.count(needle) == 1
            p.write_text(text.replace(needle, replacement))
            replay["rebound_source_sha256"][name] = sha(p)
            edited.append(name)
    assert len(edited) == 1
    inputs = {}
    for name in ["negative_startup_physical.kicad_pcb", "placement.json", "generated/construction.json",
                 "generated/native-review.json"]:
        p = SOURCE / name
        h = sha(p)
        dst = ROOT / "inputs" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(p.read_bytes())
        assert sha(dst) == sha(p) == h
        inputs[str(p)] = h
    write(work / "staged-original-replay.json", original_replay)
    write(ROOT / "four-cap-model.json", dict(boxes=model["boxes"], tails=model["tails"], mates=model["mates"]))
    replay["receiving_repair"] = dict(
        changed_boxes=changed, modified_SCAD=edited,
        actual_new_native_inputs_sha256=inputs,
        original_model_sha256=sha(parent_model), source_script_sha256=sha(Path(__file__)),
        only_four_native_proved_cap_boxes_shifted=True,
        all_other_boxes_tails_mates_and_allowances_preserved=True,
        physical_qualified=False, full_harness_qualified=False)
    write(replay_path, replay)
    print("Staged captured-only successor; four native cap moves, all other receiving geometry exact")


if __name__ == "__main__":
    main()
