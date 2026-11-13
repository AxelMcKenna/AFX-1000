"""Exact three-object replacement scope, group identity and retired-reference mapping."""
import collections,hashlib,json
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def objects(p):
 t=read_sexpr(p.read_text());return t,{first(row,'uuid')[1]:sexpr([v for v in row if not(isinstance(v,list)and v and v[0]=='filled_polygon')])for row in t if isinstance(row,list)and children(row,'uuid')}
r=read(R/'candidate-r148/routing.json');b=read(R/'capture-r139/capture.json');c=read(R/'capture-r148/capture.json');prior=read(R/'reference-review-r139.json');ref=read(R/'reference-review-r148.json');expected={'b1c1865b-7772-58be-ab73-298eb697dc74','094cfe15-e54e-5a1a-86f3-64eb7dd586b8','e278094b-72b0-5e04-90d5-578081219fd8'}
bt,old=objects(R/'native-r139/signal_main.kicad_pcb');nt,new=objects(R/'native-r148/signal_main.kicad_pcb');assert {x['uuid']for x in r['declared_removed']}==expected;assert set(old)-set(new)==expected;assert all(new[u]==v for u,v in old.items()if u not in expected)
for tag in ['general','layers','setup']:assert [sexpr(v)for v in children(bt,tag)]==[sexpr(v)for v in children(nt,tag)]
assert len(children(nt,'footprint'))==477 and sha(R/'native-r139/signal_main.kicad_dru')==sha(R/'native-r148/signal_main.kicad_dru')
added_ids={u for row in r['routes']for u in row['added_track_uuids']}|{x['uuid']for key in ['vias','new_ground_vias','new_reference_zones']for x in r[key]};assert set(new)-set(old)==added_ids
before={o['uuid']:o for o in b['objects']};after={o['uuid']:o for o in c['objects']};membership={u:k for k,vs in c['all_groups'].items()for u in vs};destinations={};merges=collections.defaultdict(list)
for gid,vs in b['all_groups'].items():
 dst={membership[u]for u in vs if u not in expected};assert len(dst)==1,(gid,dst);destinations[gid]=next(iter(dst));merges[next(iter(dst))].append(gid)
joined=[{'net':before[b['all_groups'][groups[0]][0]]['net'],'before_groups':groups,'after_group':gid}for gid,groups in merges.items()if len(groups)>1];assert len(joined)==1 and joined[0]['net']=='/A_ADC/PD_R'and len(joined[0]['before_groups'])==2
assert c['native_uncapped_opens']==c['independent_sum_of_pad_cluster_gaps']==162
replacements=[]
for row in r['routes']:
 for uid,p,q in zip(row['added_track_uuids'],row['path_mm'],row['path_mm'][1:]):
  o=after[uid];assert o['kind']=='PCB_TRACK'and o['net']==row['net']and list(o['layers'])==[row['layer']]and o['width_mm']==row['width_mm']and o['position_mm']==p and o['end_mm']==q
 if row['role']!='authorized obstacle replacement':continue
 oldtrack=before[row['replaced_original_uuid']];assert oldtrack['uuid']in expected and row['path_mm'][0]==oldtrack['position_mm']and row['path_mm'][-1]==oldtrack['end_mm'];assert row['width_mm']>=oldtrack['width_mm']and row['net']==oldtrack['net']and[row['layer']]==list(oldtrack['layers']);assert all(after[u]['group']==destinations[oldtrack['group']]for u in row['added_track_uuids'])
 coverage=next(v for v in ref['new_reference_cases']if v['name']==row['net']+' authorized obstacle replacement');assert coverage['unexplained_uncovered_mm2']<1e-6
 replacements.append({'retired_uuid':oldtrack['uuid'],'net':row['net'],'layer':row['layer'],'width_mm':row['width_mm'],'preserved_remote_endpoints_mm':[oldtrack['position_mm'],oldtrack['end_mm']],'replacement_track_uuids':row['added_track_uuids'],'native_group':destinations[oldtrack['group']],'before_length_mm':LineString([oldtrack['position_mm'],oldtrack['end_mm']]).length,'after_length_mm':LineString(row['path_mm']).length,'reference_case':coverage})
oldcases={v['uuid']:v for v in prior['retained_reference_cases']};newcases={v['uuid']:v for v in ref['retained_reference_cases']};retired=set(oldcases)-set(newcases);assert retired==expected&set(oldcases)and len(retired)==2 and not(set(newcases)-set(oldcases));mapped=[]
for uid in sorted(retired):
 replacement=next(x for x in replacements if x['retired_uuid']==uid);mapped.append({'retired_reference_case':oldcases[uid],'exact_replacement':replacement});assert replacement['reference_case']['raw_uncovered_mm2']<1e-6,replacement
for v in r['vias']+r['new_ground_vias']:
 o=after[v['uuid']];assert o['kind']=='PCB_VIA'and o['net']==v['net']and o['position_mm']==v['at']and o['width_mm']==.6 and o['drill_mm']==.3
main=next(o['group']for o in c['objects']if o.get('ref')=='D_U1001'and o.get('pin')=='20');assert all(after[v['uuid']]['group']==main for v in r['new_ground_vias'])
paths=[Path(__file__),R/'native-r139/signal_main.kicad_pcb',R/'native-r148/signal_main.kicad_pcb',R/'native-r139/signal_main.kicad_dru',R/'native-r148/signal_main.kicad_dru',R/'candidate-r148/routing.json',R/'capture-r139/capture.json',R/'capture-r148/capture.json',R/'reference-review-r139.json',R/'reference-review-r148.json']
report={'pass':True,'source_sha256':{str(p.relative_to(REPO)):sha(p)for p in paths},'exact_authorized_replacements':replacements,'exact_retired_reference_mapping':mapped,'all_other_authored_objects_unchanged':True,'all_477_footprints_unchanged':True,'native_mount_keepouts_and_rules_unchanged':True,'exact_group_joins':joined,'signal_join_length_mm':sum(LineString(x['path_mm']).length for x in r['routes']if x['net']=='/A_ADC/PD_R'),'new_reference_cases':len(ref['new_reference_cases']),'retained_reference_cases':len(newcases),'retired_cases_with_exact_replacement_proof':len(mapped),'new_pose_changes':[],'noise_stability_qualified':False,'fabrication_released':False}
(R/'replacement-audit-r148.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS exact three replacements, two mapped original reference cases, one PD_R join')
