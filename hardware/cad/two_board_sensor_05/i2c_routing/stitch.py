"""Add local through-ground stitches at each I2C layer transition; preserve r3."""
import json,math,uuid,hashlib
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
R=Path(__file__).resolve().parent;c=json.loads((R/'capture-after-r3/capture.json').read_text())
foreign=unary_union([shape(ps)for o in c['objects']if o['net']!='LINK_AGND' for ps in o['layers'].values()if ps])
refs={l:unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND' and z['layer']==l])for l in ['In4.Cu','In6.Cu']}
transitions=[('J402.3',[175,87]),('J402.4',[175,84.5]),('SCLvia',[189.160625,83.70625]),('SDAvia',[188.5,68.9])]
t=read_sexpr((R/'candidate-r3/signal_main.kicad_pcb').read_text());rows=[]
for name,xy in transitions:
 candidates=sorted(([xy[0]+i*.1,xy[1]+j*.1]for i in range(-20,21)for j in range(-20,21)),key=lambda p:math.dist(p,xy))
 for p in candidates:
  pt=Point(p)
  if pt.distance(foreign)<.51:continue
  if any(o['kind']=='PCB_VIA'and math.dist(p,o['position_mm'])<.86 for o in c['objects']):continue
  if not all(v.covers(pt.buffer(.31))for v in refs.values()):continue
  if any(math.dist(p,r['at'])<.86 for r in rows):continue
  break
 else:raise RuntimeError(name)
 uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH05-I2C-return-'+name))
 t.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),'LINK_AGND'],[a('uuid'),uid]])
 rows.append({'transition':name,'signal_at':xy,'at':p,'distance_mm':math.dist(p,xy),'uuid':uid,'size_mm':.6,'drill_mm':.3,'layers':['F.Cu','B.Cu']})
o=R/'candidate-r4';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');r=json.loads((R/'candidate-r3/routing.json').read_text());r['return_stitches']=rows;r['source_sha256_stitch']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r3/signal_main.kicad_pcb',R/'capture-after-r3/capture.json']};(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rows,indent=2))
