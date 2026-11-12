"""Fail-closed acceptance gate for the bounded r26 DAC routing checkpoint."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[R/'native-r26/review.json',R/'native-r26/drc.json',R/'native-r26/erc.json',R/'native-r26/object-delta.json',R/'native-r26/netlist.xml',R/'capture-r26/capture.json',R/'reference-review-r26.json',R/'transitions-r26.json',R/'fidelity-r26.json',R/'native-r26/added-via-drill-review.json',R/'native-precision-r26/report.json',R/'candidate-r26/routing.json',R/'preview-r26.json',R/'preview-r26.png',R/'REFERENCE-POLICY.md',R/'test_reference_gate.py',R/'run_linux.py',Path(__file__)]
# Keep the accepted board usable with the exact native project/rule/library inputs.
for p in (R/'native-r26').rglob('*'):
 if not p.is_file():continue
 relative=p.relative_to(R/'native-r26')
 if p.suffix in ['.kicad_sch','.kicad_pro','.kicad_dru']or p.name in ['sym-lib-table','fp-lib-table']or relative.parts[0]in ['libraries','symbols']:
  baseline=R.parent/'signal_input/native-r7'/relative
  assert baseline.is_file()and sha(p)==sha(baseline),('changed native project dependency',p)
  paths.append(p)
closure={};queue=list(paths)
while queue:
 p=queue.pop().resolve()
 if str(p)in closure:continue
 closure[str(p)]=sha(p)
 if p.suffix!='.json'or not p.is_relative_to(R):continue
 doc=read(p)
 if not isinstance(doc,dict):continue
 for key,bindings in doc.items():
  if not key.endswith('source_sha256')or not isinstance(bindings,dict):continue
  for name,digest in bindings.items():
   dependency=Path(name);dependency=dependency if dependency.is_absolute()else REPO/dependency
   assert sha(dependency)==digest,('stale source',p,dependency)
   queue.append(dependency)
native=read(R/'native-r26/review.json');drc=read(R/'native-r26/drc.json');erc=read(R/'native-r26/erc.json');cap=read(R/'capture-r26/capture.json');ref=read(R/'reference-review-r26.json');tr=read(R/'transitions-r26.json');fid=read(R/'fidelity-r26.json');drill=read(R/'native-r26/added-via-drill-review.json');routing=read(R/'candidate-r26/routing.json');old_drc=read(R.parent/'signal_input/native-r7/drc.json')
assert not drc['violations']and not drc['ignored_checks']and not erc['ignored_checks']and not any(s['violations']for s in erc['sheets'])
assert drc['schematic_parity']==old_drc['schematic_parity']and len(drc['schematic_parity'])==1
assert native['exact_all_netlist_partitions']and native['old_objects_unchanged']and not read(R/'native-r26/object-delta.json')['changed_old_objects']
assert len(drc['unconnected_items'])==cap['native_uncapped_opens']==cap['independent_sum_of_pad_cluster_gaps']==routing['expected_opens']==198
assert cap['footprints_captured']==477
from hardware.electronics.common.sexpr import read_sexpr,children,sexpr
old_tree=read_sexpr((R.parent/'signal_input/native-r7/signal_main.kicad_pcb').read_text());new_tree=read_sexpr((R/'native-r26/signal_main.kicad_pcb').read_text())
for tag in ['general','layers','setup']:
 assert [sexpr(v)for v in children(old_tree,tag)]==[sexpr(v)for v in children(new_tree,tag)],('changed board settings',tag)
assert ref['all_original_native_groups_preserved']and sum(len(m['old_groups'])-1 for m in ref['only_approved_net_groups_merged'])==32
assert all(x['unexplained_uncovered_mm2']<1e-6 for x in ref['new_reference_cases'])and all(x['unexplained_loss_mm2']<1e-6 for x in ref['retained_reference_cases'])
assert len({x['signal_uuid']for x in tr['transitions']})==len(tr['transitions'])==34
assert all(x['verified_return_corridor_length_mm']<=2.5+1e-9 and all(v<1e-6 for v in x['corridor_uncovered_mm2'].values())for x in tr['transitions'])
assert fid['pass']and len(fid['cases'])==183
assert len(drill['new_or_replaced_vias'])==54 and drill['minimum_gap_mm']>=.1
remaining=[v for v in drc['unconnected_items']if '/A_DAC/'in json.dumps(v)];assert len(remaining)==8
nets=sorted({n for v in remaining for n in re.findall(r'\[(/A_DAC/[^\]]+)\]',json.dumps(v))})
assert set(nets)=={b['net']for b in routing['blocked']}
report={'accepted_bounded_geometry_checkpoint':True,'selected_pcb':str((R/'native-r26/signal_main.kicad_pcb').relative_to(REPO)),'selected_pcb_sha256':sha(R/'native-r26/signal_main.kicad_pcb'),'baseline_native_opens':230,'native_opens':198,'new_cluster_joins':32,'footprints_unchanged':477,'new_route_reference_cases':len(ref['new_reference_cases']),'retained_reference_cases':len(ref['retained_reference_cases']),'local_return_cases':34,'raw_zone_fidelity_cases':183,'new_drill_cases':54,'minimum_new_drill_to_SMD_copper_mm':drill['minimum_gap_mm'],'remaining_DAC_connections':remaining,'remaining_DAC_nets':nets,'retained_missing_footprint_finding':drc['schematic_parity'],'reference_policy':'REFERENCE-POLICY.md','raw_reference_changes_retained_in':'reference-review-r26.json','full_DAC_routing_complete':False,'noise_stability_crosstalk_qualified':False,'fabrication_released':False,'source_sha256':{str(Path(p).relative_to(REPO)):h for p,h in sorted(closure.items())}}
(R/'final-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['source_sha256','remaining_DAC_connections']},indent=2));print('Verified closure files',len(closure))
