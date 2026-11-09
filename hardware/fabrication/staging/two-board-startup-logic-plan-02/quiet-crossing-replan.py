from pathlib import Path
import json,types,inspect,textwrap
s=Path('/private/tmp/plan_startup_interconnects_v2.py').read_text();exec(s[:s.index('# Reserve the two fixed')])
prev=json.loads(Path('/private/tmp/startup-interconnects-v3.json').read_text())
replace={'FOLLOW1 gate output to eFuse enable','PG0 to Schmitt input','PG2 to Schmitt input'}
for v in prev['extra_vias']:
 extra.append(v);cellvias[v['ref'],v['pin']]=v;screen.vias.append((v['net'],v['position_mm']))
 for l in c['copper_layers']:screen.added.append((v['net'],l,Point(v['position_mm']).buffer(.2)))
for r in prev['routes']:
 if r.get('label') in replace:continue
 new.append(r);screen.added.append((r['net'],r['layer'],LineString(r['path_mm'])))
exec(s[s.index('def connect('):s.index('# Restore both')].replace('budget=18000','budget=90000').replace("layers=('In2.Cu','In3.Cu','In6.Cu')","layers=('In2.Cu','In3.Cu')"))
joins=[j for j in prev['joins'] if j['label'] not in replace];deferred=[]
method=textwrap.dedent(inspect.getsource(routing.Screen.grid_path)).replace('min(u, v)-50','min(u, v)-100').replace('max(u, v)+50','max(u, v)+100')
ns=dict(routing.__dict__);exec(method,ns);screen.grid_path=types.MethodType(ns['grid_path'],screen)
# Existing inner-layer supply fields enclose the old vias. Bring each signal
# out on its existing surface copper before transitioning below those fields.
quiet=json.loads((STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json').read_text())['quiet_ground_islands']
qid={u for q in quiet for u in q['zone_uuids']};qfields=[routing.shape(z['authored_outline']) for z in c['zones'] if z['uuid'] in qid]
for source,target,label in [(('E_U29','3'),('E_R108','1'),'FOLLOW1 gate output to eFuse enable'),(('E_U40','1'),('E_R103','1'),'PG0 to Schmitt input'),(('E_U40','6'),('E_R111','1'),'PG2 to Schmitt input')]:
 o=pads[target];net=o['net'];layer='B.Cu';cent=o['position_mm'];choices=[]
 for d,xy in sorted((math.dist(cent,(ix*.5,iy*.5)),(ix*.5,iy*.5)) for ix in range(int((cent[0]-10)*2),int((cent[0]+10)*2)+1) for iy in range(int((cent[1]-10)*2),int((cent[1]+15)*2)+1)):
  if d>15 or not screen.via_legal(net,xy):continue
  if any(Point(xy).distance(q)<.6 for q in qfields):continue
  # At least one inner layer must allow an immediate escape from this via.
  available=[l for l in ['In2.Cu','In3.Cu'] if all(z['net']==net or z['layer']!=l or Point(xy).distance(routing.shape(z['polygons']))>.61 for z in c['zones'] if z['net']!='PWR_AGND')]
  if not available:continue
  path=screen.simple(net,layer,cent,xy,24)
  if path:choices.append((path[0],xy,path[1],available))
  elif len(choices)<2 and len(choices)>=0:
   # Defer expensive local searches until all direct candidates are known.
   pass
  if len(choices)>=16:break
 if not choices:
  print('NO SURFACE TRANSITION',target,flush=True);deferred.append(dict(label=label,reason='No surface-to-free-inner transition'));continue
 chosen=None
 print('CHOICES',target,[(xy,ls) for _,xy,pt,ls in choices],flush=True)
 for _,xy,path,layers in sorted(choices):
  # Validate the inner connection before committing the new via or escape.
  temp=dict(ref=target[0],pin=target[1],net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
  result=connect(cellvias[source],[temp],label,layers=layers)
  if result:chosen=(temp,path,result);break
  deferred.pop()
 if not chosen:deferred.append(dict(label=label,reason='All screened transitions failed inner routing'));continue
 v,path,result=chosen;extra.append(v);screen.vias.append((net,v['position_mm']))
 for l in c['copper_layers']:screen.added.append((net,l,Point(v['position_mm']).buffer(.2)))
 add(net,layer,path,label+' surface transition');joins.append(result)
 print('TRANSITION',target,v['position_mm'],flush=True)
Path('/private/tmp/startup-interconnects-v5.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2))
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
