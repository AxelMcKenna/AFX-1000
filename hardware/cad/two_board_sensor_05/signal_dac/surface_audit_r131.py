"""Exact additive inventory and two native group joins; no changed physical poses."""
import collections,hashlib,json,math
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def objects(p):
 t=read_sexpr(p.read_text());out={}
 for row in t:
  if isinstance(row,list)and children(row,'uuid'):out[first(row,'uuid')[1]]=sexpr([v for v in row if not(isinstance(v,list)and v and v[0]=='filled_polygon')])
 return t,out
bt,old=objects(R/'native-r125/signal_main.kicad_pcb');nt,new=objects(R/'native-r131/signal_main.kicad_pcb');assert all(new.get(u)==v for u,v in old.items());assert len(new)-len(old)==7
for tag in ['general','layers','setup']:assert [sexpr(v)for v in children(bt,tag)]==[sexpr(v)for v in children(nt,tag)]
assert len(children(nt,'footprint'))==477
assert sha(R/'native-r125/signal_main.kicad_dru')==sha(R/'native-r131/signal_main.kicad_dru')
r=read(R/'candidate-r131/routing.json');b=read(R/'capture-r125/capture.json');c=read(R/'capture-r131/capture.json');before={o['uuid']:o for o in b['objects']};after={o['uuid']:o for o in c['objects']};added=[o for u,o in after.items()if u not in before];assert len(added)==7 and all(o['kind']=='PCB_TRACK'for o in added)
for route in r['routes']:
 for p,q in zip(route['path_mm'],route['path_mm'][1:]):assert sum(o['net']==route['net']and list(o['layers'])==['F.Cu']and o['width_mm']==.2 and o['position_mm']==[round(v,6)for v in p]and o['end_mm']==[round(v,6)for v in q]for o in added)==1
membership={u:k for k,vs in c['all_groups'].items()for u in vs};merges=collections.defaultdict(list)
for gid,vs in b['all_groups'].items():
 dst={membership[u]for u in vs};assert len(dst)==1,(gid,dst);merges[next(iter(dst))].append(gid)
assert len(merges)==len(c['all_groups']);joined=[{'net':before[b['all_groups'][groups[0]][0]]['net'],'before_groups':groups,'after_group':gid}for gid,groups in merges.items()if len(groups)>1];assert len(joined)==2 and {x['net']for x in joined}=={'/A_ADC/REF_HALF_L','/A_ADC/REF_HALF_R'}and all(len(x['before_groups'])==2 for x in joined)
assert c['native_uncapped_opens']==c['independent_sum_of_pad_cluster_gaps']==164
prior=read(R/'reference-review-r125.json');ref=read(R/'reference-review-r131.json');assert {x['uuid']for x in prior['retained_reference_cases']}=={x['uuid']for x in ref['retained_reference_cases']}
paths=[Path(__file__),R/'native-r125/signal_main.kicad_pcb',R/'native-r131/signal_main.kicad_pcb',R/'native-r125/signal_main.kicad_dru',R/'native-r131/signal_main.kicad_dru',R/'candidate-r131/routing.json',R/'capture-r125/capture.json',R/'capture-r131/capture.json',R/'reference-review-r125.json',R/'reference-review-r131.json',R/'replacement-audit-r125.json']
report={'source_sha256':{str(p.relative_to(REPO)):sha(p)for p in paths},'all_existing_authored_objects_unchanged':True,'all_477_footprints_unchanged_since_r125':True,'native_mount_keepouts_and_rules_unchanged':True,'no_original_copper_or_zone_rework':True,'no_new_vias':True,'added_track_uuids':sorted(o['uuid']for o in added),'exact_group_joins':joined,'retained_reference_case_identities_unchanged':True,'signal_lengths_mm':{x['net']:x['trace_length_mm']for x in r['routes']},'cumulative_physical_capture':'replacement-audit-r125.json','new_pose_changes':[],'inherited_D101_C105_receiving_gap_mm':.02,'manufacturing_placement_tolerance_qualified':False,'noise_stability_qualified':False,'fabrication_released':False}
(R/'surface-audit-r131.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS seven added tracks / two exact joins / all477 poses and all existing authored objects unchanged')
