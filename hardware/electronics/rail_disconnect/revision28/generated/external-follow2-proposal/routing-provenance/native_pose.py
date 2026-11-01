import pcbnew
from pathlib import Path
R=Path(__file__).parent;b=pcbnew.LoadBoard(str(R.parent/'source-parent/rail_disconnect.kicad_pcb'));f=next(f for f in b.GetFootprints() if f.GetReference()=='C84');f.SetOrientationDegrees(270);f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(163.3),pcbnew.FromMM(151.7)));pcbnew.SaveBoard(str(R/'posed-native.kicad_pcb'),b)
