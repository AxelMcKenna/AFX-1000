"""Exact authored courtyard screen for the finite D101 placement family."""
import json,hashlib,math
from pathlib import Path
from shapely.geometry import LineString,box,Polygon,Point
from shapely.affinity import translate,rotate
from shapely.ops import unary_union,polygonize
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent;t=read_sexpr((R/'native-r107/signal_main.kicad_pcb').read_text());polys={};unsupported=[]
for fp in children(t,'footprint'):
 ref=next(x[2]for x in children(fp,'property')if x[1]=='Reference');at=list(map(float,first(fp,'at')[1:]));lines=[];filled=[]
 for row in fp:
  if not isinstance(row,list)or not children(row,'layer')or first(row,'layer')[1]!='B.CrtYd':continue
  if row[0]=='fp_line':lines.append(LineString([list(map(float,first(row,key)[1:]))for key in ['start','end']]))
  elif row[0]=='fp_rect':
   p,q=[list(map(float,first(row,key)[1:]))for key in ['start','end']];filled.append(box(min(p[0],q[0]),min(p[1],q[1]),max(p[0],q[0]),max(p[1],q[1])))
  else:unsupported.append((ref,row[0]));continue
 if not lines and not filled:continue
 g=unary_union([*filled,*polygonize(unary_union(lines))]);assert not g.is_empty,(ref,lines);g=rotate(g,-(at[2]if len(at)>2 else 0),origin=(0,0));polys[ref]=translate(g,xoff=at[0],yoff=at[1])
assert not unsupported,unsupported
source=json.loads((R/'pd-pose-screen-r114.json').read_text());rows=[];accepted=[]
for p in source['legal_pad_and_via_hypotheses']:
 g=translate(rotate(polys['A_D101'],p['world_rotation_degrees'],origin=(75,66)),xoff=p['translation_mm'][0],yoff=p['translation_mm'][1]);hits=[{'reference':ref,'overlap_mm2':g.intersection(other).area}for ref,other in polys.items()if ref!='A_D101'and g.intersection(other).area>1e-9];row={**p,'courtyard_bounds_mm':list(g.bounds),'courtyard_hits':hits};rows.append(row)
 if not hits:accepted.append(row)
result={'planning_only':True,'physical_source_board_unchanged':True,'source_courtyard_bounds_mm':list(polys['A_D101'].bounds),'screened_count':len(rows),'accepted':accepted,'all_cases':rows,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'pd-pose-screen-r114.json',R/'native-r107/signal_main.kicad_pcb']}};out=R/'pd-courtyard-r118.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print('PASS parsed',len(polys),'back courtyards; viable hypotheses',len(accepted));print(json.dumps(accepted[:8],indent=2))
