"""Virtual relocation of only newly added C907; no board edit or route acceptance."""
import json,math
from pathlib import Path
from shapely.geometry import Point,box
from shapely.affinity import translate
from shapely.ops import unary_union
from ..routed.plan import shape,sha
from ..ldo_local.placement import courtyards
from hardware.electronics.common.sexpr import read_sexpr
H=Path(__file__).resolve().parent;c=json.loads((H/'capture-02/capture.json').read_text());board=H.parent/'ldo_local/inputs-local-return-08/power_protection.kicad_pcb';cs=courtyards(read_sexpr(board.read_text()));newcourt=translate(cs['P_C907'],-1,0);hits=[r for r,g in cs.items() if r!='P_C907' and g.intersects(newcourt)];removed=set(json.loads((H.parent/'ldo_local/native-07/review.json').read_text())['added_copper_uuids']);objects=[]
for o in c['objects']:
 if o['uuid'] in removed:continue
 gs={l:shape(g) for l,g in o['layers'].items()}
 if o.get('ref')=='P_C907':gs={l:translate(g,-1,0) for l,g in gs.items()}
 objects.append((o,gs))
rows=[]
for label,xy,net in [('IN',[186.6,125.8],'/P_power_supply/AUX_PREREG5'),('INreturn',[185.8,125.3],'PWR_AGND'),('EN',[193.6,128.5],'/P_power_supply/AUX_PREREG5'),('ENreturn',[192.9,129.0],'PWR_AGND')]:
 via=Point(xy).buffer(.3);conf=[];padguards=[]
 for o,gs in objects:
  d=min((via.distance(g) for g in gs.values()),default=999)
  if o['net']!=net and d<.2-1e-8:conf.append({'uuid':o['uuid'],'reference':o.get('ref'),'pin':o.get('pin'),'net':o['net'],'distance_mm':d})
  if o['kind']=='PAD' and len(gs)<3 and any(Point(xy).distance(g)<.3 for g in gs.values()):padguards.append(o['uuid'])
 rows.append({'label':label,'position_mm':xy,'net':net,'foreign_copper_conflicts':conf,'SMD_drill_guard_conflicts':padguards})
r={'source_board_sha256':sha(board),'capture_sha256':sha(H/'capture-02/capture.json'),'script_sha256':sha(Path(__file__)),'new_C907_center_mm':[186.5,126.6],'new_C907_courtyard_bounds_mm':list(newcourt.bounds),'courtyard_conflicts':hits,'vias':rows,'native_board_changed':False,'qualified':False};(H/'relocation-probe.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
