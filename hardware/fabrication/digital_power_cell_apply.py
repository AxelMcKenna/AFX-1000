"""Apply the source-bound DC01 local-cell plan using isolated native KiCad."""
import json,sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'staging/digital-placement-native-05'
PLAN=ROOT/'staging/digital-power-cell-plan-01'
OUT=ROOT/'staging/digital-power-cell-placement-01'

def apply():
    assert sys.platform=='linux'
    import pcbnew
    pp=PLAN/'plan.json';data=json.loads(pp.read_text());assert all(sha(Path(p))==h for p,h in data['source_sha256'].items())
    pcb=SOURCE/'digital_core.kicad_pcb';board=pcbnew.LoadBoard(str(pcb));fps={f.GetReference():f for f in board.GetFootprints()}
    for row in data['IC_placements']:
        f=fps[row['ref']];f.SetOrientationDegrees(row['rotation_deg']);f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in row['anchor_mm']]))
    rows=[]
    for row in data['placements']:
        f=fps[row['ref']]
        if f.IsFlipped()!=(row['side']=='B'):f.Flip(f.GetPosition(),False)
        f.SetOrientationDegrees(row['rotation_deg']);f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in row['anchor_mm']]))
        target=next(p for p in fps[row['owner']].Pads() if p.GetNumber()==row['owner_pin']);pad=next(p for p in f.Pads() if p.GetNumber()=='1')
        assert pad.GetNetname()==target.GetNetname()
        dist=(pad.GetPosition()-target.GetPosition()).EuclideanNorm()/1e6
        assert abs(dist-row['planned_pin_distance_mm'])<.000003
        rows.append(dict(**row,native_pin_distance_mm=dist))
    OUT.mkdir(exist_ok=False);assert pcbnew.SaveBoard(str(OUT/pcb.name),board)
    (OUT/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,pp,Path(__file__)]},placements=rows,IC_placements=data['IC_placements'],
        native_review_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Applied',len(rows),'native local placements')

if __name__=='__main__':apply()
