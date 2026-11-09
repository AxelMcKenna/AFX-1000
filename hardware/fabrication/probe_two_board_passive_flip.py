"""Read-only in-memory probe of native KiCad passive flipping."""
import json
import pcbnew
from hardware.fabrication.integrate_two_board_signal import STAGING
b=pcbnew.LoadBoard(str(STAGING/'two-board-power-digital-distribution-native-02/power_protection.kicad_pcb'))
for ref in ['E_R110','E_C47']:
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
 def state():return dict(angle=f.GetOrientationDegrees(),layer=b.GetLayerName(f.GetLayer()),pads=[(p.GetNumber(),pcbnew.ToMM(p.GetPosition().x),pcbnew.ToMM(p.GetPosition().y)) for p in f.Pads()])
 before=state();angle=f.GetOrientationDegrees();f.Flip(f.GetPosition(),False);f.SetOrientationDegrees(angle)
 print(json.dumps(dict(ref=ref,before=before,after=state())))
