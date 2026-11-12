"""Independent all-pairs PCB interference and retained mounting-contract checks."""
import json,hashlib
from pathlib import Path
from shapely.geometry import Polygon,Point
from shapely.affinity import rotate,translate
R=Path(__file__).resolve().parent;REPO=R.parents[3];c=json.loads((R/'contract.json').read_text());boards={b['name']:b for b in c['boards']};captured=json.loads((REPO/'hardware/cad/two_board_print_01/capture.json').read_text());buttons={b[0]:b for b in captured['buttons']};solids=[];conflicts=[]
for i in c['instances']:
 b=boards[i['design']];assert b['mounts']==buttons[i['id']][8]
 p=Polygon(b['outline'],b['cutouts'])
 for xy in b['mounts']:p=p.difference(Point(*xy).buffer(1.2,quad_segs=24))
 x,y,a=i['pose'];p=translate(rotate(p,a,origin=(0,0)),xoff=x,yoff=y);solids.append((i['id'],p))
for n,(name,p) in enumerate(solids):
 for other,q in solids[n+1:]:
  a=p.intersection(q).area
  if a>1e-6:conflicts.append(dict(a=name,b=other,area=a))
d=dict(instances=len(solids),pairs=len(solids)*(len(solids)-1)//2,collisions=conflicts,scope='Actual source PCB polygons at installed poses; all mounting holes match retained holder contract',source_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'contract.json',Path(__file__),REPO/'hardware/cad/two_board_print_01/capture.json']});(R/'planar-review.json').write_text(json.dumps(d,indent=2)+'\n');print(d['pairs'],'pairs',len(conflicts),'collisions');assert not conflicts,conflicts
