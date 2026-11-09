"""Verify full replacement of two control nets and the added LED_22 connection."""
import copy,json,math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
from hardware.fabrication.audit_pot_filter_delta import check as parent_check
from hardware.fabrication.audit_digital_pot_filter import check as physical_check
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent
LED='/LED/LED_22';CONTROLS={'/CONTROLS/CONTROL_02','/CONTROLS/CONTROL_12'};NETS=CONTROLS|{LED}
def copper(tree):return {first(n,'uuid')[1]:n for tag in ('segment','via') for n in children(tree,tag)}

def verify_delta(before,after,recipe):
 d=geometry_delta(before,after);assert d==recipe['geometry_delta'] and d['other_root_geometry_exact']
 for tag in ('footprint','zone'):assert d[tag]==dict(added=[],removed=[],changed=[])
 assert len(d['segment']['added'])==24 and len(d['segment']['removed'])==19 and not d['segment']['changed']
 assert len(d['via']['added'])==3 and len(d['via']['removed'])==6 and not d['via']['changed']
 old,new=copper(before),copper(after)
 removed={i for i,n in old.items() if first(n,'net')[1] in CONTROLS}
 assert removed==set(d['segment']['removed']+d['via']['removed'])==set(recipe['removed_uuids'])
 assert {first(n,'uuid')[1] for n in recipe['removed_objects']}==removed
 assert all(n==old[first(n,'uuid')[1]] for n in recipe['removed_objects'])
 assert not any(first(n,'net')[1]==LED for n in old.values())
 for tag in ('segment','via'):
  for i in d[tag]['added']:
   n=new[i];assert first(n,'net')[1] in NETS
   if tag=='segment':assert float(first(n,'width')[1])==.2 and first(n,'layer')[1] in ('F.Cu','In3.Cu','In5.Cu','B.Cu')
   else:assert float(first(n,'size')[1])==.6 and float(first(n,'drill')[1])==.3
 return d

def check():
 parent=ROOT/'staging/digital-pot-filter-native-01';out=ROOT/'staging/digital-led-control-native-01';rd=ROOT/'staging/digital-led-control-escape-repair-01'
 rp=rd/'construction.json';recipe=json.loads(rp.read_text());assert all(sha(Path(p))==h for p,h in recipe['source_sha256'].items())
 candidate=rd/'digital_core.kicad_pcb';assert sha(candidate)==recipe['candidate_PCB_sha256']
 before,after=[read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (parent,out)]
 d=verify_delta(before,after,recipe)
 native_delta=geometry_delta(read_sexpr(candidate.read_text()),after);assert native_delta['other_root_geometry_exact']
 assert all(native_delta[t]==dict(added=[],removed=[],changed=[]) for t in ('footprint','segment','via','zone'))
 pp=parent/'pot-filter-review.json';physical=out/'corridor-audit.json'
 assert parent_check()==json.loads(pp.read_text())
 assert physical_check(out.name,'digital-led-control-inputs-39')==json.loads(physical.read_text())
 paths=[Path(__file__),rp,candidate,pp,physical];records=[]
 for folder,opens in ((parent,40),(out,39)):
  p=folder/'review.json';review=json.loads(p.read_text());assert not native_evidence_errors(folder/'digital_core.kicad_pro',review)
  assert review['status']['counts']==dict(violations=0,unconnected_items=opens,schematic_parity=0,erc=0)
  cp=folder/'stage-connectivity-review.json';w=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in w['source_sha256'].items());records.append(w);paths += [p,cp,folder/'digital_core.kicad_pcb']
 old,new=[{r['net']:r for r in w['nets']} for w in records];assert old.keys()==new.keys();improved=[]
 for net,prior in old.items():
  a,b=[[set(map(tuple,g)) for g in r['pad_groups']] for r in (prior,new[net])]
  assert set.union(*a)==set.union(*b) and all(any(g<=h for h in b) for g in a),net
  if len(b)<len(a):improved.append(net)
  if net not in NETS:assert new[net]==prior,net
 assert improved==[LED] and all(new[n]['all_pads_connected'] for n in NETS)
 assert records[1]['open_nets']==39 and sum(n.startswith('/LED/LED_') and not r['all_pads_connected'] for n,r in new.items())==33
 assert len(children(after,'segment'))==2773 and len(children(after,'via'))==477
 cp=ROOT/'staging/digital-led-control-inputs-39/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 ids=set(d['segment']['added']+d['via']['added']);added=[o for o in cap['objects'] if o['uuid'] in ids];assert len(added)==27
 surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01;faces=('F.Cu','In3.Cu','In5.Cu','B.Cu');screen=DigitalViaScreen(cap,signal_layers=faces)
 for o in added:
  if o['kind']=='PCB_TRACK':assert screen.legal(o['net'],next(iter(o['layers'])),[o['position_mm'],o['end_mm']])
  else:
   work=copy.deepcopy(cap);work['objects']=[p for p in cap['objects'] if p['uuid']!=o['uuid']]
   assert DigitalViaScreen(work,signal_layers=faces).via_legal(o['net'],o['position_mm'])
 for net in NETS:
  routes=[r for r in recipe['routes'] if r['net']==net]
  segments=[(f,p,q) for r in routes for f,path in r['runs'] for p,q in zip(path,path[1:]) if math.dist(p,q)>1e-7]
  points=[p for r in routes for p in r['new_vias_mm']]
  tracks=[o for o in added if o['net']==net and o['kind']=='PCB_TRACK'];vias=[o for o in added if o['net']==net and o['kind']=='PCB_VIA']
  assert len(segments)==len(tracks) and len(points)==len(vias)==1
  assert all(any(f in o['layers'] and math.dist(p,o['position_mm'])<2e-6 and math.dist(q,o['end_mm'])<2e-6 for o in tracks) for f,p,q in segments)
  assert all(any(math.dist(p,o['position_mm'])<2e-6 for o in vias) for p in points)
  assert math.isclose(new[net]['planar_copper_length_mm'],sum(r['planar_length_mm'] for r in routes),abs_tol=1e-5) and new[net]['via_count']==1
 for name in ('conditional-assembly-review.json','visual-review.json'):
  p=out/name;r=json.loads(p.read_text());assert all(sha(Path(k))==v for k,v in r['source_sha256'].items());paths.append(p)
 paths += [cp]+[ROOT/n for n in ('digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_pin_escape_routes.py','digital_native_spacing_search_v3.py')]
 return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=d,before_opens=40,after_opens=39,improved_nets=improved,regressed_pad_groups=[],net_before_after={n:dict(before=old[n],after=new[n]) for n in sorted(NETS)},all_other_net_records_exact=True,all_component_poses_and_unretired_copper_exact=True,power_local_thermal_SD_and_planes_preserved=True,signal_integrity_loading_and_installed_performance_qualified=False,fabrication_released=False)
if __name__=='__main__':
 result=check()
 with (ROOT/'staging/digital-led-control-native-01/led-control-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('Exact LED/control audit passed; 40 -> 39 opens; both control nets restored')
