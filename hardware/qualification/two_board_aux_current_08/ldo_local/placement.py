"""Exact existing courtyard polygons, including stepped MSOP courtyard."""
import json,math
from shapely.geometry import box,Point,LineString,Polygon
from shapely.ops import unary_union,polygonize
from shapely.affinity import rotate,translate
from hardware.electronics.common.sexpr import read_sexpr,children,first
from .screen import H,BASE,sha,shape

def courtyards(tree):
 out={}
 for f in children(tree,'footprint'):
  if first(f,'layer')[1]!='F.Cu':continue
  ref=next(p[2] for p in children(f,'property') if p[1]=='Reference');at=first(f,'at');angle=float(at[3]) if len(at)>3 else 0;geoms=[];lines=[]
  for tag in ['fp_line','fp_rect','fp_poly','fp_circle','fp_arc']:
   for e in children(f,tag):
    if first(e,'layer')[1]!='F.CrtYd':continue
    pair=lambda n:tuple(map(float,first(e,n)[1:3]))
    if tag=='fp_arc':raise AssertionError('Unsupported courtyard arc')
    if tag=='fp_line':lines.append(LineString([pair('start'),pair('end')]))
    elif tag=='fp_rect':a,b=pair('start'),pair('end');geoms.append(box(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
    elif tag=='fp_poly':geoms.append(Polygon([tuple(map(float,v[1:3])) for v in first(e,'pts')[1:]]))
    else:a,b=pair('center'),pair('end');geoms.append(Point(a).buffer(math.dist(a,b),quad_segs=128))
  if lines:
   ps=list(polygonize(unary_union(lines)));assert ps,ref;geoms+=ps
  g=unary_union(geoms) if geoms else Point(0,0).buffer(10)
  out[ref]=translate(rotate(g,-angle,origin=(0,0)),float(at[1]),float(at[2]))
 return out

def run():
 tree=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());cs=courtyards(tree);new=translate(box(-1.48,-.73,1.48,.73),187.5,126.6);hits=[r for r,g in cs.items() if g.intersects(new)];assert not hits,hits
 distances=sorted((g.distance(new),r) for r,g in cs.items());result={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'script_sha256':sha(H/'placement.py'),'reference':'P_C907','position_mm':[187.5,126.6],'orientation_degrees':180,'new_courtyard_bounds_mm':list(new.bounds),'exact_courtyard_conflicts':hits,'nearest_existing_courtyards_mm':distances[:5],'P_U102_stepped_courtyard_area_mm2':cs['P_U102'].area,'P_U102_bounding_box_area_mm2':box(*cs['P_U102'].bounds).area,'qualified':False};(H/'placement.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':run()
