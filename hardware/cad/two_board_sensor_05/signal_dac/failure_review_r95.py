"""Fail-closed acceptance gate for the bounded r95 DAC routing checkpoint."""
import ast,hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[R/'native-r95/review.json',R/'native-r95/drc.json',R/'native-r95/erc.json',R/'native-r95/object-delta.json',R/'native-r95/netlist.xml',R/'capture-r95/capture.json',R/'reference-review-r95.json',R/'transitions-r95.json',R/'fidelity-r95.json',R/'native-r95/added-via-drill-review.json',R/'capture-r95/precision.json',R/'candidate-r95/routing.json',R/'replacement-audit-r95.json',R/'failure-r95.txt',R/'HOLD-R95.md',R/'run_linux.py',R/'capture_precision_r95.py',R/'verify_failed_r95.py',Path(__file__),REPO/'hardware/electronics/adc_driver/revision2/README.md',REPO/'hardware/electronics/adc_driver/revision2/integration.json']
# Keep the accepted board usable with the exact native project/rule/library inputs.
for p in (R/'native-r95').rglob('*'):
 if not p.is_file():continue
 relative=p.relative_to(R/'native-r95')
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

drc=read(R/'native-r95/drc.json');native=read(R/'native-r95/review.json');cap=read(R/'capture-r95/capture.json');ref=read(R/'reference-review-r95.json');tr=read(R/'transitions-r95.json');fid=read(R/'fidelity-r95.json');drill=read(R/'native-r95/added-via-drill-review.json');replacement=read(R/'replacement-audit-r95.json')
assert not drc['violations'] and not drc['ignored_checks']
assert len(drc['unconnected_items'])==cap['native_uncapped_opens']==cap['independent_sum_of_pad_cluster_gaps']==167
assert native['exact_all_netlist_partitions'] and native['old_objects_unchanged_except_exact_agent_rework']
assert replacement['original_copper_unchanged'] and replacement['all_r89_authored_objects_unchanged'] and replacement['all_r89_native_groups_preserved'] and replacement['removed_agent_copper']==[]
assert len(tr['transitions'])==65 and all(x['verified_return_corridor_length_mm']<=2.5+1e-9 and all(v<1e-6 for v in x['corridor_uncovered_mm2'].values())for x in tr['transitions'])
assert fid['pass'] and len(fid['cases'])==225 and len(drill['new_or_replaced_vias'])==96 and drill['minimum_gap_mm']>=.1
failed=[row for row in ref['new_reference_cases']if row['unexplained_uncovered_mm2']>=1e-6]
assert len(failed)==1 and failed[0]['name']=='/A_ADC/PD_R escape' and failed[0]['layer']=='F.Cu'
assert failed[0]['unexplained_uncovered_mm2']==0.00010027711015885879
assert all(x['unexplained_loss_mm2']<1e-6 for x in ref['retained_reference_cases'])
report={'accepted':False,'selected_checkpoint_remains':'r89','selected_native_opens':177,'candidate_native_opens':167,'candidate_pcb_sha256':sha(R/'native-r95/signal_main.kicad_pcb'),'failed_new_reference_cases':failed,'new_reference_cases':len(ref['new_reference_cases']),'retained_reference_cases':len(ref['retained_reference_cases']),'all_retained_reference_cases_pass':True,'local_return_cases':65,'raw_fill_fidelity_cases':225,'new_drill_cases':96,'all_r89_copper_and_poses_preserved':True,'design_hold':'User requested efficient workflow before further design; no geometry repair attempted after this failed validation.','fabrication_released':False,'noise_stability_crosstalk_qualified':False,'source_sha256':{str(Path(p).relative_to(REPO)):h for p,h in sorted(closure.items())}}
(R/'failed-checkpoint-r95.json').write_text(json.dumps(report,indent=2)+'\n');print('Bound rejected r95 checkpoint; r89 remains accepted; closure',len(closure))
