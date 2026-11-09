"""Combine remaining startup cells with U20 access and U19 supply-pin repairs."""
import copy,json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.electronics.common.sexpr import children,read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,prop
from hardware.fabrication.route_two_board_buck_cell import position,transform_object,mechanical_check
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
CAP=STAGING/'two-board-power-routing-inputs-2199-startup-cells-03/capture.json'
BASE=STAGING/'two-board-power-startup-cells-native-03'
PLAN=STAGING/'two-board-startup-remaining-plan-03/plan.json'
U24=STAGING/'two-board-startup-u24-plan-02/plan.json'
OUT=STAGING/'two-board-startup-remaining-plan-04'


def run():
 assert not OUT.exists()
 c,p,u24=[json.loads(f.read_text()) for f in [CAP,PLAN,U24]]
 for d in [c,p,u24]:
  for n,h in d['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 assert not p['unresolved_detours']
 old={o['uuid']:o for o in c['objects']}
 for key in ['routes','vias','joins','cells']:p[key].extend(u24[key])
 p['moves'].update(u24['moves'])
 if u24['cells']:p['deferred']=[d for d in p['deferred'] if d['chip']!='E_U24']
 net='/E_rail_disconnect/E28_MASTER_ENABLE'
 pin=lambda ref,n:next(o for o in c['objects'] if o.get('ref')==ref and o.get('pin')==n)
 members=c['all_groups'][pin('E_U20','1')['group']]
 retire=[u for u in members if old[u]['kind']=='PCB_TRACK'];assert len(retire)==5
 p['retired_objects']=sorted(set(p['retired_objects'])|set(retire))
 routes=[dict(label='U20 enable pin3 escape',net=net,layer='B.Cu',width_mm=.2,path_mm=[[78.9,145.5],[78.5,145.]]),
         dict(label='U20 enable pin1 escape',net=net,layer='B.Cu',width_mm=.2,path_mm=[[78.95,146.5],[78.,147.]]),
         dict(label='U20 enable front bridge',net=net,layer='F.Cu',width_mm=.2,path_mm=[[78.5,145.],[78.,147.]]),
         dict(label='E_U20.2 return',net='PWR_AGND',layer='B.Cu',width_mm=.2,path_mm=[[78.9,146.],[77.5,146.]]),
         dict(label='U19 supply pins',net='PWR_V2V5_AUX',layer='B.Cu',width_mm=.2,path_mm=[[77.,155.4],[77.,156.6]])]
 p['routes'].extend(routes)
 for n,xy in [(net,[78.5,145.]),(net,[78.,147.]),('PWR_AGND',[77.5,146.])]:p['vias'].append(dict(net=n,position_mm=xy,size_mm=.6,drill_mm=.3))
 p['joins'].extend([dict(net='PWR_AGND',left=['E_U20','2'],right=['P_C103','2']),dict(net='PWR_V2V5_AUX',left=['E_U19','3'],right=['E_U19','4'])])
 next(x for x in p['cells'] if x['chip']=='E_U20')['ground_paths'].append(routes[3])
 p['deferred']=[d for d in p['deferred'] if d.get('pad')!='E_U20.2']
 fps={prop(f,'Reference')[2]:f for f in children(read_sexpr((BASE/'power_protection.kicad_pcb').read_text()),'footprint')}
 moved=dict(fps)
 for ref,(xy,rot,flip) in p['moves'].items():assert not flip;moved[ref]=rotate_footprint(fps[ref],xy,rot)
 placementpath=STAGING/'two-board-placement-05/capture.json';placement=json.loads(placementpath.read_text())
 for row in p['side_reconciliations']:next(x for x in placement['parts'] if x['id']==row['ref'])['side']=row['current_side']
 mechanical_check(moved,set(p['moves']),placement)
 objects=[]
 for o in c['objects']:
  if o['uuid'] in p['retired_objects']:continue
  if o.get('ref') in p['moves']:
   xy,rot,_=p['moves'][o['ref']];o=transform_object(o,position(fps[o['ref']]),xy,rot)
  objects.append(o)
 routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
 s=ViaScreen(dict(c,objects=objects,zones=[]))
 for r in p['routes']:
  assert s.legal(r['net'],r['layer'],r['path_mm']),r['label']
  s.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
 for v in p['vias']:
  assert s.via_legal(v['net'],v['position_mm']),v
  s.vias.append((v['net'],v['position_mm']))
 # Independent moved-pad clearance against all retained surface copper.
 for o in objects:
  if o.get('ref') not in p['moves']:continue
  for layer,ps in o['layers'].items():
   if layer not in ['F.Cu','B.Cu']:continue
   g=routing.shape(ps)
   for other in objects:
    if other.get('ref')==o['ref'] or other['net']==o['net'] or not other['layers'].get(layer):continue
    assert g.distance(routing.shape(other['layers'][layer]))>=.2-1e-6,(o['ref'],o['pin'],other['uuid'])
 p['expected_closed_connections']=len(p['joins'])
 p['source_sha256']={str(f.relative_to(REPO)):sha(f) for f in [Path(__file__),CAP,PLAN,U24,placementpath,BASE/'power_protection.kicad_pcb',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_layer_detours.py','route_two_board_buck_cell.py','repack_two_board_buck_input.py']],STAGING/'assembly-layout-04/allocation.json']}
 OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(p,indent=2)+'\n')
 print(json.dumps(dict(cells=len(p['cells']),joins=len(p['joins']),vias=len(p['vias']),retired=len(p['retired_objects']),deferred=p['deferred'])))


if __name__=='__main__':run()
