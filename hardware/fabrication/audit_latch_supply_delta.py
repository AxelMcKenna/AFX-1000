"""Verify the R3017 move, short source escape, replacement supply and leaf cleanup."""
import copy,json,math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,geometry_delta,native_evidence_errors
from hardware.fabrication.audit_blank_pullup_delta import check as parent_check
from hardware.fabrication.audit_digital_latch_supply import check as physical_check
from hardware.fabrication.digital_latch_supply_prune import prune
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search
ROOT=Path(__file__).resolve().parent
SRC='/LED/LATCH_5V_SRC';OUT='/LED/LATCH_5V';POWER='V3V3_IO';NETS={SRC,OUT,POWER}
REMOVED={'b5be175a-6407-420d-bdca-a534a938e3ed','01cacff9-0d3e-556c-8e9f-cf9880470dc8','27a32c70-e4ca-51c3-b910-fc4cb752068a','28dc0617-a379-50cb-9627-8bfe823e9dca','29f23fbc-2cb7-582f-8c4c-4bb0180eb357','6116c548-70bd-54e2-999c-bbb4f42d0217','96e3c929-704e-5f6b-81f3-654dd7b06838','a05782eb-ef4b-5fab-b65d-219f2ba3a789','a6c8b04f-db70-5c1a-9333-bedda29491f4'}
PRUNED={'0ee7e2d9-a618-4cf3-8bf0-3ebea5e3e5da','5a55d7bf-0c6a-5708-a398-170344198534','63e10b66-f37c-5d18-b586-7c7d333d4bbc','81da222a-c7c6-5283-9dbd-528e07d98e84','9cebdc4e-24b9-445a-aab5-66250ad3ca61','9f544b62-bfff-42cc-95d1-ceb65b2ca176','b0b1e014-82e8-5894-a76a-bc7a2a44c056'}
def refs(t):return {next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(t,'footprint')}
def copper(t):return {first(n,'uuid')[1]:n for tag in ('segment','via') for n in children(t,tag)}
def same_authored(a,b):
 d=geometry_delta(a,b);assert d['other_root_geometry_exact'] and all(d[t]==dict(added=[],removed=[],changed=[]) for t in ('footprint','segment','via','zone'))
def verify_delta(before,after,recipe,cleanup):
 old,new=refs(before),refs(after);assert old.keys()==new.keys()
 assert all(sexpr(f)==sexpr(new[r]) for r,f in old.items() if r!='R3017')
 moved=copy.deepcopy(new['R3017']);assert list(map(float,first(moved,'at')[1:3]))==[68.,25.] and list(map(float,first(old['R3017'],'at')[1:3]))==[75.,23.]
 moved[moved.index(first(moved,'at'))]=copy.deepcopy(first(old['R3017'],'at'));assert sexpr(moved)==sexpr(old['R3017'])
 assert recipe['component_move']['after_mm']==[68.,25.] and recipe['component_move']['after_side']=='B' and recipe['component_move']['after_angle']==0
 d=geometry_delta(before,after);assert d['other_root_geometry_exact']
 assert d['footprint']==dict(added=[],removed=[],changed=[first(old['R3017'],'uuid')[1]]) and d['zone']==dict(added=[],removed=[],changed=[])
 assert len(d['segment']['added'])==105 and len(d['via']['added'])==2
 assert not d['segment']['changed'] and not d['via']['changed']
 assert set(d['segment']['removed']+d['via']['removed'])==REMOVED|PRUNED and len(d['via']['removed'])==1
 assert set(recipe['removed_uuids'])==REMOVED and set(cleanup['removed_uuids'])==PRUNED
 prior=copper(before)
 for rec,expected in ((recipe,REMOVED),(cleanup,PRUNED)):
  assert {first(n,'uuid')[1] for n in rec['removed_objects']}==expected
  assert all(n==prior[first(n,'uuid')[1]] and first(n,'net')[1] in {OUT,POWER} for n in rec['removed_objects'])
 for tag in ('segment','via'):
  for n in children(after,tag):
   if first(n,'uuid')[1] not in d[tag]['added']:continue
   net=first(n,'net')[1];assert net in NETS
   if tag=='segment':assert float(first(n,'width')[1])==(.3 if net==POWER else .2) and first(n,'layer')[1] in ('F.Cu','B.Cu')
   else:assert net in {SRC,POWER} and float(first(n,'size')[1])==.6 and float(first(n,'drill')[1])==.3
 return d

def check():
 parent=ROOT/'staging/digital-blank-pullup-native-01';out=ROOT/'staging/digital-latch-supply-native-02';rd=ROOT/'staging/digital-latch-supply-repack-01';cd=ROOT/'staging/digital-latch-supply-clean-01';inter=ROOT/'staging/digital-latch-supply-native-01'
 rp=rd/'construction.json';clp=cd/'construction.json';recipe=json.loads(rp.read_text());cleanup=json.loads(clp.read_text())
 for r,p in ((recipe,rd),(cleanup,cd)):
  assert all(sha(Path(k))==v for k,v in r['source_sha256'].items()) and sha(p/'digital_core.kicad_pcb')==r['candidate_PCB_sha256']
 before,after=[read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (parent,out)]
 d=verify_delta(before,after,recipe,cleanup)
 initial=read_sexpr((rd/'digital_core.kicad_pcb').read_text());middle=read_sexpr((inter/'digital_core.kicad_pcb').read_text());clean=read_sexpr((cd/'digital_core.kicad_pcb').read_text())
 assert geometry_delta(before,initial)==recipe['geometry_delta'];same_authored(initial,middle);assert geometry_delta(middle,clean)==cleanup['geometry_delta'];same_authored(clean,after)
 pcp=ROOT/'staging/digital-latch-supply-prune-inputs-42/capture.json';prune_cap=json.loads(pcp.read_text());assert all(sha(Path(k))==v for k,v in prune_cap['source_sha256'].items())
 eligible={i for i,n in copper(before).items() if first(n,'net')[1] in {OUT,POWER}}
 removed,reasons=prune(prune_cap,eligible);assert removed==PRUNED and reasons==cleanup['reasons']
 pp=parent/'blank-pullup-review.json';assert parent_check()==json.loads(pp.read_text())
 physical=out/'corridor-audit.json';assert physical_check(out.name,'digital-latch-supply-inputs-42')==json.loads(physical.read_text())
 paths=[Path(__file__),rp,clp,rd/'digital_core.kicad_pcb',cd/'digital_core.kicad_pcb',inter/'digital_core.kicad_pcb',pcp,pp,physical,parent/'digital_core.kicad_pcb',out/'digital_core.kicad_pcb'];records=[]
 for folder,opens in ((parent,43),(out,42)):
  p=folder/'review.json';r=json.loads(p.read_text());assert not native_evidence_errors(folder/'digital_core.kicad_pro',r)
  assert r['status']['counts']==dict(violations=0,unconnected_items=opens,schematic_parity=0,erc=0)
  cp=folder/'stage-connectivity-review.json';c=json.loads(cp.read_text());assert all(sha(Path(k))==v for k,v in c['source_sha256'].items());records.append(c);paths += [p,cp]
 oldnets,newnets=[{r['net']:r for r in c['nets']} for c in records];assert oldnets.keys()==newnets.keys();improved=[]
 for net,old in oldnets.items():
  a=[set(map(tuple,g)) for g in old['pad_groups']];b=[set(map(tuple,g)) for g in newnets[net]['pad_groups']]
  assert set.union(*a)==set.union(*b) and all(any(g<=h for h in b) for g in a),net
  if len(b)<len(a):improved.append(net)
  if net not in NETS:assert newnets[net]==old,net
 assert improved==[SRC] and all(newnets[n]['all_pads_connected'] for n in NETS)
 assert math.isclose(newnets[SRC]['planar_copper_length_mm'],4.784980465165774,abs_tol=1e-5) and newnets[SRC]['via_count']==1
 cp=ROOT/'staging/digital-latch-supply-inputs-42/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(k))==v for k,v in cap['source_sha256'].items())
 ids=set(d['segment']['added']+d['via']['added']);added=[o for o in cap['objects'] if o['uuid'] in ids];assert len(added)==107
 signal_layers=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 for width in (.2,.3):
  surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=width;surface.MARGIN=.01
  screen=DigitalViaScreen(cap,signal_layers=signal_layers)
  for o in added:
   if o['kind']=='PCB_TRACK' and math.isclose(o['width_mm'],width):assert screen.legal(o['net'],next(iter(o['layers'])),[o['position_mm'],o['end_mm']])
 for o in added:
  if o['kind']=='PCB_VIA':
   work=copy.deepcopy(cap);work['objects']=[p for p in cap['objects'] if p['uuid']!=o['uuid']];screen=DigitalViaScreen(work,signal_layers=signal_layers);assert screen.via_legal(o['net'],o['position_mm'])
 assert {r['net'] for r in recipe['routes']}==NETS
 for route in recipe['routes']:
  segments=[(f,p,q) for f,path in route['runs'] for p,q in zip(path,path[1:]) if math.dist(p,q)>1e-7];rows=[o for o in added if o['net']==route['net'] and o['kind']=='PCB_TRACK'];vias=[o for o in added if o['net']==route['net'] and o['kind']=='PCB_VIA']
  assert len(segments)==len(rows) and len(vias)==len(route['new_vias_mm'])
  assert all(any(f in o['layers'] and math.dist(p,o['position_mm'])<2e-6 and math.dist(q,o['end_mm'])<2e-6 for o in rows) for f,p,q in segments)
  assert all(any(math.dist(p,o['position_mm'])<2e-6 for o in vias) for p in route['new_vias_mm'])
 for name in ('conditional-assembly-review.json','visual-review.json'):
  p=out/name;r=json.loads(p.read_text());assert all(sha(Path(k))==v for k,v in r['source_sha256'].items());paths.append(p)
 paths += [cp,ROOT/'digital_latch_supply_prune.py',ROOT/'digital_via_spacing_v2.py',ROOT/'route_nf_surface.py',ROOT/'nf_minimum_logic.py',ROOT/'nf_pin_escape_routes.py',ROOT/'digital_native_spacing_search_v3.py']
 return dict(source_sha256={str(p):sha(p) for p in paths},geometry_delta=d,component_move=recipe['component_move'],before_opens=43,after_opens=42,improved_nets=improved,regressed_pad_groups=[],net_before_after={n:dict(before=oldnets[n],after=newnets[n]) for n in sorted(NETS)},all_other_nets_exact=True,all_unretired_copper_and_other_component_poses_exact=True,all_power_local_thermal_SD_clock_data_and_plane_checks_preserved=True,electrical_qualified=False,fabrication_released=False)
if __name__=='__main__':
 result=check()
 with (ROOT/'staging/digital-latch-supply-native-02/latch-supply-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('Exact latch/supply audit passed; 43 -> 42 opens; all parent pad groups retained')
