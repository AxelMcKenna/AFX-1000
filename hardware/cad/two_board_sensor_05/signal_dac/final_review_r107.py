"""Portable, source-bound acceptance of the exact D_H4 mount repair."""
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
native=read(R/'native-r107/review.json');drc=read(R/'native-r107/drc.json');erc=read(R/'native-r107/erc.json');cap=read(R/'capture-r107/capture.json');ref=read(R/'reference-review-r107.json');tr=read(R/'transitions-r107.json');fid=read(R/'fidelity-r107.json');drill=read(R/'native-r107/added-via-drill-review.json');mount=read(R/'mount-audit-r107.json');tests=read(R/'keepout-tests-r107/review.json')
assert not drc['violations']and not drc['ignored_checks']and not erc['ignored_checks']and not any(s['violations']for s in erc['sheets'])
assert drc['schematic_parity']==read(R/'native-r98/drc.json')['schematic_parity']
assert native['exact_all_netlist_partitions']and native['old_objects_unchanged_except_exact_agent_rework']
assert len(drc['unconnected_items'])==cap['native_uncapped_opens']==cap['independent_sum_of_pad_cluster_gaps']==167
assert cap['footprints_captured']==477 and mount['all_477_footprints_unchanged']and mount['all_other_authored_objects_unchanged']and mount['all_r98_native_partitions_preserved_without_merges_or_splits']
assert len(mount['exact_removed_original_copper'])==5 and len(mount['mounts'])==9
assert len(ref['new_reference_cases'])==130 and len(ref['retained_reference_cases'])==4873
assert all(x['unexplained_uncovered_mm2']<1e-6 for x in ref['new_reference_cases'])and all(x['unexplained_loss_mm2']<1e-6 for x in ref['retained_reference_cases'])
assert len({x['signal_uuid']for x in tr['transitions']})==len(tr['transitions'])==66
assert all(x['verified_return_corridor_length_mm']<=2.5+1e-9 and all(v<1e-6 for v in x['corridor_uncovered_mm2'].values())for x in tr['transitions'])
assert fid['pass']and len(fid['cases'])==236
assert len(drill['new_or_replaced_vias'])==98 and drill['minimum_gap_mm']>=.1
assert {x['case']for x in tests['tests']}=={'track','via','smd_pad','npth_annulus'}and all(x['caught']for x in tests['tests'])
paths=[Path(__file__),R/'verify_portable_r107.py',R/'CHECKPOINT-R107.md',R/'SELF-REVIEW-R107.md',R/'final-review-r98.json',R/'native-r107/review.json',R/'native-r107/drc.json',R/'native-r107/erc.json',R/'native-r107/object-delta.json',R/'native-r107/netlist.xml',R/'capture-r107/capture.json',R/'capture-r107/precision.json',R/'capture_bundle_r107.py',R/'reference-review-r107.json',R/'transitions-r107.json',R/'fidelity-r107.json',R/'native-r107/added-via-drill-review.json',R/'mount-audit-r107.json',R/'keepout-tests-r107/review.json',R/'run_linux.py',R/'native-r104/run.log',R/'mount_r104.py',R/'native_r104.py',R/'candidate-r104/routing.json',R/'native-r105/review.json',R/'reference-review-r105.json',R/'keepout-tests-r105/run.log',R/'keepout-tests-r106/run.log',R/'keepout_regressions_r105.py',R/'keepout_regressions_r106.py',R/'verification-preflight-r105.txt']
# Enumerate immutable project dependencies from the accepted ancestor manifest,
# never from the current directory contents.
ancestor=read(R/'final-review-r98.json');prefix=str((R/'native-r98').relative_to(REPO))+'/'
for name in ancestor['source_sha256']:
 if not name.startswith(prefix):continue
 rel=Path(name.removeprefix(prefix));p=R/'native-r107'/rel
 if p.suffix in ['.kicad_sch','.kicad_pro','.kicad_dru']or p.name in ['sym-lib-table','fp-lib-table']or rel.parts[0]in ['libraries','symbols']:
  if p.suffix=='.kicad_dru':assert sha(p)==sha(R/'candidate-r107'/rel)
  else:assert sha(p)==sha(R/'native-r98'/rel)
  paths.append(p)
for test in tests['tests']:
 observed=read(R/'keepout-tests-r107'/test['case']/'drc.json');assert all(x in observed['violations']for x in test['caught'])
 paths.extend(R/'keepout-tests-r107'/test['case']/name for name in ['drc.json','run.log','signal_main.kicad_pcb','signal_main.kicad_pro','signal_main.kicad_dru'])
contract=REPO/'hardware/cad/assembly_workflow/verification/main-fasteners-r1'
paths.extend(contract/name for name in ['contact-keepouts.json','copper-screen.json','source-review.json'])
paths.append(R/'test_portable_closure_r107.py')
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
report={'accepted_bounded_geometry_checkpoint':True,'selected_pcb':str((R/'native-r107/signal_main.kicad_pcb').relative_to(REPO)),'selected_pcb_sha256':sha(R/'native-r107/signal_main.kicad_pcb'),'native_opens':167,'exact_original_copper_replacements':mount['exact_removed_original_copper'],'footprints_unchanged_since_r98':477,'native_mount_keepouts':9,'native_negative_tests':4,'new_route_reference_cases':130,'retained_reference_cases':4873,'local_return_cases':66,'raw_zone_fidelity_cases':236,'new_drill_cases':98,'minimum_drill_to_SMD_copper_mm':drill['minimum_gap_mm'],'missing_ESS_footprint_retained':drc['schematic_parity'],'mechanical_integration_pending':True,'noise_stability_qualified':False,'fabrication_released':False,'source_sha256':dict(sorted(closure.items()))}
(R/'final-review-r107.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS r107 complete gate; closure',len(closure))
