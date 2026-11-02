"""Apply the source-bound two start-delay capacitor placement plan in isolated KiCad."""
import json
import sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha,native_evidence_errors


def run():
    assert sys.platform=='linux'
    import pcbnew
    root=Path(__file__).resolve().parent
    source=root/'staging/nf-ct-local-native-01';project=source/'negative_startup_physical.kicad_pro'
    assert not native_evidence_errors(project,json.loads((source/'review.json').read_text()))
    plan_path=root/'staging/nf-timing-placement-search-03/plan.json';plan=json.loads(plan_path.read_text())
    assert all(sha(Path(p))==h for p,h in plan['source_sha256'].items())
    pcb=project.with_suffix('.kicad_pcb');board=pcbnew.LoadBoard(str(pcb));fps={f.GetReference():f for f in board.GetFootprints()}
    rows=[]
    for row in plan['placements']:
        row=row['selected'];fp=fps[row['ref']];assert not fp.IsFlipped()
        fp.Flip(fp.GetPosition(),False)
        fp.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(v) for v in row['anchor_mm']]))
        fp.SetOrientationDegrees(row['rotation_deg'])
        pads={p.GetNumber():p for p in fp.Pads()};owner={p.GetNumber():p for p in fps[row['owner']].Pads()}
        assert pads['1'].GetNetname()==owner[row['owner_timing_pin']].GetNetname() and pads['2'].GetNetname()==owner[row['owner_reference_pin']].GetNetname()
        actual={str(pin):[pads[str(pin)].GetPosition().x/1e6,pads[str(pin)].GetPosition().y/1e6] for pin in [1,2]}
        rows.append(dict(plan=row,native_pad_positions_mm=actual))
    remove={t['uuid'] for row in plan['placements'] for t in row['selected']['displaced_logic_tracks']}
    removed=[]
    for track in list(board.GetTracks()):
        if track.m_Uuid.AsString() in remove:
            removed.append(dict(uuid=track.m_Uuid.AsString(),net=track.GetNetname()))
            board.Remove(track)
    assert len(removed)==len(remove)
    output=root/'staging/nf-start-delay-placement-01';output.mkdir(exist_ok=False)
    pcbnew.SaveBoard(str(output/pcb.name),board)
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,project,plan_path,Path(__file__)]},placements=rows,removed_logic_tracks=removed,
        native_review_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Moved',len(rows),'CT caps; removed',len(removed),'explicitly identified logic segments for local repair')


if __name__=='__main__':run()
