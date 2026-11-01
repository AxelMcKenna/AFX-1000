"""Actual KiCad geometry tests for raster guard and final assembly constraints."""

import json
from pathlib import Path

import numpy as np
import pcbnew

from hardware.qualification.boards.fan_health.composite.finish_grid import maskshape, mm, xy

ROOT = Path(__file__).resolve().parent
b = pcbnew.LoadBoard(str(ROOT / "fan_power_health.kicad_pcb"))
# The native compound BBox(clearance) ignored inflation in the rejected trial.
# This actual-pad fixture must retain clearance outside that uninflated box.
p = next(p for f in b.GetFootprints() if f.GetReference() == "R7" for p in f.Pads() if p.GetNumber() == "2")
s = p.GetEffectiveShape(pcbnew.F_Cu)
mask = np.zeros((661, 381), dtype=bool)
maskshape(mask, s, 0.32)
assert mask[401, 265] and mask[393, 273], "Lost explicit compound-bbox clearance guard"
assert s.Collide(xy(40.1, 26.5), mm(0.32))
vias = [t for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
assert vias and all(
    v.GetFrontTentingMode() == pcbnew.TENTING_MODE_TENTED
    and v.GetBackTentingMode() == pcbnew.TENTING_MODE_TENTED
    for v in vias
)
assert all(v.GetDrill() >= mm(0.3) and v.GetWidth(pcbnew.F_Cu) >= mm(0.65) for v in vias)
assert not [t for t in b.GetTracks() if not isinstance(t, pcbnew.PCB_VIA) and t.GetLayer() == pcbnew.In1_Cu]
b.BuildConnectivity()
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == "/GND":
            assert any(
                isinstance(t, pcbnew.ZONE) and t.GetLayer() == pcbnew.In1_Cu
                for t in b.GetConnectivity().GetConnectedItems(p)
            ), (f.GetReference(), p.GetNumber(), "Ground not attached to actual In1")
result = dict(
    native_compound_clearance_guard_regression=True,
    all_actual_GND_pads_connected_to_In1=True,
    through_vias=len(vias),
    minimum_finished_drill_mm=0.3,
    minimum_land_mm=0.65,
    all_vias_explicit_front_back_tented=True,
    In1_signal_tracks=0,
    physical_qualified=False,
)
(ROOT / "generated/native-geometry-checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
