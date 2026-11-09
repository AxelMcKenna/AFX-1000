"""Consolidate obsolete internal ports and regroup/route U20's local cell.

Retiring the old source-side return studs does NOT qualify replacement return
copper. Low-impedance analog/digital force returns remain explicit release holds.
"""
import copy,json,math,shutil,uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha,read_netlist
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position,angle,transform_object,mechanical_check
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-buck-enable-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2508-buck-enable/capture.json'
SURVEY=STAGING/'two-board-u20-cell-survey-01/survey.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
LOCAL=STAGING/'two-board-power-buck-local-native-01/buck-local-routing.json'
OUT=STAGING/'two-board-power-u20-local-01'
RETIRED={'P_J20':{'1':'PWR_AGND'},'P_J21':{'1':'PWR_AGND'},'P_J106':{'1':'PWR_V2V5_AUX','2':'PWR_AGND','3':'PWR_RUN_BEFORE_FAN','4':'PWR_P03_SOURCES_READY'}}
ANCHOR=[177.5,136.5]
REFMAP={'P_U23':'P_U20','P_L23':'P_L20','P_C220':'P_C200','P_C221':'P_C201','P_C222':'P_C202','P_C223':'P_C203','P_C230':'P_C210','P_C231':'P_C211','P_R221':'P_R201','P_R220':'P_R206'}

def remove_port(sheet,ref,wanted):
 symbol=next(s for s in children(sheet,'symbol') if prop(s,'Reference')[2]==ref);assert float(first(symbol,'at')[3])==0
 x,y=map(float,first(symbol,'at')[1:3]);lib=next(s for s in children(first(sheet,'lib_symbols'),'symbol') if s[1]==first(symbol,'lib_id')[1]);nodes=[symbol];found=set()
 for unit in children(lib,'symbol'):
  for pin in children(unit,'pin'):
   n=str(first(pin,'number')[1]);assert n in wanted;found.add(n);px,py=map(float,first(pin,'at')[1:3]);point=[x+px,y-py]
   wires=[w for w in children(sheet,'wire') if any(math.dist(point,list(map(float,p[1:3])))<1e-6 for p in children(first(w,'pts'),'xy'))];assert len(wires)==1
   wire=wires[0];ends=[list(map(float,p[1:3])) for p in children(first(wire,'pts'),'xy')];other=next(p for p in ends if math.dist(point,p)>1e-6)
   labels=[l for l in children(sheet,'global_label') if math.dist(other,list(map(float,first(l,'at')[1:3])))<1e-6];assert len(labels)==1 and labels[0][1]==wanted[n]
   assert not any(math.dist(other,list(map(float,first(j,'at')[1:3])))<1e-6 for j in children(sheet,'junction'))
   assert sum(any(math.dist(other,list(map(float,p[1:3])))<1e-6 for p in children(first(w,'pts'),'xy')) for w in children(sheet,'wire'))==1
   nodes.extend([wire,labels[0]])
 assert found==set(wanted) and len(nodes)==1+2*len(wanted)
 for n in nodes:sheet.remove(n)
 return nodes

def run():
 assert not OUT.exists()
 cap=json.loads(CAP.read_text());survey=json.loads(SURVEY.read_text())
 for d in [cap,survey]:
  for n,h in d['source_sha256'].items():assert sha(REPO/n)==h,n
 parts,pins=read_netlist(BASE/'netlist.xml');objects={o['uuid']:o for o in cap['objects']}
 for r,ns in RETIRED.items():
  assert {pin:net for (ref,pin),net in pins.items() if ref==r}==ns
  for o in objects.values():
   if o.get('ref')==r and o.get('group'):assert cap['all_groups'][o['group']]==[o['uuid']]
 # Actual consumers/drivers remain, including both sides of the fan RUN gate.
 for node,net in [(('F_U15','4'),'PWR_RUN_BEFORE_FAN'),(('E_U28','11'),'PWR_P03_SOURCES_READY'),(('P_U25','12'),'PWR_P03_SOURCES_READY'),(('E_U1','1'),'PWR_V2V5_AUX'),(('E_J7','1'),'PWR_AGND'),(('F_J201','2'),'PWR_AGND')]:assert pins[node]==net,node
 assert pins['G_NT1','1']!=pins['G_NT1','2'] and pins['N_J1','2']!=pins['N_J6','2']
 board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());oldfps={prop(f,'Reference')[2]:f for f in children(board,'footprint')}
 cell=next(c for c in survey['cells'] if c['rotation_degrees']==0);candidate=next(c for c in cell['candidates'] if c['anchor_mm']==ANCHOR);assert set(candidate['blocking_owners'])==set(RETIRED)
 moving={m['ref'] for m in cell['members']};assert len(moving)==20
 for o in objects.values():
  if o.get('ref') in moving and o.get('group'):assert cap['all_groups'][o['group']]==[o['uuid']] or all(objects[u].get('ref')==o['ref'] for u in cap['all_groups'][o['group']])
 fps={r:copy.deepcopy(f) for r,f in oldfps.items() if r not in RETIRED};moves=[]
 for m in cell['members']:
  r=m['ref'];target=[round(ANCHOR[i]+m['delta_mm'][i],6) for i in range(2)];rot=m['angle_degrees']-angle(oldfps[r]);moves.append(dict(ref=r,old_xy=position(oldfps[r]),new_xy=target,rotation_added_degrees=rot))
  if r!='P_C201':fps[r]=rotate_footprint(fps[r],target,rot);continue
  f=rotate_footprint(oldfps['P_C221'],target,m['angle_degrees']-angle(oldfps['P_C221']));prop(f,'Reference')[2]=r;first(f,'uuid')[:]=first(oldfps[r],'uuid')
  f[:]=[n for n in f if not(isinstance(n,list) and n and n[0]=='path')];f.extend(copy.deepcopy(children(oldfps[r],'path')))
  oldpads={str(p[1]):p for p in children(oldfps[r],'pad')}
  for p in children(f,'pad'):
   first(p,'uuid')[:]=first(oldpads[str(p[1])],'uuid');first(p,'net')[:]=first(oldpads[str(p[1])],'net')
  fps[r]=f
 mechanical_check(fps,moving,json.loads(PLACEMENT.read_text()))
 move_by={r['ref']:r for r in moves};new=[]
 for o in objects.values():
  ref=o.get('ref')
  if ref in RETIRED:continue
  if ref=='P_C201':
   source=next(q for q in objects.values() if q.get('ref')=='P_C221' and q.get('pin')==o['pin']);n=transform_object(source,position(oldfps['P_C221']),position(fps[ref]),angle(fps[ref])-angle(oldfps['P_C221']))
   for k in ['ref','uuid','net','group']:n[k]=o[k]
  elif ref in moving:
   r=move_by[ref];n=transform_object(o,r['old_xy'],r['new_xy'],r['rotation_added_degrees'])
  else:n=o
  new.append(n)
 geometry=[(o,l,shape(ps)) for o in new for l,ps in o['layers'].items() if ps];trees={l:([(o,g) for o,k,g in geometry if k==l],STRtree([g for o,k,g in geometry if k==l])) for l in cap['copper_layers']}
 outline=shape(cap['outline']).buffer(-.5);holes=[];mounts=[]
 for o in new:
  d=o.get('drill_mm',0);radius=max(d)/2 if isinstance(d,list) else d/2
  if radius:holes.append((o['position_mm'],radius))
  if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref']):mounts.append((o['position_mm'],max(3.6,radius+.5)))
 assert len(mounts)==15
 for o,l,g in geometry:
  if o.get('ref') not in moving:continue
  assert outline.covers(g)
  rows,tree=trees[l]
  for i in tree.query(g.buffer(.211)):
   q,h=rows[int(i)]
   if q.get('ref')!=o['ref'] and q['net']!=o['net']:assert g.distance(h)>=.21-1e-7,(o.get('ref'),o.get('pin'),q.get('ref'),q.get('pin'))
  assert all(g.distance(Point(p))-r>=.15 for p,r in holes)
  assert all(g.distance(Point(p))>=r+.01 for p,r in mounts)
 # Every changed or removed footprint is remote from the unchanged U23 zones.
 for o in [q for q in objects.values() if q.get('ref') in moving|set(RETIRED)]+[q for q in new if q.get('ref') in moving]:
  for z in cap['zones']:
   assert all(shape(ps).distance(shape(z['authored_outline']))>2 for ps in o['layers'].values() if ps)
 board[:]=[n for n in board if not(isinstance(n,list) and n and n[0]=='footprint' and prop(n,'Reference')[2] in RETIRED)]
 for i,f in enumerate(board):
  if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in moving:board[i]=fps[prop(f,'Reference')[2]]
 codes={str(n[2]):int(n[1]) for n in children(board,'net')};local=json.loads(LOCAL.read_text());routes=[];added=[]
 pad=lambda r,p:next(o for o in new if o.get('ref')==r and o.get('pin')==p)
 for old in local['routes']:
  left=[REFMAP.get(old['left'][0],old['left'][0]),old['left'][1]];right=[REFMAP.get(old['right'][0],old['right'][0]),old['right'][1]]
  pts=[[round(p[0]-295+ANCHOR[0],6),round(p[1]-127+ANCHOR[1],6)] for p in old['path_mm']]
  net=pad(*(right if left[0]=='_SW_ANCHOR' else left))['net'];w=old['width_mm'];line=LineString(pts)
  for endpoint,xy in [(left,pts[0]),(right,pts[-1])]:
   if endpoint[0]!='_SW_ANCHOR':assert pad(*endpoint)['net']==net and math.dist(pad(*endpoint)['position_mm'],xy)<2e-6,(old['label'],endpoint)
  assert outline.buffer(-w/2-.01).covers(line)
  rows,tree=trees['F.Cu']
  for i in tree.query(line.buffer(w/2+.211)):
   q,g=rows[int(i)]
   if q['net']!=net:assert line.distance(g)>=w/2+.21-1e-7,(old['label'],q.get('ref'),q.get('pin'))
  assert all(n==net or line.distance(g)>=w/2+width/2+.21-1e-7 for n,width,g in added)
  assert all(line.distance(Point(p))>=r+w/2+.01 for p,r in mounts)
  for z in cap['zones']:assert line.distance(shape(z['authored_outline']))>2
  ids=[]
  for i,(p,q) in enumerate(zip(pts,pts[1:])):
   u=str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPU20LOCAL01:'+sha(CAP)+':'+old['label']+':'+str(i)));ids.append(u)
   board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),w],[a('layer'),'F.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
  added.append((net,w,line));routes.append(dict(label=old['label'].replace('P_C23','P_C21').replace('P_C22','P_C20'),left=left,right=right,net=net,width_mm=w,path_mm=pts,length_mm=line.length,maximum_length_mm=old['maximum_length_mm'],segment_uuids=ids))
 shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md','local-plane-fill.json','native-zone-export.*','enable-dc-screen.json'))
 (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 p=OUT/'P_power_p03.kicad_sch';sheet=read_sexpr(p.read_text());deleted={r:remove_port(sheet,r,ns) for r,ns in RETIRED.items()}
 symbol=next(s for s in children(sheet,'symbol') if prop(s,'Reference')[2]=='P_C201');replacement=dict(ref='P_C201',old_value=prop(symbol,'Value')[2],old_footprint=prop(symbol,'Footprint')[2],new_value=prop(fps['P_C201'],'Value')[2],new_footprint=str(fps['P_C201'][1]))
 prop(symbol,'Value')[2]=replacement['new_value'];prop(symbol,'Footprint')[2]=replacement['new_footprint'];prop(symbol,'Datasheet')[2]='https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005X7R1H104K050BB';p.write_text(sexpr(sheet)+'\n')
 for name in ['expected-circuit.json','symbol-paths.json']:
  p=OUT/name;d=json.loads(p.read_text())
  for ref in RETIRED:del d[ref]
  if name=='expected-circuit.json':d['P_C201']['value']=replacement['new_value'];d['P_C201']['footprint']=replacement['new_footprint']
  p.write_text(json.dumps(d,indent=2)+'\n')
 p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP18';p.write_text(sexpr(root)+'\n')
 paths=[Path(__file__),CAP,SURVEY,PLACEMENT,LOCAL,BASE/'power_protection.kicad_pcb',BASE/'netlist.xml',BASE/'P_power_p03.kicad_sch',BASE/'expected-circuit.json',BASE/'buck-enable-audit.json',REPO/'hardware/electronics/power_distribution/p03/spec.py',REPO/'hardware/electronics/power_distribution/p03/README.md',STAGING/'two-board-power-interface-audit-01/interface-review.json',STAGING/'assembly-layout-04/allocation.json',*[REPO/'hardware/fabrication'/n for n in ['repack_two_board_buck_input.py','route_two_board_buck_cell.py','route_nf_surface.py']]]
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},moves=moves,bootstrap_replacement=replacement,
  retired_connector_pins=RETIRED,retired_schematic_nodes=deleted,retired_terminal_opens=6,retired_copper_segments=0,
  internal_return_terminal_retirement_basis='Source, disconnect and fan/NF circuits share the same new power PCB. No external signal-board port or protective stage is removed. Former analog/digital return-bar functions require qualified PCB current-return paths before release.',
  return_replacement_qualified=False,legacy_return_bars_require_updated_assembly_design=True,
  selected_anchor_mm=ANCHOR,routes=routes,added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=0,
  existing_tracks_vias_and_local_U23_zones_unchanged=True,changed_geometry_at_least_2mm_from_existing_zone_outlines=True,
  expected_parts=1085,expected_footprints=1100,expected_opens_after_retirement_only=2502,expected_opens_after_local_routes=2486,
  local_current_loops_and_output_network_qualified=False,native_validation_pending=True,fabrication_released=False)
 (OUT/'u20-local-change.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(moved=len(moves),retired=sorted(RETIRED),routes=len(routes),segments=result['added_segments'],expected_opens=2486)))

if __name__=='__main__':run()
