"""Separate native rear-placement trial for the two watchdog timing capacitors.

No circuit changes. Fresh routing, receiving and native review are mandatory.
"""
import json
import sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha, native_evidence_errors


def run():
    assert sys.platform == 'linux', 'Native Mac CAD remains disabled'
    import pcbnew
    root = Path(__file__).resolve().parent
    source = root/'staging/nf-six-net-native-01'
    project = source/'negative_startup_physical.kicad_pro'
    report = json.loads((source/'review.json').read_text())
    assert not native_evidence_errors(project, report)
    pcb = project.with_suffix('.kicad_pcb')
    output = root/'staging/nf-watchdog-placement-01'
    output.mkdir(exist_ok=False)
    board = pcbnew.LoadBoard(str(pcb))
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    rows=[]
    for ref,owner,x,y,angle in [('C1','U3',6.,27.5,180),('C2','U9',143.75,10.25,90)]:
        fp=fps[ref]
        old=dict(position_mm=[fp.GetPosition().x/1e6,fp.GetPosition().y/1e6],angle=fp.GetOrientationDegrees(),layer=board.GetLayerName(fp.GetLayer()))
        assert not fp.IsFlipped()
        fp.Flip(fp.GetPosition(),False)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(angle)
        pads={p.GetNumber():p for p in fp.Pads()}
        target=next(p for p in fps[owner].Pads() if p.GetNumber()=='2')
        assert pads['1'].GetNetname()==target.GetNetname()
        distance=(pads['1'].GetPosition()-target.GetPosition()).EuclideanNorm()/1e6
        rows.append(dict(ref=ref,owner=owner,before=old,anchor_mm=[x,y],rotation_deg=angle,side='B',native_pin_distance_mm=distance,
                         pads=[dict(pin=p.GetNumber(),net=p.GetNetname(),position_mm=[p.GetPosition().x/1e6,p.GetPosition().y/1e6]) for p in fp.Pads()]))
    pcbnew.SaveBoard(str(output/pcb.name),board)
    receipt=dict(source_sha256={str(pcb):sha(pcb),str(project):sha(project)},script_sha256=sha(Path(__file__)),placements=rows,
                 all_other_component_poses_and_authored_copper_intended_unchanged=True,
                 rear_complete_height_receiving_mm=1.9,carrier_X_bands_avoided_mm=[[33.55,42.45],[133.55,142.45]],
                 routing_complete=False,native_review_passed=False,whole_unit_receiving_qualified=False,fabrication_released=False)
    (output/'construction.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':
    run()
