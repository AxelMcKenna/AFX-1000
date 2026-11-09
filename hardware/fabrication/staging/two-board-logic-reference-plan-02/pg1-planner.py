import sys,json,copy,math,types,inspect,textwrap
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.fabrication.integrate_two_board_signal import STAGING
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
c=json.loads((STAGING/'two-board-power-routing-inputs-2294-startup-logic-02/capture.json').read_text());r=json.loads((STAGING/'two-board-power-startup-logic-native-02/startup-logic-routing.json').read_text())
old=next(x for x in r['routes'] if x.get('label')=='PG1 to Schmitt input');ret=set(old['segment_uuids']);objects=[o for o in c['objects'] if o['uuid'] not in ret]
routing.SIGNAL_LAYERS=tuple(c['copper_layers']);screen=ViaScreen(dict(c,objects=objects,zones=[]));q=json.loads((STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())['quiet_ground_islands']
qids={u for x in q for u in x['zone_uuids']};quiet=[routing.shape(z['authored_outline']) for z in c['zones'] if z['uuid'] in qids]
# Keep the entire In3 branch over space available for its In4 main return.
for z in c['zones']:
 if z['net']!='PWR_AGND':
  screen.geometry[z['layer']].append((z['net'],routing.shape(z['polygons']),.31))
  if z['layer']=='In4.Cu':screen.geometry['In3.Cu'].append((z['net'],routing.shape(z['authored_outline']),.45))
screen.trees={l:STRtree([g for n,g,d in rows]) for l,rows in screen.geometry.items()}
method=textwrap.dedent(inspect.getsource(routing.Screen.grid_path)).replace('min(u, v)-50','min(u, v)-100').replace('max(u, v)+50','max(u, v)+100');ns=dict(routing.__dict__);exec(method,ns);screen.grid_path=types.MethodType(ns['grid_path'],screen)
pad=next(o for o in objects if o.get('ref')=='E_R107' and o.get('pin')=='1');net=pad['net'];start=old['path_mm'][0];result=None
candidates=[]
for distance,xy in sorted((math.dist(pad['position_mm'],(ix*.5,iy*.5)),(ix*.5,iy*.5)) for ix in range(258,292) for iy in range(262,284)):
 if not screen.via_legal(net,xy) or any(Point(xy).distance(g)<.6 for g in quiet):continue
 if any(z['net']!='PWR_AGND' and z['layer'] in ['In3.Cu','In4.Cu'] and Point(xy).distance(routing.shape(z['authored_outline']))<.65 for z in c['zones']):continue
 path=screen.simple(net,'B.Cu',pad['position_mm'],xy,16)
 if path:candidates.append((path[0],xy,path[1]))
 if len(candidates)>=16:break
print('CANDIDATES',[(round(d,3),xy) for d,xy,p in candidates],flush=True)
for d,xy,path in sorted(candidates):
 inner=screen.simple(net,'In3.Cu',start,xy,45)
 if inner:inner=inner[1]
 else:inner=screen.grid_path(net,'In3.Cu',start,xy,budget=90000)
 if not inner:continue
 result=dict(retired_route=old,routes=[dict(label='PG1 to Schmitt input',net=net,layer='In3.Cu',width_mm=.2,path_mm=inner),dict(label='PG1 to Schmitt input surface transition',net=net,layer='B.Cu',width_mm=.2,path_mm=path)],vias=[dict(ref='E_R107',pin='1',net=net,position_mm=xy,size_mm=.6,drill_mm=.3)],native_validation_pending=True);break
assert result
Path('/private/tmp/logic-reference-pg1-route.json').write_text(json.dumps(result,indent=2));print('ROUTE',result['routes'],flush=True)
