from pathlib import Path
import collections,json,hashlib,shutil,re,tarfile
repo=Path.cwd();root=repo/'hardware/electronics/rail_disconnect/revision28';src=root/'generated/p9-pruned-leaf-reviewed-work';dst=root/'generated/p9-targeted-timing-leaf-work';replay=root/'generated/p9-timing-leaf-byte-replay';gen=dst/'generated'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(repo))
def designs(p):return [f for f in p.rglob('*') if f.is_file() and 'generated' not in f.relative_to(p).parts and f.suffix!='.kicad_prl']
files=designs(dst);assert all(f.read_bytes()==(replay/f.relative_to(dst)).read_bytes() for f in files)
metadata=json.loads((gen/'timing-leaf-exception.json').read_text());allow=set(metadata['source_bound_exact_allowlist']);assert len(allow)==5
old=json.loads((src/'generated/drc-pruned-leaf1.json').read_text());new=json.loads((gen/'drc-targeted-timing1.json').read_text())
def ids(row):return {i['uuid'] for i in row['items']}
def signature(row):return(row['type'],row['severity'],tuple(sorted(ids(row))))
def nets(rows):return collections.Counter(re.search(r'\[/?([^\]]+)\]',r['items'][0]['description'])[1] for r in rows)
assert nets(old['unconnected_items'])==nets(new['unconnected_items'])
retained=[r for r in old['violations'] if not ids(r)&allow];removed=[r for r in old['violations'] if ids(r)&allow]
assert len(removed)==5 and all(r['type']=='via_dangling' for r in removed)
assert collections.Counter(signature(r) for r in retained)==collections.Counter(signature(r) for r in new['violations'])
assert len(new['unconnected_items'])==43 and len(new['violations'])==66 and not any(r['severity']=='error' for r in new['violations']) and not new['schematic_parity']
assert json.loads((gen/'native-targeted-timing1.json').read_text())['counts']['erc']==0
assert json.loads((gen/'full-contract.json').read_text())['contracts_equal']
assert json.loads((gen/'native-negative-controls.json').read_text())['all_three_actual_native_mutations_rejected']
lock=root/'generated/leaf-prune-source-lock-contract.json';assert sha(lock)==metadata['original_lock_contract_sha256']
models=json.loads((gen/'positive-diagnostic.json').read_text());assert len(models)==4
before=json.loads((gen/'return-before-five.json').read_text());after=json.loads((gen/'return-after-five.json').read_text());assert [v['grid_mm'] for v in before]==[.15,.1]==[v['grid_mm'] for v in after]
assert all(v['status']=='diagnostic_estimate' for v in models+before+after)
recipes=gen/'source-recipes';recipes.mkdir(exist_ok=True)
code=[root/'timing_leaf_trial.py',root/'prune_leaf_vias.py',root/'native.py',root/'native_force_compare.py',root/'native_contract_compare.py',root/'native_pad_geometry.py',root/'coupled.py',root/'copper.py',root/'native_mesh.py',root/'distributed_mesh.py',root/'stackup.json',repo/'hardware/electronics/common/sexpr.py',repo/'tests/tooling/test_disconnect_revision28.py',Path('/private/tmp/afx-e28-leaf-returns-bounded.py'),Path(__file__)]
for p in code:shutil.copy2(p,recipes/p.name)
assert sha(recipes/'timing_leaf_trial.py')==metadata['source_recipe_sha256']
sources=designs(src)+files+[lock,src/'generated/native-pruned-leaf1.json',src/'generated/drc-pruned-leaf1.json',src/'generated/filled-pruned-leaf1.kicad_pcb']
artifacts=[p for p in gen.rglob('*') if p.is_file() and p.name not in ('current-native.json','native-inputs.tar.gz','native-input-index.json')]
index={rel(p):sha(p) for p in sources+artifacts};(gen/'native-input-index.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n');artifacts.append(gen/'native-input-index.json')
archive=gen/'native-inputs.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in sources+artifacts:tar.add(p,arcname=rel(p),recursive=False)
expected={rel(p):sha(p) for p in sources+artifacts}
with tarfile.open(archive,'r:gz') as tar:
 assert {m.name for m in tar.getmembers()}==set(expected)
 for m in tar.getmembers():assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==expected[m.name]
receipt=dict(schema_version=1,scope='PRIVATE exact five unused timing-via exception; not a release or global lock relaxation',candidate_pcb_path=rel(dst/'rail_disconnect.kicad_pcb'),candidate_pcb_sha256=sha(dst/'rail_disconnect.kicad_pcb'),source_sha256={rel(p):sha(p) for p in sources},artifact_sha256={rel(p):sha(p) for p in artifacts+[archive]},native_counts=dict(opens=43,hard_drc=0,parity=0,erc=0,warnings=66),prior_warning_count=71,every_per_net_open_count_unchanged=True,every_other_warning_type_and_item_uuid_unchanged=True,removed_exact_allowlist=sorted(allow),independently_verified_no_track_no_same_net_filled_zone_one_SMD_pad_one_layer=True,prior_global_lock_contract_unchanged=True,all_other_locked_objects_literal_preserved=True,all_package_pad_body_zone_outline_setup_and_timing_values_preserved=True,all_three_actual_native_negative_controls_rejected=True,actual_filled_difference_reports=[rel(gen/'five-hole-force-compare.json'),rel(gen/'five-hole-all-filled-compare.json'),rel(gen/'nine-hole-all-filled-compare.json')],strict_zero_force_loss_claimed=False,raw_filled_residual_losses_retained=True,positive_analog_extra_ohm_by_grid={str(v['grid_mm']):v['copper_plus_unequal_chip_penalty_ohm'] for v in models if v['domain']=='analog'},analog_3mohm_allocation_pass=False,E28_only_digital_return_ohm_before={str(v['grid_mm']):v['ohm'] for v in before},E28_only_digital_return_ohm_after={str(v['grid_mm']):v['ohm'] for v in after},full_return_2mohm_allocation_pass=False,bars_contacts_P03_and_physical_load_steps_excluded_from_E28_return=True,design_input_files_byte_replayed=len(files),archive_bytes=archive.stat().st_size,archive_members_decompressed_and_hash_verified=len(expected),native_closed=False,manufacturer_process_and_assembly_accepted=False,physical_qualified=False,fabrication_released=False)
(gen/'current-native.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print('PCB',receipt['candidate_pcb_sha256']);print('receipt',sha(gen/'current-native.json'));print('archive',archive.stat().st_size,'files',len(files),'members',len(expected))
