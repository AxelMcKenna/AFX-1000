from pathlib import Path
import json,math,hashlib,importlib.util,re,xml.etree.ElementTree as ET
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;REPO=HERE.parents[3]
helper=BASE/'r12_ground/verify.py';spec=importlib.util.spec_from_file_location('distance',helper);distance=importlib.util.module_from_spec(spec);spec.loader.exec_module(distance)
g=json.loads((HERE/'routes.json').read_text());bows=json.loads((BASE/'r22_ground_signal_clearance/bows.json').read_text());right=json.loads((BASE/'r15_right_ground/right-routes.json').read_text())['edges'];left=json.loads((BASE/'r14_left_ground/left-routes.json').read_text())['edges'];selected=json.loads((BASE/'r20_scene_signal/route.json').read_text())['edges'];old=left+[e for e in right if e['id'] not in bows['replaces_wires']]+bows['edges']+selected+json.loads((BASE/'r21_adjacent_signals/routes.json').read_text())['edges']
datums=json.loads((BASE/'r12_ground/ground-routes.json').read_text())['endpoints_mm'];contract=json.loads((BASE/'r11_distribution/reference/panel-contract.json').read_text());nets={(node.get('ref'),node.get('pin')):net.get('name') for net in ET.parse(BASE/'r11_distribution/reference/signal-netlist.xml').findall('.//nets/net') for node in net.findall('node')}
assert {(e['source'],e['target']) for e in g['edges']}=={('D_J2002:6','button_scene_4:1')}
assert not {e['source'] for e in g['edges']} & {e['source'] for e in selected}
minimum=999;minimum_terminal=999;results=[];closest=None
max_radius=max(x['radius_mm'] for e in g['edges'] for x in e['primitives'] if x['kind']=='arc')
clearance_bound=.88*math.cos(math.pi/32)**2-max_radius*(1-math.cos(math.radians(1.5)))-.6
assert clearance_bound>=.25

for e in g['edges']:
 name=e['target'][7:-2];pad=next(x['signal'] for x in contract['front_inputs'] if x['id']==name);assert e['source']==pad['reference']+':'+pad['pin'] and e['net']==pad['net']==nets[pad['reference'],pad['pin']]
 p=np.array(e['points_mm'])
 for filename,prefix,radius in [('routes.scad','panel_signal_',.6),('clearance.scad','clearance_',.88)]:
  body=(HERE/filename).read_text().split('module '+prefix+e['id']+'(){',1)[1].split('\n}',1)[0]
  modeled=np.array([json.loads(q) for q in re.findall(r'translate\((\[[^]]+\])\)',body)])
  assert modeled.shape==(2*(len(p)-1),3)
  assert np.max(np.abs(modeled-np.array([q for a,b in zip(p,p[1:]) for q in [a,b]])))<1e-9
  assert len(re.findall(r'sphere\(r='+re.escape(str(radius).lstrip('0'))+r',\$fn=32\)',body))==len(modeled)
 assert np.linalg.norm(p[0]-(pad['xy']+[27.04]))<1e-7 and np.linalg.norm(p[-1]-datums[e['target']])<1e-7
 cursor=0;last=None;min_radius=999;joins=[]
 for primitive in e['primitives']:
  assert np.linalg.norm(p[cursor]-primitive['start'])<1e-7
  if primitive['kind']=='line':
   end=np.array(primitive['end']);T=end-p[cursor];T=T/np.linalg.norm(T);next_cursor=cursor+1;assert np.linalg.norm(p[next_cursor]-end)<1e-7;end_tangent=T
  else:
   assert primitive['kind']=='arc';R=primitive['radius_mm'];assert R>=12;min_radius=min(min_radius,R)
   T,N=np.array(primitive['tangent']),np.array(primitive['normal']);assert abs(T@N)<1e-8 and abs(T@T-1)<1e-8 and abs(N@N-1)<1e-8
   angle=math.radians(primitive['angle_degrees']);steps=math.ceil(primitive['angle_degrees']/3);next_cursor=cursor+steps;angles=np.linspace(0,angle,steps+1);expected=p[cursor]+R*np.sin(angles)[:,None]*T+R*(1-np.cos(angles))[:,None]*N;assert np.max(np.linalg.norm(p[cursor:next_cursor+1]-expected,axis=1))<1e-7;end_tangent=math.cos(angle)*T+math.sin(angle)*N
  if last is not None:assert last@T>1-1e-9;joins.append(float(last@T))
  cursor=next_cursor;last=end_tangent
 assert cursor==len(p)-1
 for other in old+[x for x in g['edges'] if x['id']>e['id']]:
  q=np.array(other['points_mm'])
  for a,b in zip(p,p[1:]):
   for c,d in zip(q,q[1:]):
    lower=np.linalg.norm(np.maximum(0,np.maximum(np.minimum(a,b),np.minimum(c,d))-np.minimum(np.maximum(a,b),np.maximum(c,d))))
    if lower>=minimum:continue
    new=distance.distance(a,b,c,d)
    if new<minimum:minimum=new;closest=dict(wires=[e['id'],other['id']],segments=[[a.tolist(),b.tolist()],[c.tolist(),d.tolist()]])
 lengths=np.linalg.norm(p[1:]-p[:-1],axis=1);stations=np.concatenate(([0],np.cumsum(lengths)))
 for i,(a,b) in enumerate(zip(p,p[1:])):
  for j in range(i+2,len(p)-1):
   if stations[j]-stations[i+1]<=3:continue
   c,d=p[j],p[j+1]
   if np.any(np.maximum(np.minimum(a,b),np.minimum(c,d))-np.minimum(np.maximum(a,b),np.maximum(c,d))>1.2):continue
   assert distance.distance(a,b,c,d)>=1.2+2*max_radius*(1-math.cos(math.radians(1.5))),(e['id'],'self collision',i,j)
 for name,point in datums.items():
  if not name.startswith('button_') or not name.endswith(':1') or name==e['target']:continue
  point=np.array(point)
  for a,b in zip(p,p[1:]):
   v=b-a;minimum_terminal=min(minimum_terminal,float(np.linalg.norm(point-a-np.clip((point-a)@v/(v@v),0,1)*v)))
 results.append(dict(wire=e['id'],net=e['net'],minimum_radius_mm=min_radius,minimum_tangent_join_dot=min(joins),terminal_tangent=last.tolist(),installed_centerline_length_mm=sum(math.dist(q["start"],q["end"]) if q["kind"]=="line" else q["radius_mm"]*math.radians(q["angle_degrees"]) for q in e["primitives"]),sampled_centerline_length_mm=float(stations[-1])))
def sag(edge):
 return max((p['radius_mm']*(1-math.cos(math.radians(p['angle_degrees'])/math.ceil(p['angle_degrees']/3)/2)) for p in edge.get('primitives',[]) if p['kind']=='arc'),default=0)
new_sag=max(map(sag,g['edges']));old_sag=max(map(sag,old));gap=minimum-1.2-new_sag-old_sag
assert gap>=.25,('selected wire clearance below0.25mm',minimum,closest)
assert minimum_terminal-1.2-new_sag>=.25,('other signal terminal clearance below0.25mm',minimum_terminal)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert all(sha(REPO/p)==h for p,h in g['source_sha256'].items())
sources=[Path(__file__),helper,HERE/'routes.json',HERE/'routes.scad',HERE/'clearance.scad',BASE/'r22_ground_signal_clearance/bows.json',BASE/'r15_right_ground/right-routes.json',BASE/'r14_left_ground/left-routes.json',BASE/'r20_scene_signal/route.json',BASE/'r12_ground/ground-routes.json',BASE/'r11_distribution/reference/panel-contract.json',BASE/'r11_distribution/reference/signal-netlist.xml',BASE/'r21_adjacent_signals/routes.json']
out=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},wires=results,minimum_wire_surface_gap_mm=gap,closest_wire_pair=closest,minimum_other_signal_terminal_surface_gap_mm=minimum_terminal-1.2-new_sag,expanded_controls_probe_min_margin_mm=clearance_bound,requires_ground_variant='r22',fabrication_released=False,opening_slack_qualified=False)
(HERE/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))
