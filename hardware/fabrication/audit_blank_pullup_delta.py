"""Verify the LED_BLANK pull-up translation and restored signal and 3.3 V supply."""
import copy,json,math
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
from hardware.fabrication.audit_latch_via_delta import check as parent_check
from hardware.fabrication.audit_digital_blank_pullup import check as physical_check
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v2 as search
ROOT=Path(__file__).resolve().parent
NET='LED_BLANK'
REMOVED={'fea0fc0e-c268-5cfe-8eb2-4c235472bb03'}
def refs(tree):
 return {next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(tree,'footprint')}
def verify_delta(before,after,recipe):
 old,new=refs(before),refs(after);assert old.keys()==new.keys()
 assert all(sexpr(f)==sexpr(new[r]) for r,f in old.items() if r!='R3010')
 move=recipe['component_move'];assert move['ref']=='R3010'
 assert move['before_mm']==[75.,25.] and move['after_mm']==[60.5,13.5]
 assert list(map(float,first(old['R3010'],'at')[1:3]))==move['before_mm']
 moved=copy.deepcopy(new['R3010']);assert list(map(float,first(moved,'at')[1:3]))==move['after_mm']
 moved[moved.index(first(moved,'at'))]=copy.deepcopy(first(old['R3010'],'at'))
 assert sexpr(moved)==sexpr(old['R3010'])
 delta=geometry_delta(before,after);assert delta==recipe['geometry_delta'] and delta['other_root_geometry_exact']
 assert delta['footprint']==dict(added=[],removed=[],changed=[first(old['R3010'],'uuid')[1]])
 for tag in ('via','zone'):assert delta[tag]==dict(added=[],removed=[],changed=[])
 assert set(delta['segment']['removed'])==REMOVED and not delta['segment']['changed'] and len(delta['segment']['added'])==13
 oldtracks={first(n,'uuid')[1]:n for n in children(before,'segment')}
 assert set(recipe['removed_uuids'])==REMOVED and {first(n,'uuid')[1] for n in recipe['removed_objects']}==REMOVED
 assert all(n==oldtracks[first(n,'uuid')[1]] and first(n,'net')[1]=='V3V3_IO' for n in recipe['removed_objects'])
 assert recipe['supply_surface_connection_required'] is True
 for node in children(after,'segment'):
  if first(node,'uuid')[1] not in delta['segment']['added']:continue
  assert first(node,'net')[1] in {NET,'V3V3_IO'}
  assert float(first(node,'width')[1])==.2 and first(node,'layer')[1]=='B.Cu'
 return delta

def check():
 parent=ROOT/'staging/digital-latch-via-native-01';out=ROOT/'staging/digital-blank-pullup-native-01';rd=ROOT/'staging/digital-blank-pullup-repack-01';rp=rd/'construction.json';recipe=json.loads(rp.read_text())
 assert all(sha(Path(p))==h for p,h in recipe['source_sha256'].items())
 candidate=rd/'digital_core.kicad_pcb';assert sha(candidate)==recipe['candidate_PCB_sha256']
 pcbpaths=[p/'digital_core.kicad_pcb' for p in (parent,out)];before,after=[read_sexpr(p.read_text()) for p in pcbpaths]
 delta=verify_delta(before,after,recipe);d=geometry_delta(read_sexpr(candidate.read_text()),after)
 assert d['other_root_geometry_exact'] and all(d[tag]==dict(added=[],removed=[],changed=[]) for tag in ('footprint','segment','via','zone'))
 pp=parent/'latch-review.json';assert parent_check()==json.loads(pp.read_text())
 physical=out/'corridor-audit.json';assert physical_check(out.name,'digital-blank-pullup-inputs-43')==json.loads(physical.read_text())
 paths=[Path(__file__),rp,candidate,pp,physical,*pcbpaths];records=[]
 for folder,opens in [(parent,44),(out,43)]:
  review_path=folder/'review.json';r=json.loads(review_path.read_text());assert not native_evidence_errors(folder/'digital_core.kicad_pro',r)
  assert r['status']['counts']==dict(violations=0,unconnected_items=opens,schematic_parity=0,erc=0)
  cp=folder/'stage-connectivity-review.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items());records.append(c);paths += [review_path,cp]
 oldnets,newnets=[{r['net']:r for r in c['nets']} for c in records];assert oldnets.keys()==newnets.keys();improved=[]
 for net,old in oldnets.items():
  a=[set(map(tuple,g)) for g in old['pad_groups']];b=[set(map(tuple,g)) for g in newnets[net]['pad_groups']]
  assert set.union(*a)==set.union(*b) and all(any(g<=h for h in b) for g in a),net
  if len(b)<len(a):improved.append(net)
  if net not in {NET,'V3V3_IO'}:assert newnets[net]==old,net
 assert improved==[NET] and len(oldnets[NET]['pad_groups'])==3 and len(newnets[NET]['pad_groups'])==2
 assert not newnets[NET]['all_pads_connected'] and newnets['V3V3_IO']['all_pads_connected']
 assert any({('R3010','1'),('R1002','1'),('U3005','6')}<=set(map(tuple,g)) for g in newnets[NET]['pad_groups'])
 assert any({('R3010','2'),('R1002','2')}<=set(map(tuple,g)) for g in newnets['V3V3_IO']['pad_groups'])
 cp=ROOT/'staging/digital-blank-pullup-inputs-43/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 newids=set(delta['segment']['added']+delta['via']['added']);work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in newids]
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;signal_layers=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=DigitalViaScreen(work,signal_layers=signal_layers);added=[o for o in cap['objects'] if o['uuid'] in newids]
 for o in added:
  if o['kind']=='PCB_TRACK':
   assert screen.legal(o['net'],next(iter(o['layers'])),[o['position_mm'],o['end_mm']])
   screen.added.append((o['net'],next(iter(o['layers'])),LineString([o['position_mm'],o['end_mm']])))
 for o in added:
  if o['kind']=='PCB_VIA':
   assert screen.via_legal(o['net'],o['position_mm']);screen.new_vias.append((o['net'],tuple(o['position_mm'])))
 assert {r['net'] for r in recipe['routes']}=={NET,'V3V3_IO'}
 for route in recipe['routes']:
  segments=[(face,p,q) for face,path in route['runs'] for p,q in zip(path,path[1:]) if math.dist(p,q)>1e-7]
  rows=[o for o in added if o['net']==route['net'] and o['kind']=='PCB_TRACK'];vias=[o for o in added if o['net']==route['net'] and o['kind']=='PCB_VIA']
  assert len(segments)==len(rows) and len(vias)==len(route['new_vias_mm'])
  assert all(any(face in o['layers'] and math.dist(p,o['position_mm'])<2e-6 and math.dist(q,o['end_mm'])<2e-6 for o in rows) for face,p,q in segments)
  assert all(any(math.dist(p,o['position_mm'])<2e-6 for o in vias) for p in route['new_vias_mm'])
 for name in ('conditional-assembly-review.json','visual-review.json'):
  path=out/name;r=json.loads(path.read_text());assert all(sha(Path(p))==h for p,h in r['source_sha256'].items());paths.append(path)
 paths += [cp,ROOT/'digital_via_spacing_v2.py',ROOT/'route_nf_surface.py',ROOT/'nf_minimum_logic.py',ROOT/'nf_pin_escape_routes.py',ROOT/'digital_native_spacing_search_v2.py']
 return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=delta,before_opens=44,after_opens=43,improved_nets=improved,regressed_pad_groups=[],component_move=recipe['component_move'],blank_before=oldnets[NET],blank_after=newnets[NET],supply_before=oldnets['V3V3_IO'],supply_after=newnets['V3V3_IO'],all_unretired_copper_exact=True,all_other_component_poses_exact=True,all_other_nets_exact=True,all_power_local_thermal_SD_clock_data_and_plane_checks_preserved=True,electrical_qualified=False,fabrication_released=False)
if __name__=='__main__':
 result=check()
 with (ROOT/'staging/digital-blank-pullup-native-01/blank-pullup-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('Exact LED_BLANK pull-up audit passes; 44 -> 43 opens; all parent pad groups retained')
