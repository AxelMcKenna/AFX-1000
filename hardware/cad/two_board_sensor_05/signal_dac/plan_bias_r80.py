import json
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.cad.two_board_sensor_05.signal_dac import routing_context_r79 as C
from hardware.cad.two_board_sensor_05.signal_dac.bounded_path import bounded_path
ids={'cf016448-f25e-5ec5-be0e-4e9909c719dc','0806b2a9-a35e-5518-b572-09eed64c4f90','31ef76f5-1cb6-58fd-ad56-23b1d77fb1a0'}
assert not ids&{x['uuid']for x in C.baseline['objects']}
C.c={**C.c,'objects':[x for x in C.c['objects']if x['uuid']not in ids]};C.screen=C.S.Screen(C.c);C.base_legal=C.screen.legal;C.screen.legal=C.ref_legal
C.obs=[(o,C.S.shape(ps))for o in C.c['objects']for ps in o['layers'].values()if ps];C.tree=STRtree([g for _,g in C.obs])
left=[106.59115,78.134649];right=[129.231815,79.12244];ret=[108.09115,79.884649];net='/A_DAC/BIAS_P_R'
for q in [left,right]:
 print('VIA',q,C.vialegal(q,net),C.return_site(q),flush=True)
 for layer in C.S.SIGNAL_LAYERS:C.screen.added.append((net,layer,Point(q).buffer(.2)))
for layer in C.S.SIGNAL_LAYERS:C.screen.added.append(('LINK_AGND',layer,Point(ret).buffer(.2)))
paths=[('/A_DAC/BIAS_P_L',[[107.4,81],[107.3,78.8],[107.35,78],[106.8,74.9]]),('/A_DAC/RX_POS_L',[[126.925,78.835],[129.5875,78.1],[129.5875,69.8]])]
for n,p in paths:
 ok=C.screen.legal(n,'In3.Cu',p);print('REWORK',n,ok,flush=True)
 if not ok:
  for ix in C.screen.trees['In3.Cu'].query(LineString(p).buffer(.5)):
   nn,g,d=C.screen.geometry['In3.Cu'][int(ix)]
   if nn!=n and LineString(p).distance(g)<=d:print('obstacle',nn,LineString(p).distance(g),flush=True)
  continue
 C.screen.added.append((n,'In3.Cu',LineString(p)))
for layer in ['In3.Cu','In5.Cu']:
 found=bounded_path(lambda p:C.screen.legal(net,layer,p),left,right,(99,64,140,89),max_nodes=100000)
 print('ROUTE',layer,found,flush=True)
assert found['path'] is not None
import uuid,hashlib
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=C.R;t=read_sexpr((R/'native-r78/signal_main.kicad_pcb').read_text());removed=[]
for row in list(t):
 if isinstance(row,list) and row and row[0] in ['segment','via'] and first(row,'uuid')[1] in ids:
  removed.append({'uuid':first(row,'uuid')[1],'before_sexpr':sexpr(row),'net':first(row,'net')[1],'reason':'Rework previously added copper for final BIAS_P_R escape; preserve original copper.'});t.remove(row)
assert len(removed)==3
routes=[{'net':n,'layer':'In3.Cu','width_mm':.2,'path_mm':p,'role':'agent_rework','join':0}for n,p in paths]
routes += [{'net':net,'layer':'F.Cu','width_mm':.2,'path_mm':p,'role':'escape','join':0}for p in [[[105.525,78.635],left],[[128,78.0875],right]]]
routes.append({'net':net,'layer':'In5.Cu','width_mm':.2,'path_mm':found['path'],'role':'join','join':0})
for row in routes:
 C.prospective_holes=[left,right]
 assert C.screen.legal(row['net'],row['layer'],row['path_mm'])
vias=[]
for k,(q,uid,r)in enumerate([(left,'ef038536-de23-4a7a-84d1-d86380bea993',ret),(right,'cda4b539-b3f5-415b-b756-ab759fab1ac1',[131.505,79.5])]):
 v={'net':net,'at':q,'from_pad':uid,'return_at':r,'size_mm':.6,'drill_mm':.3,'uuid':str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r80-via-{k}'))};vias.append(v)
 t.append([a('via'),[a('at'),*q],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),v['uuid']]])
for k,row in enumerate(routes):
 for j,(p,q)in enumerate(zip(row['path_mm'],row['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),row['layer']],[a('net'),row['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r80-{k}-{j}'))]])
out=R/'candidate-r80';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n')
source=[Path(__file__) if False else R/'plan_bias_r80.py',R/'routing_context_r79.py',R/'bounded_path.py',R/'native-r78/signal_main.kicad_pcb',R/'capture-r78/capture.json']
(out/'routing.json').write_text(json.dumps({'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in source},'routes':routes,'vias':vias,'planned_ground_returns':[ret],'used_return_sites':[{'signal_at':v['at'],'return_at':v['return_at']}for v in vias],'declared_removed_since_r78':removed,'expected_opens':190,'blocked':[],'bounded_search_records':{'layer':'In5.Cu','bounds_mm':[99,64,140,89],'step_mm':.1,'max_nodes':100000,**found},'BIAS_P_R_trace_length_mm':sum(LineString(r['path_mm']).length for r in routes if r['net']==net)},indent=2)+'\n')
