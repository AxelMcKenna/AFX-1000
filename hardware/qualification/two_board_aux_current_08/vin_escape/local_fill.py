"""Insert only the recorded native antipad using exact repeated bridge vertices."""
import json,copy
from shapely.geometry import Polygon,Point,LineString
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,Atom
from .verify import H,SRC,nmshape,shape,EXPECTED,VIN
from ..routed.plan import sha

def build():
 tree=read_sexpr((H/'native-01/authored.kicad_pcb').read_text());g=json.loads((H/'native-01/geometry.json').read_text());new={z['uuid']:z for z in g['zones']};c=json.loads((SRC/'capture-01/capture.json').read_text());old={z['uuid']:z for z in c['zones']};report=[]
 for z in children(tree,'zone'):
  u=first(z,'uuid')[1]
  if u not in EXPECTED:continue
  ng=nmshape(new[u]['polygons_nm']);parts=list(ng.geoms) if hasattr(ng,'geoms') else [ng];holes=[list(r.coords)[:-1] for p in parts for r in p.interiors if Polygon(r).covers(Point(VIN))];assert len(holes)==1;hole=holes[0];allowed=shape(old[u]['polygons']);found=False
  for fp in children(z,'filled_polygon'):
   pts=first(fp,'pts');xy=[[float(v[1]),float(v[2])] for v in pts[1:]]
   if not Polygon(xy).buffer(0).covers(Point(VIN)):continue
   candidates=sorted((Point(a).distance(Point(b)),i,j) for i,a in enumerate(xy) for j,b in enumerate(hole))
   for _,i,j in candidates:
    line=LineString([xy[i],hole[j]])
    if line.difference(allowed).length>1e-9:continue
    # Hole runs opposite to the containing contour.
    area=lambda ps:sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ps,ps[1:]+ps[:1]))
    h=hole[j:]+hole[:j]
    if area(xy)*area(h)>0:h=[h[0]]+list(reversed(h[1:]))
    additions=h+[h[0],xy[i]]
    pts[i+2:i+2]=[[Atom('xy'),Atom(format(a,'.9f')),Atom(format(b,'.9f'))] for a,b in additions]
    found=True;report.append({'zone':u,'bridge_mm':[xy[i],h[0]],'hole_points':len(h)});break
   if found:break
  assert found,u
 out=H/'local-antipads.kicad_pcb';out.write_text(sexpr(tree)+'\n');(H/'local-antipads.json').write_text(json.dumps({'script_sha256':sha(H/'local_fill.py'),'board_sha256':sha(out),'bridges':report},indent=2)+'\n')
if __name__=='__main__':build()
