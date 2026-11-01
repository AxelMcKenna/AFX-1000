import pcbnew,json,hashlib
from pathlib import Path
R=Path('/private/tmp/afx-e28-ana-pg1-follow2');p=R/'source-parent/rail_disconnect.kicad_pcb';b=pcbnew.LoadBoard(str(p));f=next(f for f in b.GetFootprints() if f.GetReference()=='C84');f.SetOrientationDegrees(270);f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(162.8),pcbnew.FromMM(152.4)));rows=[]
for q in f.Pads():rows.append(dict(pin=q.GetNumber(),net=q.GetNetname(),xy_mm=[pcbnew.ToMM(q.GetPosition().x)-100,pcbnew.ToMM(q.GetPosition().y)-100],absolute_orientation_degrees=q.GetOrientationDegrees(),size_mm=[pcbnew.ToMM(q.GetSize().x),pcbnew.ToMM(q.GetSize().y)]))
pcbnew.SaveBoard(str(R/'c84-vertical-native.kicad_pcb'),b)
(R/'c84-vertical-native-pads.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pad_contract=rows,no_original_board_written=True),indent=2)+'\n');print(rows)
