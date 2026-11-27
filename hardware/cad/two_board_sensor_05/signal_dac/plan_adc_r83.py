"""Bounded front-only ADC control connections; no sensitive feedback rerouting."""
import json,math,uuid,hashlib
from pathlib import Path
from shapely.geometry import LineString
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r83 as C
from hardware.cad.two_board_sensor_05.signal_dac.bounded_path import bounded_path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
R=C.R;routes=[];blocked=[];searches=[];joins=0
nets=['/A_ADC/'+x for x in ['THRESH_LOWER','THRESH_UPPER','BIAS_SHIFT_L','BIAS_SHIFT_R','PD_L','PD_R','PD_GATED']]
for net in nets:
 assert net not in C.sensitive
 groups=[list(m)for m in C.c['all_groups'].values()if C.obj[m[0]]['net']==net]
 while len(groups)>1:
  choices=[];trials=[]
  for i,g in enumerate(groups):
   for j in range(i+1,len(groups)):
    for u in g:
     p=C.obj[u]
     if p['kind']!='PAD'or not p['layers'].get('F.Cu'):continue
     for v in groups[j]:
      q=C.obj[v]
      if q['kind']!='PAD'or not q['layers'].get('F.Cu'):continue
      start,end=p['position_mm'],q['position_mm'];dist=math.dist(start,end)
      trials.append((dist,i,j,start,end))
      for path in C.S.candidate_paths(start,end):
       if LineString(path).length>dist*1.4+2:continue
       if C.screen.legal(net,'F.Cu',path):choices.append((LineString(path).length,i,j,path));break
  if not choices:
   for dist,i,j,start,end in sorted(trials)[:8]:
    bounds=[min(start[0],end[0])-3,min(start[1],end[1])-3,max(start[0],end[0])+3,max(start[1],end[1])+3]
    found=bounded_path(lambda p:C.screen.legal(net,'F.Cu',p),start,end,bounds,max_nodes=15000)
    searches.append({'net':net,'start':start,'end':end,'bounds_mm':bounds,'step_mm':.1,'max_nodes':15000,'reason':found['reason'],'visited':found['visited']})
    if found['path']is not None and LineString(found['path']).length<dist*1.4+2:choices.append((LineString(found['path']).length,i,j,found['path']));break
  if not choices:blocked.append({'net':net,'remaining_groups':groups});break
  length,i,j,path=min(choices);routes.append({'net':net,'layer':'F.Cu','width_mm':.2,'path_mm':path,'role':'join','join':joins});joins+=1;groups[i]+=groups[j];groups.pop(j);C.screen.added.append((net,'F.Cu',LineString(path)));print(net,length,flush=True)
t=read_sexpr((R/'native-r82/signal_main.kicad_pcb').read_text())
for k,r in enumerate(routes):
 for j,(p,q)in enumerate(zip(r['path_mm'],r['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),'F.Cu'],[a('net'),r['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-adc-r83-{k}-{j}'))]])
out=R/'candidate-r83';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');old=json.loads((R/'candidate-r82/routing.json').read_text());old['routes']+=routes;old['expected_opens']=190-joins;old['ADC_blocked']=blocked;old['ADC_searches']=searches;old['ADC_selected_nets']=nets;old['declared_removed_since_r82']=[]
paths=[Path(__file__),R/'adc_context_r83.py',R/'bounded_path.py',R/'native-r82/signal_main.kicad_pcb',R/'capture-r82/capture.json',R/'candidate-r82/routing.json',R.parents[2]/'electronics/adc_driver/README.md',R.parents[2]/'electronics/adc_driver/qualification/README.md']
old['ADC_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths};(out/'routing.json').write_text(json.dumps(old,indent=2)+'\n');print('JOINS',joins,'remaining',190-joins,'blocked nets',len(blocked))
