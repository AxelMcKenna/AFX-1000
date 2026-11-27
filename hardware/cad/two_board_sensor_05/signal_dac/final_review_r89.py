"""Fail-closed acceptance gate for the bounded r89 DAC routing checkpoint."""
import ast,hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[R/'native-r89/review.json',R/'native-r89/drc.json',R/'native-r89/erc.json',R/'native-r89/object-delta.json',R/'native-r89/netlist.xml',R/'capture-r89/capture.json',R/'reference-review-r89.json',R/'transitions-r89.json',R/'fidelity-r89.json',R/'native-r89/added-via-drill-review.json',R/'capture-r89/precision.json',R/'candidate-r89/routing.json',R/'preview-r89.json',R/'preview-r89.png',R/'REFERENCE-POLICY.md',R/'failure-r85.txt',REPO/'hardware/electronics/adc_driver/revision2/README.md',REPO/'hardware/electronics/adc_driver/revision2/integration.json',REPO/'hardware/electronics/adc_driver/revision2/components.json',R/'replacement-audit-r89.json',R/'test_bounded_path.py',R/'test_visibility_path.py',R/'test_copper_inventory.py',R/'test_sensitive_placement.py',R/'test_return_paths.py',R/'test_reference_gate_r89.py',R/'run_linux.py',R/'capture_precision_r89.py',Path(__file__),R/'verify_portable_r89.py',R/'CHECKPOINT-R89.md',R/'SELF-REVIEW-R89.md']
# Keep the accepted board usable with the exact native project/rule/library inputs.
for p in (R/'native-r89').rglob('*'):
 if not p.is_file():continue
 relative=p.relative_to(R/'native-r89')
 if p.suffix in ['.kicad_sch','.kicad_pro','.kicad_dru']or p.name in ['sym-lib-table','fp-lib-table']or relative.parts[0]in ['libraries','symbols']:
  baseline=R.parent/'signal_input/native-r7'/relative
  assert baseline.is_file()and sha(p)==sha(baseline),('changed native project dependency',p)
  paths.append(p)
closure={};queue=list(paths)
while queue:
 p=queue.pop().resolve()
 if str(p)in closure:continue
 closure[str(p)]=sha(p)
 if p.suffix=='.py':
  # Bind local Python imports used by the native capture and verification code.
  for node in ast.walk(ast.parse(p.read_text())):
   modules=[]
   if isinstance(node,ast.Import):modules=[alias.name for alias in node.names]
   elif isinstance(node,ast.ImportFrom):
    if node.level:
     package=list(p.relative_to(REPO).parts[:-1]);package=package[:len(package)-node.level+1]
     prefix='.'.join([*package,*((node.module or '').split('.')if node.module else[])])
    else:prefix=node.module or ''
    modules=[prefix,*[prefix+'.'+alias.name for alias in node.names if alias.name!='*']]
   for module in modules:
    if not module.startswith('hardware.'):continue
    parts=module.split('.')
    candidates=[REPO.joinpath(*parts).with_suffix('.py'),*[REPO.joinpath(*parts[:i],'__init__.py')for i in range(1,len(parts)+1)]]
    queue.extend(candidate for candidate in candidates if candidate.is_file())
 if p.suffix!='.json'or not p.is_relative_to(R):continue
 doc=read(p)
 if not isinstance(doc,dict):continue
 for key,bindings in doc.items():
  if not key.endswith('source_sha256')or not isinstance(bindings,dict):continue
  for name,digest in bindings.items():
   dependency=Path(name);dependency=dependency if dependency.is_absolute()else REPO/dependency
   assert sha(dependency)==digest,('stale source',p,dependency)
   queue.append(dependency)
native=read(R/'native-r89/review.json');drc=read(R/'native-r89/drc.json');erc=read(R/'native-r89/erc.json');cap=read(R/'capture-r89/capture.json');ref=read(R/'reference-review-r89.json');tr=read(R/'transitions-r89.json');fid=read(R/'fidelity-r89.json');drill=read(R/'native-r89/added-via-drill-review.json');routing=read(R/'candidate-r89/routing.json');old_drc=read(R.parent/'signal_input/native-r7/drc.json')
assert not drc['violations']and not drc['ignored_checks']and not erc['ignored_checks']and not any(s['violations']for s in erc['sheets'])
assert drc['schematic_parity']==old_drc['schematic_parity']and len(drc['schematic_parity'])==1
assert native['exact_all_netlist_partitions']and native['old_objects_unchanged_except_exact_agent_rework']
assert set(read(R/'native-r89/object-delta.json')['changed_old_objects'])=={x['uuid']for x in routing['declared_removed_since_r83']}
replacement=read(R/'replacement-audit-r89.json')
assert replacement['original_copper_unchanged']and replacement['all_r83_authored_objects_unchanged']and replacement['all_r83_native_groups_preserved']
assert replacement['removed_agent_copper']==[] and sum(len(m['before_groups'])-1 for m in replacement['new_group_merges'])==10
assert len(replacement['new_routes'])==18 and all(row['net']in routing['ADC_selected_nets']for row in replacement['new_routes'])
assert len(drc['unconnected_items'])==cap['native_uncapped_opens']==cap['independent_sum_of_pad_cluster_gaps']==routing['expected_opens']==177
assert cap['footprints_captured']==477
from hardware.electronics.common.sexpr import read_sexpr,children,sexpr
old_tree=read_sexpr((R.parent/'signal_input/native-r7/signal_main.kicad_pcb').read_text());new_tree=read_sexpr((R/'native-r89/signal_main.kicad_pcb').read_text())
moves=routing['moves'];assert len(moves)==2
assert moves[0]['reference']=='A_R303' and moves[0]['before_mm']==[120,73] and moves[0]['after_mm']==[109,82.5] and moves[0]['side']=='F.Cu'
assert moves[1]['reference']=='A_R308' and moves[1]['before_mm']==[116,68] and moves[1]['after_mm']==[120.5,81] and moves[1]['side']=='F.Cu'
from hardware.electronics.common.sexpr import first
old_fp={first(x,'uuid')[1]:x for x in children(old_tree,'footprint')};new_fp={first(x,'uuid')[1]:x for x in children(new_tree,'footprint')}
assert set(old_fp)==set(new_fp) and len(old_fp)==477
for uid,footprint in old_fp.items():
 for move in moves:
  if uid==move['uuid']:first(footprint,'at')[1:3]=move['after_mm']
 assert sexpr(footprint)==sexpr(new_fp[uid]),('undeclared footprint change',uid)
old_zones={first(x,'uuid')[1]:x for x in children(old_tree,'zone')};new_zones={first(x,'uuid')[1]:x for x in children(new_tree,'zone')}
for uid,z in old_zones.items():
 def authored(row):return sexpr([x for x in row if not(isinstance(x,list)and x and x[0]=='filled_polygon')])
 assert uid in new_zones and authored(z)==authored(new_zones[uid]),('modified original zone',uid)
new_keepouts={uid for uid,z in new_zones.items()if uid not in old_zones and children(z,'keepout')}
assert new_keepouts=={x['zone_uuid']for x in routing['supplemental_lowcap_exclusions']} and len(new_keepouts)==1
assert len(ref['verified_transported_pad_exclusions'])==1
for tag in ['general','layers','setup']:
 assert [sexpr(v)for v in children(old_tree,tag)]==[sexpr(v)for v in children(new_tree,tag)],('changed board settings',tag)
assert ref['all_original_native_groups_preserved']and sum(len(m['old_groups'])-1 for m in ref['only_approved_net_groups_merged'])==53
assert all(x['unexplained_uncovered_mm2']<1e-6 for x in ref['new_reference_cases'])and all(x['unexplained_loss_mm2']<1e-6 for x in ref['retained_reference_cases'])
assert len({x['signal_uuid']for x in tr['transitions']})==len(tr['transitions'])==57
assert all(x['verified_return_corridor_length_mm']<=2.5+1e-9 and all(v<1e-6 for v in x['corridor_uncovered_mm2'].values())for x in tr['transitions'])
assert fid['pass']and len(fid['cases'])==214
assert len(drill['new_or_replaced_vias'])==84 and drill['minimum_gap_mm']>=.1
remaining=[v for v in drc['unconnected_items']if '/A_DAC/'in json.dumps(v)];assert len(remaining)==0
nets=sorted({n for v in remaining for n in re.findall(r'\[(/A_DAC/[^\]]+)\]',json.dumps(v))})
assert set(nets)=={b['net']for b in routing['blocked']}
report={'accepted_bounded_geometry_checkpoint':True,'selected_pcb':str((R/'native-r89/signal_main.kicad_pcb').relative_to(REPO)),'selected_pcb_sha256':sha(R/'native-r89/signal_main.kicad_pcb'),'baseline_native_opens':230,'native_opens':177,'new_cluster_joins':53,'footprints_unchanged':475,'verified_passive_translations':moves,'mechanical_freshness_requires_integration':True,'new_route_reference_cases':len(ref['new_reference_cases']),'retained_reference_cases':len(ref['retained_reference_cases']),'local_return_cases':57,'raw_zone_fidelity_cases':214,'new_drill_cases':84,'minimum_new_drill_to_SMD_copper_mm':drill['minimum_gap_mm'],'remaining_DAC_connections':remaining,'remaining_DAC_nets':nets,'retained_missing_footprint_finding':drc['schematic_parity'],'ADC_control_added_trace_length_mm':replacement['new_trace_length_mm'],'exact_replacement_and_geometry_context':'replacement-audit-r89.json','reference_policy':'REFERENCE-POLICY.md','raw_reference_changes_retained_in':'reference-review-r89.json','modeled_DAC_connections_complete':True,'full_DAC_routing_complete':False,'noise_stability_crosstalk_qualified':False,'fabrication_released':False,'source_sha256':{str(Path(p).relative_to(REPO)):h for p,h in sorted(closure.items())}}
(R/'final-review-r89.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['source_sha256','remaining_DAC_connections']},indent=2));print('Verified closure files',len(closure))
