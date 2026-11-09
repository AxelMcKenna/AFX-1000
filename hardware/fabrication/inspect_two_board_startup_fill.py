"""Inspect unexpected fill changes in the first startup candidate, without editing it."""
import json,sys
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.capture_partial_board import polygons
from hardware.fabrication.fill_two_board_power_zones_v2 import canonical

def run():
 assert sys.platform=='linux'
 import pcbnew
 base=STAGING/'two-board-power-digital-startup-01/power_protection.kicad_pcb'
 filled=STAGING/'two-board-power-digital-startup-filled-01/native-zone-export.kicad_pcb'
 paths=[Path(__file__),base,filled,REPO/'hardware/fabrication/capture_partial_board.py',REPO/'hardware/fabrication/fill_two_board_power_zones_v2.py'];records=[]
 b0,b1=[pcbnew.LoadBoard(str(p)) for p in [base,filled]];z1={z.m_Uuid.AsString():z for z in b1.Zones()}
 for z in b0.Zones():
  p0=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()))
  if not p0.OutlineCount():continue
  p1=pcbnew.SHAPE_POLY_SET(z1[z.m_Uuid.AsString()].GetFilledPolysList(z.GetLayer()));p0.Unfracture();p1.Unfracture()
  before,after=polygons(p0),polygons(p1)
  records.append(dict(uuid=z.m_Uuid.AsString(),layer=b0.GetLayerName(z.GetLayer()),net=z.GetNetname(),canonical_match=canonical(before)==canonical(after),before=before,after=after))
 out=filled.parent/'unexpected-fill-delta.json'
 with out.open('x') as f:json.dump(dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},zones=records),f)
 print(json.dumps([dict(uuid=r['uuid'],layer=r['layer'],net=r['net']) for r in records if not r['canonical_match']]))
if __name__=='__main__':run()
