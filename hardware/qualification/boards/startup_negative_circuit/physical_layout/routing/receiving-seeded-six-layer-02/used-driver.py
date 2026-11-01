"""Combine four-cap MCAD repair with the native-clean partial routed trial."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "centered-seeded-six-layer"
WORK = ROOT / "receiving-seeded-six-layer-02"
TARGET = ROOT.parent / "receiving_repair"
REFS = {"C4", "C5", "C31", "C32"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    WORK.mkdir(exist_ok=False)
    source = SOURCE / "output.kicad_pcb"
    before = sha(source)
    b = pcbnew.LoadBoard(str(source))
    target = pcbnew.LoadBoard(str(TARGET / "negative_startup_physical.kicad_pcb"))
    targets = {f.GetReference(): f for f in target.GetFootprints()}
    moves = []
    endpoints = []
    for f in b.GetFootprints():
        t = targets[f.GetReference()]
        assert f.GetValue() == t.GetValue() and f.IsFlipped() == t.IsFlipped()
        assert str(f.GetFPIDAsString()) == str(t.GetFPIDAsString())
        assert abs((f.GetOrientationDegrees() - t.GetOrientationDegrees() + 180) % 360 - 180) < 1e-9
        if f.GetReference() not in REFS:
            assert f.GetPosition() == t.GetPosition()
            continue
        old_pads = {p.GetNumber(): p.GetPosition() for p in f.Pads()}
        assert t.GetPosition().x == f.GetPosition().x
        assert t.GetPosition().y - f.GetPosition().y == pcbnew.FromMM(.6)
        f.SetPosition(t.GetPosition())
        new_pads = {p.GetNumber(): p for p in f.Pads()}
        for number, old in old_pads.items():
            new = new_pads[number]
            hits = []
            for track in b.GetTracks():
                if isinstance(track, pcbnew.PCB_VIA) or track.GetLayer() != pcbnew.B_Cu:
                    continue
                # The original literal planner's mm→nm conversion left one
                # C32.2 endpoint 1nm from its native pad center. Match at most
                # that single native coordinate unit; record and snap exactly.
                near_start = max(abs(track.GetStart().x-old.x), abs(track.GetStart().y-old.y)) <= 1
                near_end = max(abs(track.GetEnd().x-old.x), abs(track.GetEnd().y-old.y)) <= 1
                if near_start or near_end:
                    assert track.GetNetname() == new.GetNetname()
                    end = "start" if near_start else "end"
                    actual = track.GetStart() if near_start else track.GetEnd()
                    (track.SetStart if end == "start" else track.SetEnd)(new.GetPosition())
                    hits.append(dict(uuid=track.m_Uuid.AsString(), endpoint=end, locked=track.IsLocked(),
                                     actual_old_endpoint_nm=[actual.x, actual.y],
                                     native_pad_delta_nm=[actual.x-old.x, actual.y-old.y]))
            assert hits, (f.GetReference(), number)
            endpoints.append(dict(ref=f.GetReference(), pin=number, before_nm=[old.x, old.y],
                                  after_nm=[new.GetPosition().x, new.GetPosition().y], tracks=hits))
        moves.append(f.GetReference())
    assert set(moves) == REFS
    output = WORK / "output.kicad_pcb"
    pcbnew.SaveBoard(str(output), b)
    for name in ["output.kicad_pro", "output.kicad_sch", "fp-lib-table"]:
        shutil.copyfile(SOURCE / name, WORK / name)
    assert sha(source) == before
    (WORK / "construction.json").write_text(json.dumps(dict(
        source_PCB_sha256=before, receiving_target_sha256=sha(TARGET / "negative_startup_physical.kicad_pcb"),
        output_PCB_sha256=sha(output), source_script_sha256=sha(Path(__file__)),
        changed_component_refs=sorted(moves), changed_B_Cu_endpoints=endpoints,
        all_other263_complete_poses_preserved=True,
        native_DRC_and_uncapped_connectivity_required=True,
        physical_qualified=False, PDN_qualified=False, fabrication_released=False), indent=2) + "\n")


if __name__ == "__main__":
    main()
