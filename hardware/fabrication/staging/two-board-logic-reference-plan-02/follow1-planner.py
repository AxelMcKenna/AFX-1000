import sys,json,math,types,inspect,textwrap
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.fabrication.integrate_two_board_signal import STAGING
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
c=json.loads((STAGING/'two-board-power-routing-inputs-2294-startup-logic-02/capture.json').read_text());r=json.loads((STAGING/'two-board-power-startup-logic-native-02/startup-logic-routing.json').read_text());pg=json.loads(Path('/private/tmp/logic-reference-pg1-route.json').read_text())
labels={'FOLLOW1 gate output to eFuse enable','FOLLOW1 gate output to eFuse enable surface transition'};old=[x for x in r['routes'] if x.get('label') in labels];oldvia=next(v for v in r['vias'] if (v['ref'],v['pin'])==('E_R108','1'));ret={u for x in old+[pg['retired_route']] for u in x['segment_uuids']}|{oldvia['uuid']}
objects=[o for o in c['objects'] if o['uuid'] not in ret];routing.SIGNAL_LAYERS=tuple(c['copper_layers']);screen=ViaScreen(dict(c,objects=objects,zones=[]))
q=json.loads((STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())['quiet_ground_islands'];qids={u for x in q for u in x['zone_uuids']}
net=old[0]['net'];start=next(o['position_mm'] for o in objects if o['kind']=='PCB_VIA' and o['net']==net and o['position_mm']==[135.54,119.225]);source=next(x['path_mm'][0] for x in old if x['layer']=='In2.Cu')
for z in c['zones']:
 if z['net']!='PWR_AGND':screen.geometry[z['layer']].append((z['net'],routing.shape(z['polygons']),.31))
 if z['uuid'] in qids:
  if z['layer']=='In6.Cu':screen.geometry['B.Cu'].append(('QUIET_REFERENCE_RESERVE',routing.shape(z['authored_outline']).buffer(.35).difference(Point(start).buffer(.515)),0))
  if z['layer']=='In1.Cu':screen.geometry['In2.Cu'].append(('QUIET_REFERENCE_RESERVE',routing.shape(z['authored_outline']).buffer(.35),0))
screen.trees={l:STRtree([g for n,g,d in rows]) for l,rows in screen.geometry.items()}
for route in pg['routes']:screen.added.append((route['net'],route['layer'],LineString(route['path_mm'])))
for v in pg['vias']:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
method=textwrap.dedent(inspect.getsource(routing.Screen.grid_path)).replace('min(u, v)-50','min(u, v)-100').replace('max(u, v)+50','max(u, v)+100');ns=dict(routing.__dict__);exec(method,ns);screen.grid_path=types.MethodType(ns['grid_path'],screen)
quiet=[routing.shape(z['authored_outline']) for z in c['zones'] if z['uuid'] in qids]
choices=[];legal_sites=[]
for d,xy in sorted((math.dist(start,(ix*.5,iy*.5)),(ix*.5,iy*.5)) for ix in range(252,269) for iy in range(247,269)):
 if not screen.via_legal(net,xy) or any(Point(xy).distance(g)<.65 for g in quiet):continue
 if any(z['net']!='PWR_AGND' and z['layer']=='In2.Cu' and Point(xy).distance(routing.shape(z['authored_outline']))<.65 for z in c['zones']):continue
 legal_sites.append((d,xy))
 path=screen.simple(net,'B.Cu',start,xy,20)
 if path:choices.append((path[0],xy,path[1]))
 if len(choices)>=12:break
if not choices:
 for d,xy in legal_sites[:16]:
  path=screen.grid_path(net,'B.Cu',start,xy,budget=40000)
  if path and LineString(path).length<20:choices.append((LineString(path).length,xy,path))
  if len(choices)>=4:break
print('CHOICES',[(round(d,3),xy) for d,xy,path in choices],flush=True)
result=None
for d,xy,path in sorted(choices):
 inner=screen.simple(net,'In2.Cu',source,xy,45)
 if inner:inner=inner[1]
 else:inner=screen.grid_path(net,'In2.Cu',source,xy,budget=100000)
 if not inner:continue
 result=dict(retired_routes=old,retired_via=oldvia,routes=[dict(label='FOLLOW1 gate output to eFuse enable',net=net,layer='In2.Cu',width_mm=.2,path_mm=inner),dict(label='FOLLOW1 gate output to eFuse enable surface transition',net=net,layer='B.Cu',width_mm=.2,path_mm=path)],vias=[dict(ref='E_U16',pin='1',net=net,position_mm=xy,size_mm=.6,drill_mm=.3)],native_validation_pending=True);break
assert result
Path('/private/tmp/logic-reference-follow1-route.json').write_text(json.dumps(result,indent=2));print('RESULT',result['routes'],flush=True)
