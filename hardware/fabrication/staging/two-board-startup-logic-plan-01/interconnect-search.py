import sys,copy,json,math
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString
from hardware.electronics.common.sexpr import first,children,read_sexpr
from hardware.fabrication.integrate_two_board_signal import STAGING,prop
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
p=json.loads(Path('/private/tmp/startup-logic-cells-v2.json').read_text())
c=json.loads((STAGING/'two-board-power-routing-inputs-2310-digital-startup-02/capture.json').read_text())
b=read_sexpr((STAGING/'two-board-power-digital-startup-native-02/power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(b,'footprint')}
objects=[]
for o in c['objects']:
 if o['uuid'] in p['retired_objects']:continue
 if o.get('ref') in p['moves']:
  xy,rot,_=p['moves'][o['ref']];o=transform_object(o,position(fps[o['ref']]),xy,rot)
 objects.append(o)
routing.SIGNAL_LAYERS=tuple(c['copper_layers']);screen=ViaScreen(dict(c,objects=objects,zones=[]))
# Include authored copper zones in trace screens. Vias may create ordinary
# antipads; ground contact ownership is screened separately before emission.
from shapely.strtree import STRtree
for z in c['zones']:
 if z['net']!='PWR_AGND':screen.geometry[z['layer']].append((z['net'],routing.shape(z['polygons']),.31))
screen.trees={l:STRtree([g for n,g,d in rows]) for l,rows in screen.geometry.items()}
routes=[copy.deepcopy(r) for cell in p['cells'] for r in cell['routes']]
vias=[copy.deepcopy(v) for cell in p['cells'] for v in cell['vias']]
for r in routes:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in vias:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
pads={(o.get('ref'),o.get('pin')):o for o in objects if o['kind']=='PAD'}
cellvias={(v['ref'],v['pin']):v for v in vias};new=[];extra=[];deferred=[]
def add(net,layer,path,label):
 r=dict(net=net,layer=layer,width_mm=.2,path_mm=path,label=label);new.append(r);screen.added.append((net,layer,LineString(path)));return r
def attach_via(ref,pin):
 o=pads[ref,pin];net=o['net'];layer=next(l for l in ['F.Cu','B.Cu'] if o['layers'].get(l))
 candidates=screen.escapes(net,layer,o['position_mm'])
 if not candidates:return
 length,xy,path=candidates[0];v=dict(ref=ref,pin=pin,net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
 extra.append(v);screen.vias.append((net,xy))
 for l in c['copper_layers']:screen.added.append((net,l,Point(xy).buffer(.2)))
 add(net,layer,path,f'{ref}.{pin} escape');return v
# Reserve the two fixed gate input escapes before routing the interconnects.
for key in [('E_U30','2'),('E_U34','1')]:
 v=attach_via(*key)
 if v:cellvias[key]=v;print('ESCAPE',key,v['position_mm'],flush=True)
 else:print('NO ESCAPE',key,flush=True);deferred.append(dict(label=str(key),reason='No legal fixed-pad escape'))
def connect(a,targets,label,layers=('In2.Cu','In3.Cu','In6.Cu'),maxlen=140):
 net=a['net'];options=[]
 for target in targets:
  if target['net']!=net:continue
  for layer in layers:
   if target.get('kind')=='PCB_VIA' or target.get('size_mm') or target.get('layers',{}).get(layer):options.append((math.dist(a['position_mm'],target['position_mm']),layer,target))
 for d,layer,t in sorted(options,key=lambda x:x[0]):
  path=screen.simple(net,layer,a['position_mm'],t['position_mm'],maxlen)
  if path:
   add(net,layer,path[1],label);print('JOIN',label,round(path[0],3),layer,flush=True);return dict(label=label,source=[a['ref'],a['pin']],target_uuid=t.get('uuid'),target=[t.get('ref'),t.get('pin')],net=net)
 for d,layer,t in sorted(options,key=lambda x:x[0])[:4]:
  path=screen.grid_path(net,layer,a['position_mm'],t['position_mm'],budget=18000)
  if path and LineString(path).length<=maxlen:
   add(net,layer,path,label);print('GRID JOIN',label,round(LineString(path).length,3),layer,flush=True);return dict(label=label,source=[a['ref'],a['pin']],target_uuid=t.get('uuid'),target=[t.get('ref'),t.get('pin')],net=net)
 print('DEFER',label,flush=True);deferred.append(dict(label=label,reason='No screened bounded interconnect'));return
joins=[]
def link(key,targets,label,maxlen=140):
 if key not in cellvias:return
 r=connect(cellvias[key],targets,label,maxlen=maxlen)
 if r:joins.append(r)
# Restore both relocated master-enable pins to their original physical group.
master=pads['E_U29','5']['net'];group=pads['E_U29','5']['group']
mastertargets=[o for o in objects if o['kind']=='PCB_VIA' and o.get('group')==group]
link(('E_U29','5'),mastertargets,'Restore U29 master-enable group')
link(('E_U29','7'),[cellvias['E_U29','5']],'Restore U29 local master-enable tie')
link(('E_U40','7'),[cellvias['E_U29','6']],'PG0 Schmitt output to follower gate')
for sp,tp in [('5',('E_U30','2')),('2',('E_U34','1'))]:
 if tp in cellvias:link(('E_U40',sp),[cellvias[tp]],f'PG{1 if sp=="5" else 2} Schmitt output to follower gate')
for key,label in [(('E_U29','3'),'FOLLOW1 gate output to eFuse enable'),(('E_U40','1'),'PG0 to Schmitt input'),(('E_U40','3'),'PG1 to Schmitt input'),(('E_U40','6'),'PG2 to Schmitt input')]:
 net=cellvias[key]['net'];link(key,[o for o in objects if o['kind']=='PCB_VIA' and o['net']==net],label)
# Source-backed AUX branch; local bypass alone does not power a device.
auxgrp=next(o['group'] for o in objects if o.get('ref')=='P_U103' and o.get('pin')=='5')
auxtarget=[o for o in objects if o['kind']=='PCB_VIA' and o.get('group')==auxgrp]
link(('E_U29','8'),auxtarget,'U29 AUX supply branch')
link(('E_U40','8'),[cellvias['E_U29','8']],'U40 AUX supply branch')
# Global input connection to an existing AUX_VALID connected group if it has
# a via; ALL_RAILS inputs remain reserved, not emitted as dangling fanouts.
valid=cellvias['E_U29','2']['net'];validtargets=[o for o in objects if o['kind']=='PCB_VIA' and o['net']==valid]
if validtargets:link(('E_U29','2'),validtargets,'AUX_VALID to master gate')
else:deferred.append(dict(label='AUX_VALID to master gate',reason='Needs a source-pad escape'))
Path('/private/tmp/startup-interconnects-v2.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2))
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
