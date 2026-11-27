"""Portable, source-bound acceptance of the two additive buffered-reference joins."""
import ast,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3];OWNER=Path('/private/tmp/rmx-lever-sensor-20261112')
def local(value):
 p=Path(value)
 if p.is_absolute():
  assert p.is_relative_to(OWNER)or p.is_relative_to(REPO),('external source',p)
  if p.is_relative_to(OWNER):p=REPO/p.relative_to(OWNER)
 else:p=REPO/p
 return p

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
native=read(R/'native-r131/review.json');drc=read(R/'native-r131/drc.json');erc=read(R/'native-r131/erc.json');cap=read(R/'capture-r131/capture.json');ref=read(R/'reference-review-r131.json');tr=read(R/'transitions-r131.json');fid=read(R/'fidelity-r131.json');drill=read(R/'native-r131/added-via-drill-review.json');mount=read(R/'mount-audit-r107.json');replacement=read(R/'replacement-audit-r125.json');surface=read(R/'surface-audit-r131.json');tests=read(R/'keepout-tests-r107/review.json')
assert not drc['violations']and not drc['ignored_checks']and not erc['ignored_checks']and not any(s['violations']for s in erc['sheets'])
assert drc['schematic_parity']==read(R/'native-r125/drc.json')['schematic_parity']
assert native['exact_all_netlist_partitions']and native['old_objects_unchanged_except_exact_agent_rework']
assert len(drc['unconnected_items'])==cap['native_uncapped_opens']==cap['independent_sum_of_pad_cluster_gaps']==164
assert surface['all_existing_authored_objects_unchanged']and surface['all_477_footprints_unchanged_since_r125']and surface['native_mount_keepouts_and_rules_unchanged']and surface['no_new_vias']
assert cap['footprints_captured']==477 and replacement['old_footprints_unchanged']==476 and replacement['all_other_authored_objects_unchanged']and replacement['all_r107_hardware_keepouts_and_native_rules_unchanged']
assert len(mount['exact_removed_original_copper'])==5 and len(mount['mounts'])==9
assert len(ref['new_reference_cases'])==135 and len(ref['retained_reference_cases'])==4873
assert all(x['unexplained_uncovered_mm2']<1e-6 for x in ref['new_reference_cases'])and all(x['unexplained_loss_mm2']<1e-6 for x in ref['retained_reference_cases'])
assert len({x['signal_uuid']for x in tr['transitions']})==len(tr['transitions'])==67
assert all(x['verified_return_corridor_length_mm']<=2.5+1e-9 and all(v<1e-6 for v in x['corridor_uncovered_mm2'].values())for x in tr['transitions'])
assert fid['pass']and len(fid['cases'])==238
assert len(drill['new_or_replaced_vias'])==99 and drill['minimum_gap_mm']>=.1
assert {x['case']for x in tests['tests']}=={'track','via','smd_pad','npth_annulus'}and all(x['caught']for x in tests['tests'])
paths=[Path(__file__),R/'verify_portable_r131.py',R/'CHECKPOINT-R131.md',R/'SELF-REVIEW-R131.md',R/'final-review-r125.json',R/'native-r131/review.json',R/'native-r131/drc.json',R/'native-r131/erc.json',R/'native-r131/object-delta.json',R/'native-r131/netlist.xml',R/'capture-r131/capture.json',R/'capture-r131/precision.json',R/'capture_bundle_r131.py',R/'reference-review-r131.json',R/'transitions-r131.json',R/'fidelity-r131.json',R/'native-r131/added-via-drill-review.json',R/'mount-audit-r107.json',R/'replacement-audit-r125.json',R/'surface-audit-r131.json',R/'keepout-tests-r107/review.json',R/'run_linux.py']
# Enumerate immutable project dependencies from the accepted ancestor manifest,
# never from the current directory contents.
ancestor=read(R/'final-review-r125.json');prefix=str((R/'native-r125').relative_to(REPO))+'/'
for name in ancestor['source_sha256']:
 if not name.startswith(prefix):continue
 rel=Path(name.removeprefix(prefix));p=R/'native-r131'/rel
 if p.suffix in ['.kicad_sch','.kicad_pro','.kicad_dru']or p.name in ['sym-lib-table','fp-lib-table']or rel.parts[0]in ['libraries','symbols']:
  if p.suffix=='.kicad_dru':assert sha(p)==sha(R/'candidate-r131'/rel)
  else:assert sha(p)==sha(R/'native-r125'/rel)
  paths.append(p)
for test in tests['tests']:
 observed=read(R/'keepout-tests-r107'/test['case']/'drc.json');assert all(x in observed['violations']for x in test['caught'])
 paths.extend(R/'keepout-tests-r107'/test['case']/name for name in ['drc.json','run.log','signal_main.kicad_pcb','signal_main.kicad_pro','signal_main.kicad_dru'])
contract=REPO/'hardware/cad/assembly_workflow/verification/main-fasteners-r1'
paths.extend(contract/name for name in ['contact-keepouts.json','copper-screen.json','source-review.json'])
paths.append(R/'test_portable_closure_r131.py')
closure={};queue=list(paths)
while queue:
 p=queue.pop();p=local(p).resolve();name=str(p.relative_to(REPO))
 if name in closure:continue
 closure[name]=sha(p)
 if p.suffix=='.py':
  for node in ast.walk(ast.parse(p.read_text())):
   modules=[]
   if isinstance(node,ast.Import):modules=[v.name for v in node.names]
   elif isinstance(node,ast.ImportFrom)and node.module and not node.level:modules=[node.module,*[node.module+'.'+v.name for v in node.names]]
   for module in modules:
    if not module.startswith('hardware.'):continue
    parts=module.split('.');candidates=[REPO.joinpath(*parts).with_suffix('.py'),*[REPO.joinpath(*parts[:i],'__init__.py')for i in range(1,len(parts)+1)]];queue.extend(x for x in candidates if x.is_file())
 if p.suffix=='.json'and (p.is_relative_to(R.parent)or p.is_relative_to(contract)):
  doc=read(p)
  if isinstance(doc,dict):
   for binding in doc.get('source_pcbs',{}).values():
    dep=local(binding['path']);assert sha(dep)==binding['sha256'],('stale contract PCB',dep);queue.append(dep)
   for binding in doc.get('boards',{}).values():
    if isinstance(binding,dict)and 'source_pcb'in binding:
     dep=local(binding['source_pcb']);assert sha(dep)==binding['source_pcb_sha256'],('stale screened PCB',dep);queue.append(dep)
   for key,bindings in doc.items():
    if key.endswith('source_sha256')and isinstance(bindings,dict):
     for dependency,digest in bindings.items():
      dep=local(dependency);assert sha(dep)==digest,('stale source',p,dep);queue.append(dep)
report={'accepted_bounded_geometry_checkpoint':True,'selected_by_root':False,'selected_pcb':str((R/'native-r131/signal_main.kicad_pcb').relative_to(REPO)),'selected_pcb_sha256':sha(R/'native-r131/signal_main.kicad_pcb'),'native_opens':164,'exact_original_copper_replacements':[],'exact_footprint_change':None,'cumulative_physical_moves':replacement['cumulative_moves_from_input_r7'],'footprints_unchanged_since_r125':477,'native_mount_keepouts':9,'inherited_native_keepout_negative_tests':4,'new_route_reference_cases':135,'retained_reference_cases':4873,'local_return_cases':67,'raw_zone_fidelity_cases':238,'new_drill_cases':99,'minimum_drill_to_SMD_copper_mm':drill['minimum_gap_mm'],'missing_ESS_footprint_retained':drc['schematic_parity'],'mechanical_integration_pending':True,'noise_stability_qualified':False,'fabrication_released':False,'source_sha256':dict(sorted(closure.items()))}
(R/'final-review-r131.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS r131 complete gate; closure',len(closure))
