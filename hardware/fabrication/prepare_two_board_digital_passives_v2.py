"""Prepare fifteen passive poses using KiCad's own side/rotation transform."""
import json
from pathlib import Path
import pcbnew
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
BASE=STAGING/'two-board-power-digital-distribution-native-02'
PLAN=STAGING/'two-board-digital-cell-plan-02/placement.json'
OUT=STAGING/'two-board-digital-cell-native-poses-02'
b=pcbnew.LoadBoard(str(BASE/'power_protection.kicad_pcb'));d=json.loads(PLAN.read_text());fps={f.GetReference():f for f in b.GetFootprints()}
records=[]
for ref,(xy,rot,flip) in d['moves'].items():
 f=fps[ref];angle=f.GetOrientationDegrees()
 assert len(list(f.Pads()))==2 and all(not p.GetDrillSize().x and not p.GetDrillSize().y for p in f.Pads())
 if flip:f.Flip(f.GetPosition(),False)
 f.SetOrientationDegrees((angle+rot)%360);f.SetPosition(pcbnew.VECTOR2I(round(xy[0]*1e6),round(xy[1]*1e6)))
 records.append(dict(ref=ref,side=b.GetLayerName(f.GetLayer()),position_mm=xy,angle_degrees=f.GetOrientationDegrees(),pads=[dict(pin=p.GetNumber(),xy=[pcbnew.ToMM(p.GetPosition().x),pcbnew.ToMM(p.GetPosition().y)]) for p in f.Pads()]))
OUT.mkdir();path=OUT/'native-poses.kicad_pcb';pcbnew.SaveBoard(str(path),b)
report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),PLAN,BASE/'power_protection.kicad_pcb']},artifact_sha256={path.name:sha(path)},native_version=pcbnew.GetBuildVersion(),poses=records,only_declared_footprints_to_be_imported=True,fabrication_released=False)
(OUT/'poses.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(poses=len(records),flips=sum(v[2] for v in d['moves'].values()))))
