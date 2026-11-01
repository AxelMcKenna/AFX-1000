"""Fresh successor: four exact via joints and one missing WDO layer change."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "receiving-continuation-01"
WORK = ROOT / "receiving-continuation-repair-01"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    WORK.mkdir(exist_ok=False)
    source = SOURCE / "output.kicad_pcb"
    before = sha(source)
    b = pcbnew.LoadBoard(str(source))
    by = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
    drc = json.loads((SOURCE / "output-drc.json").read_text())
    edits = []
    for finding in drc["violations"]:
        if finding["type"] != "track_not_centered_on_via":
            assert finding["type"] == "track_dangling"
            continue
        t, v = [by[i["uuid"]] for i in finding["items"]]
        assert not t.IsLocked() and isinstance(v, pcbnew.PCB_VIA) and v.IsLocked()
        q = v.GetPosition()
        candidates = []
        for which, p in [("start", t.GetStart()), ("end", t.GetEnd())]:
            if max(abs(p.x-q.x), abs(p.y-q.y)) <= 500:
                candidates.append((which, [p.x, p.y]))
        assert len(candidates) == 1 and t.GetNetname() == v.GetNetname()
        which, old = candidates[0]
        edits.append(dict(track_uuid=t.m_Uuid.AsString(), endpoint=which,
                          old_nm=old, new_nm=[q.x, q.y]))
        (t.SetStart if which == "start" else t.SetEnd)(q)
    assert len(edits) == 4
    # Native report exposes two open ends on opposite faces at the same point.
    # There is no via in the saved SES or PCB at that point. Add one explicitly;
    # all-layer native clearance/physical-hole checks must accept it afterward.
    a = by["d7de6b15-b43f-4d58-a578-f832a119616c"]
    z = by["946cbcd1-2722-43dc-a99a-f31250bd40d5"]
    assert a.GetNetname() == z.GetNetname() == "/N12_WDO"
    assert a.GetLayer() == pcbnew.F_Cu and z.GetLayer() == pcbnew.B_Cu
    assert a.GetEnd() == z.GetEnd()
    p = a.GetEnd()
    via = pcbnew.PCB_VIA(b)
    via.SetPosition(p)
    via.SetWidth(pcbnew.FromMM(.65))
    via.SetDrill(pcbnew.FromMM(.3))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(a.GetNet())
    via.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
    via.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
    b.Add(via)
    output = WORK / "output.kicad_pcb"
    pcbnew.SaveBoard(str(output), b)
    for name in ["output.kicad_pro", "output.kicad_sch", "fp-lib-table"]:
        shutil.copyfile(SOURCE / name, WORK / name)
    assert sha(source) == before
    (WORK / "construction.json").write_text(json.dumps(dict(
        source_PCB_sha256=before, source_DRC_sha256=sha(SOURCE / "output-drc.json"),
        source_script_sha256=sha(Path(__file__)), output_PCB_sha256=sha(output),
        four_new_router_endpoint_centers=edits,
        new_conventional_tented_WDO_via=dict(at_nm=[p.x, p.y], diameter_mm=.65, drill_mm=.3),
        all_component_poses_and_protected_seed_copper_unchanged=True,
        native_DRC_and_uncapped_connectivity_required=True,
        physical_qualified=False, fabrication_released=False), indent=2) + "\n")


if __name__ == "__main__":
    main()
