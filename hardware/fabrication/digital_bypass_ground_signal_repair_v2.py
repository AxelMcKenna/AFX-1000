"""Joint BYPASS escape, external thermal-via relocation and signal restoration."""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_bypass_ground_relocation_survey import SIGNAL_REMOVED,GROUND_TRACK,GROUND_VIA
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add,route
from hardware.fabrication.digital_native_route_cleanup import other_group_contacts,prune_single_face_vias
import hardware.fabrication.digital_xlat_escape_repair as repair
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v4 as search
ROOT=Path(__file__).resolve().parent
BYPASS='BYPASS_SENSE';LATCH='/LED/LATCH_5V';CODEC='CODEC_RUN'
def polys(g):return [dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]
def run():
 cp=ROOT/'staging/digital-blank-codec-inputs-32/capture.json';dp=ROOT/'staging/digital-bypass-ground-relocation-survey-01/diagnosis.json'
 cap,diag=[json.loads(p.read_text()) for p in (cp,dp)]
 for r in (cap,diag):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
 pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text())
 removed=[n for n in children(original,'segment') if first(n,'uuid')[1] in SIGNAL_REMOVED]
 assert len(removed)==4 and all(first(n,'net')[1] in (LATCH,CODEC) and float(first(n,'width')[1])==.2 for n in removed)
 old_ground_track=next(n for n in children(original,'segment') if first(n,'uuid')[1]==GROUND_TRACK)
 old_ground_via=next(n for n in children(original,'via') if first(n,'uuid')[1]==GROUND_VIA)
 assert float(first(old_ground_track,'width')[1])==1 and float(first(old_ground_via,'size')[1])==.6 and float(first(old_ground_via,'drill')[1])==.3
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01
 surface.SIGNAL_LAYERS=search.LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');repair.search=search
 escape=diag['escape'];via=escape['via_points'][0]
 source_pad=next(o for o in cap['objects'] if o.get('ref')=='U2003' and o.get('pin')=='22')
 contacts=other_group_contacts(cap,source_pad,search.LAYERS)
 attempts=[];selected=None;deadline=time.monotonic()+420
 for ground in diag['legal_options'][:3]:
  work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in SIGNAL_REMOVED]
  for o in work['objects']:
   if o['uuid']==GROUND_TRACK:
    o['position_mm']=ground['track_start_mm'];o['end_mm']=ground['track_end_mm'];o['layers']={'F.Cu':polys(LineString([o['position_mm'],o['end_mm']]).buffer(.5,quad_segs=64))}
   if o['uuid']==GROUND_VIA:
    p=ground['via_point_mm'];old=o['position_mm'];o['layers']={f:polys(translate(surface.shape(ps),p[0]-old[0],p[1]-old[1])) for f,ps in o['layers'].items()};o['position_mm']=p;o['drill_mm']=[.3,.3]
  for order in itertools.permutations((LATCH,CODEC,BYPASS)):
   if time.monotonic()>deadline:break
   screen=DigitalViaScreen(work,signal_layers=search.LAYERS)
   routes=[add(screen,BYPASS,dict(runs=escape['runs'],vias=escape['via_points']))]
   attempt=dict(ground=ground,order=order,routes=[]);attempts.append(attempt)
   for net in order:
    if net==BYPASS:
     source=dict(point=via,layers=list(search.LAYERS),runs=[],vias=[],cost=0.,group='escape')
     targets=[dict(point=p,layers=[f],runs=[],vias=[],cost=0.,group='retained') for f,p in contacts]
     result=search.route_multi(screen,net,[source],{f:targets for f in search.LAYERS},min(deadline,time.monotonic()+50),max_visits=3000000);bound=120
    else:
     start,end=([101.7,26.4],[93.9,28.9]) if net==LATCH else ([98.5721,29.555],[99.5675,36.1575])
     result=route(screen,net,'B.Cu',start,{('B.Cu',tuple(end))},min(deadline,time.monotonic()+35));bound=40 if net==LATCH else 30
    length=sum(LineString(p).length for f,p in result['runs']) if result else None
    attempt['routes'].append(dict(net=net,found=bool(result),length_mm=length,search_bound_mm=bound,proposed_route=result))
    print(ground['via_point_mm'],order,net,'found',bool(result),'length',length,flush=True)
    if result is None or length>bound:break
    routes.append(add(screen,net,result))
   if len(routes)==4:selected=ground,routes;break
  if selected or time.monotonic()>deadline:break
 paths=[cp,dp,pcb,Path(__file__),ROOT/'digital_native_route_cleanup.py']+[ROOT/n for n in ('digital_bypass_ground_relocation_survey.py','digital_bypass_outer_escape_survey.py','audit_candidate.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_continuous_escape_options_v4.py','digital_multilayer_escape_routes_v4.py','digital_visibility_escape.py','digital_native_spacing_search_v4.py','digital_native_spacing_search_v3.py','digital_native_spacing_search_v2.py','digital_continuous_via_bridges.py','nf_minimum_logic.py','nf_pin_escape_routes.py','route_nf_surface.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
 receipt=dict(source_sha256={str(p):sha(p) for p in paths},attempts=attempts,candidate_emitted=bool(selected),removed_uuids=sorted(SIGNAL_REMOVED),native_rules_relaxed=False,ground_branch_width_preserved_mm=1.,search_bounds_are_not_electrical_acceptance=True,fabrication_released=False)
 out=ROOT/'staging/digital-bypass-ground-signal-repair-02';out.mkdir(exist_ok=False)
 if selected:
  ground,routes=selected;routes,pruned=prune_single_face_vias(work,routes);receipt['pruned_unused_vias']=pruned;board=copy.deepcopy(original)
  for n in removed:board.remove(n)
  gt=next(n for n in children(board,'segment') if first(n,'uuid')[1]==GROUND_TRACK);gv=next(n for n in children(board,'via') if first(n,'uuid')[1]==GROUND_VIA)
  first(gt,'start')[1:]=ground['track_start_mm'];first(gt,'end')[1:]=ground['track_end_mm'];first(gv,'at')[1:]=ground['via_point_mm']
  for r in routes:
   for face,path in r['runs']:
    for p,q in zip(path,path[1:]):
     if math.dist(p,q)<1e-7:continue
     uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:BYPASS-GROUND:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
     board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
   for p in r['new_vias_mm']:
    uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:BYPASS-GROUND-via:{sha(cp)}:{r["net"]}:{p}'))
    board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
  dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
  receipt.update(candidate_PCB_sha256=sha(dest),routes=routes,ground_relocation=ground,ground_track_before=old_ground_track,ground_via_before=old_ground_via,removed_objects=removed,geometry_delta=geometry_delta(original,board),native_checks_pending=True)
 (out/'construction.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('Candidate emitted:',bool(selected),flush=True)
if __name__=='__main__':run()
