"""Rejected-design diagnostic only: quantify native via reference cutback, not a candidate."""
import sys,json,hashlib
from pathlib import Path
assert sys.platform=='linux'
import pcbnew
from hardware.fabrication.capture_partial_board import polygons
R=Path(__file__).resolve().parent;O=R/'native-probe-r138-recapture';source=R/'native-r131/signal_main.kicad_pcb'
assert O.is_dir() and not list(O.iterdir())
b=pcbnew.LoadBoard(str(source));removed=['b1c1865b-7772-58be-ab73-298eb697dc74','094cfe15-e54e-5a1a-86f3-64eb7dd586b8','e278094b-72b0-5e04-90d5-578081219fd8']
def fields():
 rows=[]
 for z in b.Zones():
  if z.GetIsRuleArea():continue
  for lid in b.GetEnabledLayers().CuStack():
   if not z.IsOnLayer(lid):continue
   p=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(lid));p.Unfracture()
   rows.append({'uuid':z.m_Uuid.AsString(),'net':z.GetNetname(),'layer':b.GetLayerName(lid),'polygons':polygons(p)})
 return rows
before=fields()
b=pcbnew.LoadBoard(str(R/'native-probe-r138/diagnostic-only.kicad_pcb'))
out={'diagnostic_only':True,'not_acceptable_routing_candidate':True,'removed_without_replacement':removed,'via_mm':[75.8,77.65],'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [source,Path(__file__)]},'before':before,'after':fields()}
(O/'fields.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('Diagnostic native field capture complete',flush=True)
