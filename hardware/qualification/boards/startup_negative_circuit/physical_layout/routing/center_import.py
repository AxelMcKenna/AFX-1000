"""Fresh candidate: center only four rounded router joints on fixed seed vias."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "power-seeded-six-layer"
WORK = ROOT / "centered-seeded-six-layer"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    WORK.mkdir(exist_ok=False)
    source = SOURCE / "output.kicad_pcb"
    before = sha(source)
    b = pcbnew.LoadBoard(str(source))
    by = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
    edits = []
    for track_id, via_id, endpoint in [
        ("93ccefc2-7c05-4bf4-85a0-543ee4f129a9", "4c531253-203b-471d-a34c-cc9bd9a1096a", "end"),
        ("4eb634d4-daa6-4278-b9e8-90b083ff0736", "2413ed50-915a-41db-b8ad-8937b6a63933", "start"),
        ("9ecc21c7-2848-4cfa-bc4d-f54a2be5908c", "4c531253-203b-471d-a34c-cc9bd9a1096a", "end"),
    ]:
        t, v = by[track_id], by[via_id]
        assert not t.IsLocked() and v.IsLocked() and t.GetNetname() == v.GetNetname()
        p = t.GetStart() if endpoint == "start" else t.GetEnd()
        q = v.GetPosition()
        assert max(abs(p.x - q.x), abs(p.y - q.y)) <= 500
        edits.append(dict(track=track_id, endpoint=endpoint, before_nm=[p.x, p.y], after_nm=[q.x, q.y]))
        (t.SetStart if endpoint == "start" else t.SetEnd)(q)
    ids = ["cc2d7def-ea74-42f2-95ae-43359d09b07e", "fcf02142-7f28-40f8-9427-b85548a28ca9",
           "9e9f933d-29ca-48ec-aa96-9713c95bbf21", "7c124400-0781-4b61-bdd4-f369c8ea0710"]
    tracks = [by[i] for i in ids]
    v = by["fa1298bd-c7d3-4452-867f-9bbc43d6b054"]
    assert all(not t.IsLocked() and t.GetNetname() == v.GetNetname()
               and t.GetLayer() == pcbnew.In2_Cu for t in tracks)
    a, z = tracks[0].GetStart(), v.GetPosition()
    original = [dict(id=t.m_Uuid.AsString(), start_nm=[t.GetStart().x, t.GetStart().y],
                     end_nm=[t.GetEnd().x, t.GetEnd().y]) for t in tracks]
    for t in tracks:
        b.Remove(t)
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(a)
    t.SetEnd(z)
    t.SetLayer(pcbnew.In2_Cu)
    t.SetWidth(pcbnew.FromMM(.2))
    t.SetNet(v.GetNet())
    b.Add(t)
    edits.append(dict(replaced_four_new_router_segments=original,
                      new_start_nm=[a.x, a.y], new_end_nm=[z.x, z.y]))
    output = WORK / "output.kicad_pcb"
    pcbnew.SaveBoard(str(output), b)
    for name in ["output.kicad_pro", "output.kicad_sch", "fp-lib-table"]:
        shutil.copyfile(SOURCE / name, WORK / name)
    assert sha(source) == before
    (WORK / "construction.json").write_text(json.dumps(dict(
        source_PCB_sha256=before, output_PCB_sha256=sha(output),
        source_script_sha256=sha(Path(__file__)), edits=edits,
        all_seed_copper_and_component_poses_unchanged=True,
        native_DRC_connectivity_required=True, physical_qualified=False,
        fabrication_released=False), indent=2) + "\n")


if __name__ == "__main__":
    main()
