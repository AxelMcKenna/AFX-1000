import sys,copy,json,math
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import first,children,read_sexpr
from hardware.fabrication.integrate_two_board_signal import STAGING,prop
from hardware.fabrication.route_two_board_buck_cell import position,transform_object
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
p=json.loads(Path('/private/tmp/startup-completion-cells-v2.json').read_text())
c=json.loads((STAGING/'two-board-power-routing-inputs-2294-logic-references-02/capture.json').read_text())
p['retired_objects']=sorted(set(p['retired_objects'])|{'56de9fc8-c0ab-533a-b77b-ce9173f82890','7ce905ff-c9cd-5579-b692-710f396ee77e','ba021f32-8b61-59fe-a8b2-8909faae1892','d7003052-2fc4-5192-b0b1-3d3c6eda4999'})
b=read_sexpr((STAGING/'two-board-power-logic-references-native-02/power_protection.kicad_pcb').read_text());fps={prop(f,'Reference')[2]:f for f in children(b,'footprint')}
objects=[]
for o in c['objects']:
 if o['uuid'] in p['retired_objects']:continue
 if o.get('ref') in p['moves']:
  xy,rot,_=p['moves'][o['ref']];o=transform_object(o,position(fps[o['ref']]),xy,rot)
 objects.append(o)
routing.SIGNAL_LAYERS=tuple(c['copper_layers']);screen=ViaScreen(dict(c,objects=objects,zones=[]))
quiet=json.loads((STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())['quiet_ground_islands'];qids={u for q in quiet for u in q['zone_uuids']};qfields=[routing.shape(z['authored_outline']) for z in c['zones'] if z['uuid'] in qids]
for z in c['zones']:
 if z['net']!='PWR_AGND':screen.geometry[z['layer']].append((z['net'],routing.shape(z['polygons']),.31))
# In6 may carry a control route only if it avoids all quiet returns and
# preserves the adjacent reference area beneath retained bottom traces.
from shapely.ops import unary_union
ownholes={}
for o in objects:
 if o['kind']=='PCB_VIA':ownholes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
ownholes={n:unary_union(gs) for n,gs in ownholes.items()}
for z in c['zones']:
 if z['uuid'] in qids and z['layer']=='In6.Cu':screen.geometry['In6.Cu'].append((None,routing.shape(z['authored_outline']),.31))
for o in objects:
 if o['kind']=='PCB_TRACK' and o['net']!='PWR_AGND' and o['layers'].get('B.Cu'):
  g=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2)
  if o['net'] in ownholes:g=g.difference(ownholes[o['net']])
  if not g.is_empty:screen.geometry['In6.Cu'].append((None,g,.31))
for z in c['zones']:
 if z['uuid'] in qids and z['layer']=='In1.Cu':
  screen.geometry['In2.Cu'].append((None,routing.shape(z['authored_outline']),.31))
  screen.geometry['F.Cu'].append((None,routing.shape(z['authored_outline']),.31))
 if z['uuid'] in qids and z['layer']=='In6.Cu':screen.geometry['B.Cu'].append((None,routing.shape(z['authored_outline']),.31))
 if z['layer']=='In4.Cu' and z['net']!='PWR_AGND':screen.geometry['In3.Cu'].append((None,routing.shape(z['authored_outline']),.31))
screen.trees={l:STRtree([g for n,g,d in rows]) for l,rows in screen.geometry.items()}
import types
from startup_fast_grid_v2 import fast_grid_path
screen.grid_path=types.MethodType(fast_grid_path,screen)
routes=[copy.deepcopy(r) for cell in p['cells'] for r in cell['routes']];vias=[copy.deepcopy(v) for cell in p['cells'] for v in cell['vias']]
# Reserve references beneath all new bottom fanouts and bypass joins.
newholes={}
for v in vias:newholes.setdefault(v['net'],[]).append(Point(v['position_mm']).buffer(.515))
for r in routes:
 if r['layer']!='B.Cu' or r['net']=='PWR_AGND':continue
 g=LineString(r['path_mm']).buffer(r['width_mm']/2)
 if r['net'] in newholes:g=g.difference(unary_union(newholes[r['net']]))
 if not g.is_empty:screen.geometry['In6.Cu'].append((None,g,.31))
screen.trees['In6.Cu']=STRtree([g for n,g,d in screen.geometry['In6.Cu']])
for r in routes:screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
for v in vias:
 screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
pads={(o.get('ref'),o.get('pin')):o for o in objects if o['kind']=='PAD'}
cellvias={(v['ref'],v['pin']):v for v in vias};new=[];extra=[];joins=[];deferred=[]
def add(net,layer,path,label):
 r=dict(net=net,layer=layer,width_mm=.2,path_mm=path,label=label);new.append(r);screen.added.append((net,layer,LineString(path)));return r
def viaadd(v):
 extra.append(v);screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
def inner_free(v,layer):
 if not all(z['net']==v['net'] or z['net']=='PWR_AGND' or z['layer']!=layer or Point(v['position_mm']).distance(routing.shape(z['polygons']))>.51 for z in c['zones']):return False
 xy=v['position_mm']
 return any(screen.legal(v['net'],layer,[xy,[xy[0]+dx,xy[1]+dy]]) for dx,dy in [(.1,0),(-.1,0),(0,.1),(0,-.1)])

def connect(a,targets,label,layers=('In2.Cu','In3.Cu','In6.Cu'),maxlen=180):
 net=a['net'];options=[]
 for target in targets:
  if target['net']!=net:continue
  for layer in layers:
   if not inner_free(a,layer) or not inner_free(target,layer):continue
   if target.get('kind')=='PCB_VIA' or target.get('size_mm') or target.get('layers',{}).get(layer):options.append((math.dist(a['position_mm'],target['position_mm']),layer,target))
 for d,layer,t in sorted(options,key=lambda x:x[0]):
  path=screen.simple(net,layer,a['position_mm'],t['position_mm'],maxlen)
  if path:
   add(net,layer,path[1],label);print('JOIN',label,round(path[0],3),layer,flush=True);return dict(label=label,source=[a.get('ref'),a.get('pin')],target_uuid=t.get('uuid'),target=[t.get('ref'),t.get('pin')],net=net)
 from startup_layer_hop import find_hop
 hop=find_hop(screen,a,targets,layers,inner_free,qfields,maxlen)
 if hop:
  t,v,legs=hop
  viaadd(v)
  for i,(layer,path) in enumerate(legs):add(net,layer,path,label+f' hop {i+1}')
  print('LAYER HOP',label,v['position_mm'],round(sum(LineString(path).length for layer,path in legs),3),flush=True)
  return dict(label=label,source=[a.get('ref'),a.get('pin')],target_uuid=t.get('uuid'),target=[t.get('ref'),t.get('pin')],net=net)
 for d,layer,t in sorted(options,key=lambda x:x[0])[:4]:
  print('SEARCH',label,layer,flush=True)
  path=screen.grid_path(net,layer,a['position_mm'],t['position_mm'],budget=45000)
  if path and LineString(path).length<=maxlen:
   add(net,layer,path,label);print('GRID JOIN',label,round(LineString(path).length,3),layer,flush=True);return dict(label=label,source=[a.get('ref'),a.get('pin')],target_uuid=t.get('uuid'),target=[t.get('ref'),t.get('pin')],net=net)
 return

def link(key,targets,label):
 a=cellvias[key];r=connect(a,targets,label)
 if r:joins.append(r);return True
 print('DEFER',label,flush=True);deferred.append(dict(label=label,source=list(key),reason='No screened inner interconnect'));return False

def attach(key):
 if key in cellvias:return cellvias[key]
 o=pads[key];net=o['net'];layer=next(l for l in ['F.Cu','B.Cu'] if o['layers'].get(l))
 for length,xy,path in screen.escapes(net,layer,o['position_mm']):
  if any(Point(xy).distance(q)<.6 for q in qfields):continue
  v=dict(ref=key[0],pin=key[1],net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
  if not any(inner_free(v,l) for l in ['In2.Cu','In3.Cu','In6.Cu']):continue
  viaadd(v);add(net,layer,path,f'{key[0]}.{key[1]} escape');cellvias[key]=v;print('ESCAPE',key,xy,flush=True);return v
 print('NO ESCAPE',key,flush=True)

def link_group(key,witness,label):
 a=cellvias[key];o=pads[witness];assert a['net']==o['net'];gid=o['group']
 ts=[t for t in objects if t.get('group')==gid and t['kind']=='PCB_VIA']
 for t in objects:
  if t.get('group')==gid and t['kind']=='PCB_TRACK':ts.extend([t,dict(t,position_mm=t['end_mm'])])
 r=connect(a,ts,label)
 if r:joins.append(r);return True
 # A supplied field may enclose all old inner transitions. Search surface
 # branches of the same native group for a fresh transition below the fields.
 anchors=[t for t in objects if t.get('group')==gid and t.get('ref') not in p['moves'] and (t['kind']=='PCB_VIA' or t['kind']=='PAD')]
 candidates=[]
 for target in sorted(anchors,key=lambda t:math.dist(t['position_mm'],a['position_mm']))[:4]:
  cent=target['position_mm'];net=a['net']
  for layer in ['B.Cu','F.Cu']:
   if not target['layers'].get(layer):continue
   for d,xy in sorted((math.dist(cent,(ix*.5,iy*.5)),(ix*.5,iy*.5)) for ix in range(int((cent[0]-12)*2),int((cent[0]+12)*2)+1) for iy in range(int((cent[1]-3)*2),int((cent[1]+16)*2)+1)):
    if d>16 or not screen.via_legal(net,xy) or any(Point(xy).distance(q)<.6 for q in qfields):continue
    v=dict(ref=witness[0],pin=witness[1],net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
    if not any(inner_free(v,l) for l in ['In2.Cu','In3.Cu']):continue
    path=screen.simple(net,layer,cent,xy,24)
    if path:candidates.append((path[0],v,layer,path[1],target['uuid']))
    if len(candidates)>=12:break
   if len(candidates)>=12:break
  if len(candidates)>=12:break
 for _,v,layer,path,targetid in sorted(candidates,key=lambda x:x[0]):
  r=connect(a,[v],label)
  if r:
   viaadd(v);add(a['net'],layer,path,label+' surface transition');r['target_uuid']=o['uuid'];r['target']=list(witness);r['surface_anchor_uuid']=targetid;joins.append(r);print('TRANSITION',label,v['position_mm'],flush=True);return True
 print('DEFER GROUP',label,flush=True);deferred.append(dict(label=label,source=list(key),target=list(witness),reason='No group transition and inner route'));return False

# Restore every prior connection before adding remaining startup functions.
link_group(('E_U30','2'),('E_U40','5'),'Restore U30 PG1 Schmitt input')
link_group(('E_U34','1'),('E_U40','2'),'Restore U34 PG2 Schmitt input')
link_group(('E_U34','2'),('E_U29','5'),'Restore U34 master group')
link(('E_U34','5'),[cellvias['E_U34','2']],'Restore U34 local master tie')
link(('E_U30','5'),[cellvias['E_U30','1']],'Restore U30 local master tie')
link_group(('E_U30','1'),('E_U29','5'),'Connect U30 master input')
# Restore the two pre-existing master branches previously bridged at U34.
a=dict(ref='E_U29',pin='5',net=pads['E_U29','5']['net'],position_mm=[124.5,133.0],size_mm=.6)
t=dict(ref='E_U29',pin='5',net=a['net'],position_mm=[130.5,149.0],size_mm=.6)
restored=connect(a,[t],'Restore both retained master-enable branches')
assert restored,'Cannot restore the original master-enable branch'
# Receiver outputs and digital follower gates.
link(('E_U41','7'),[cellvias['E_U30','6']],'PG3 Schmitt output to U30')
link(('E_U41','2'),[cellvias['E_U34','6']],'ANA PG1 Schmitt output to U34')
link_group(('E_U41','1'),('E_R119','1'),'DIG PG3 to Schmitt receiver')
link_group(('E_U30','7'),('E_R112','1'),'FOLLOW2 to digital eFuse enable')
link_group(('E_U34','7'),('E_R120','1'),'FOLLOW3 to digital eFuse enable')
# Source-backed AUX supplies, each distinct from its local bypass join.
for ref in ['E_U30','E_U34','E_U41']:link_group((ref,'8'),('E_U29','8'),ref+' AUX supply')
# Fixed analog receiver endpoints and the remaining analog gate output.
fixed=[('E_U31','2'),('E_U13','3'),('E_U14','3'),('E_U13','1'),('E_U32','1')]
for key in fixed:attach(key)
for source,target,label in [(('E_U41','5'),('E_U31','2'),'ANA PG0 Schmitt output to U31'),(('E_U41','3'),('E_U13','3'),'ANA PG0 to Schmitt receiver'),(('E_U41','6'),('E_U14','3'),'ANA PG1 to Schmitt receiver'),(('E_U30','3'),('E_U13','1'),'Analog enable to eFuse'),(('E_U34','3'),('E_U32','1'),'Analog follower2 to eFuse')]:
 if target in cellvias:link(source,[cellvias[target]],label)
 else:deferred.append(dict(label=label,source=list(source),target=list(target),reason='Fixed receiver needs placement/escape repair'))
# PG pullups and enable pulldowns share those same physical control nodes.
for key,target,label in [(('E_R95','1'),('E_U13','3'),'ANA PG0 pullup signal'),(('E_R99','1'),('E_U14','3'),'ANA PG1 pullup signal'),(('E_R96','1'),('E_U13','1'),'Analog enable pulldown signal'),(('E_R116','1'),('E_U32','1'),'Analog follower2 pulldown signal')]:
 if target not in cellvias:continue
 if attach(key):link(key,[cellvias[target]],label)
 else:deferred.append(dict(label=label,source=list(key),reason='Fixed resistor needs escape repair'))
Path('/private/tmp/startup-completion-routes-v8.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2))
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
