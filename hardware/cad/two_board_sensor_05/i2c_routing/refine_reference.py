"""Place proposed control return at scheduled A_J402.1, avoiding rail-health pin7."""
import json,copy,hashlib
from pathlib import Path
from shapely.geometry import LineString,box,Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent;B=R/'candidate-r2';O=R/'candidate-r3';O.mkdir(exist_ok=False)
r=json.loads((B/'routing.json').read_text());t=read_sexpr((B/'signal_main.kicad_pcb').read_text())
field=unary_union([box(171,80,179,94),*[LineString(v['path_mm']).buffer(1,quad_segs=8)for v in r['routes']]])
assert field.geom_type=='Polygon' and not field.intersects(Point(175,77).buffer(1.1)) and field.contains(Point(175,92))
uids=['47aa40ce-420b-5cb2-b288-45607816b689','7174b53e-d6c3-5d96-88bf-06b6f6d225a4']
for z in children(t,'zone'):
 if first(z,'uuid')[1]not in uids:continue
 z[:]=[v for v in z if not(isinstance(v,list)and v and v[0]in ['filled_polygon','polygon'])]
 z.append([a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)]for x,y in list(field.exterior.coords)[:-1]]]])
r['ground_extension']={'layers':['In4.Cu','In6.Cu'],'net':'LINK_AGND','priority':1,'outer_mm':list(field.exterior.coords),'nominal_signal_corridor_width_mm':2,'control_return_landing_mm':[171,80,179,94],'audio_ground_attachment':{'ref':'A_J402','pin':'1','at_mm':[175,92]},'deliberately_excluded_rail_health_pad':'A_J402.7','source_candidate_sha256':hashlib.sha256((B/'signal_main.kicad_pcb').read_bytes()).hexdigest()}
(O/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(O/'routing.json').write_text(json.dumps(r,indent=2)+'\n')
