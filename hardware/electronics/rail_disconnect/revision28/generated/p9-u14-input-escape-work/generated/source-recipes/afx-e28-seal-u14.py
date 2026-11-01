from pathlib import Path
import collections,json,hashlib,shutil,re,tarfile
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
repo=Path.cwd();root=repo/'hardware/electronics/rail_disconnect/revision28';src=root/'generated/p9-targeted-timing-leaf-work';dst=root/'generated/p9-u14-input-escape-work';replay=root/'generated/p9-u14-input-byte-replay';gen=dst/'generated'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(repo))
def designs(p):return [f for f in p.rglob('*') if f.is_file() and 'generated' not in f.relative_to(p).parts and f.suffix!='.kicad_prl']
files=designs(dst);assert all(f.read_bytes()==(replay/f.relative_to(dst)).read_bytes() for f in files)
meta=json.loads((gen/'U14-input-escape.json').read_text());assert sha(dst/'rail_disconnect.kicad_pcb')==meta['candidate_pcb_sha256']
a=json.loads((src/'generated/drc-targeted-timing1.json').read_text());b=json.loads((gen/'drc-u14-input-escape1.json').read_text())
def signature(row):return(row['type'],row['severity'],tuple(sorted(i['uuid'] for i in row['items'])))
def nets(rows):return collections.Counter(re.search(r'\[/?([^\]]+)\]',r['items'][0]['description'])[1] for r in rows)
assert nets(a['unconnected_items'])==nets(b['unconnected_items']);assert collections.Counter(signature(v) for v in a['violations'])==collections.Counter(signature(v) for v in b['violations'])
assert len(b['unconnected_items'])==43 and len(b['violations'])==66 and not b['schematic_parity'] and not any(v['severity']=='error' for v in b['violations'])
assert json.loads((gen/'native-u14-input-escape1.json').read_text())['counts']['erc']==0
assert json.loads((gen/'full-contract.json').read_text())['contracts_equal']
assert json.loads((gen/'mask-paste-equivalence.json').read_text())['no_new_drawn_mask_or_paste_openings']
lock=root/'generated/leaf-prune-source-lock-contract.json';assert sha(lock)==meta['original_lock_contract_sha256'];locked=json.loads(lock.read_text())['locked_copper'];ex=set(json.loads((src/'generated/timing-leaf-exception.json').read_text())['source_bound_exact_allowlist'])
tree=read_sexpr((dst/'rail_disconnect.kicad_pcb').read_text());objects={str(first(n,'uuid')[1]):n for n in tree if isinstance(n,list) and n and n[0] in ('segment','via')}
for row in locked:
 if row['uuid'] in ex:assert row['uuid'] not in objects
 else:assert hashlib.sha256(sexpr(objects[row['uuid']]).encode()).hexdigest()==row['native_object_sha256']
models=json.loads((gen/'positive-diagnostic.json').read_text());fine=json.loads((gen/'analog-refinement-04.json').read_text());ret=json.loads((gen/'return-diagnostic.json').read_text());assert len(models)==4 and fine['grid_mm']==.04 and [v['grid_mm'] for v in ret]==[.15,.1]
analog={str(v['grid_mm']):v['copper_plus_unequal_chip_penalty_ohm'] for v in models if v['domain']=='analog'};analog['0.04']=fine['copper_plus_unequal_chip_penalty_ohm'];assert all(v<.003 for v in analog.values());assert all(v['ohm']>.002 for v in ret)
recipes=gen/'source-recipes';recipes.mkdir(exist_ok=True)
code=[root/name for name in ('u14_input_escape.py','ground_corridor.py','repair.py','native.py','native_force_compare.py','native_contract_compare.py','native_pad_geometry.py','coupled.py','copper.py','native_mesh.py','distributed_mesh.py','generate.py','stackup.json')]+[repo/'hardware/electronics/common/sexpr.py',Path('/private/tmp/afx-e28-u14-return-bounded.py'),Path(__file__)]
for p in code:shutil.copy2(p,recipes/p.name)
assert sha(recipes/'u14_input_escape.py')==meta['source_recipe_sha256']
probe=root/'generated/p9-u14-barrel-probe-work/generated/barrel-probe.json';assert sha(probe)==meta['source_probe_sha256']
sources=designs(src)+files+[lock,probe,src/'generated/current-native.json',src/'generated/filled-targeted-timing1.kicad_pcb',src/'generated/drc-targeted-timing1.json',src/'generated/native-targeted-timing1.json']
artifacts=[p for p in gen.rglob('*') if p.is_file() and p.name not in ('current-native.json','native-inputs.tar.gz','native-input-index.json')];index={rel(p):sha(p) for p in sources+artifacts};(gen/'native-input-index.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n');artifacts.append(gen/'native-input-index.json');archive=gen/'native-inputs.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in sources+artifacts:tar.add(p,arcname=rel(p),recursive=False)
expected={rel(p):sha(p) for p in sources+artifacts}
with tarfile.open(archive,'r:gz') as tar:
 assert {m.name for m in tar.getmembers()}==set(expected)
 for m in tar.getmembers():assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==expected[m.name]
receipt=dict(schema_version=1,scope='PRIVATE actual U14 input barrel plus three unlocked PG1 trace detours, not a release',candidate_pcb_path=rel(dst/'rail_disconnect.kicad_pcb'),candidate_pcb_sha256=sha(dst/'rail_disconnect.kicad_pcb'),source_sha256={rel(p):sha(p) for p in sources},artifact_sha256={rel(p):sha(p) for p in artifacts+[archive]},native_counts=dict(opens=43,hard_drc=0,parity=0,erc=0,warnings=66),every_per_net_open_count_and_warning_item_unchanged=True,all_parts_pads_holes_other_than_one_new_barrel_zones_outline_and_rules_unchanged=True,all_existing_force_gate_and_timing_objects_retained_outside_antecedent_exact_five_hole_exception=True,global_lock_contract_unmodified=True,changed_unlocked_pg1_trace_objects=3,actual_new_input_barrels=1,rejected_output_barrel_not_retained=True,actual_masks_and_paste_unchanged_above_timestamp_comments=True,actual_filled_force_difference_rows=json.loads((gen/'force-compare.json').read_text())['rows'],strict_no_force_loss_claimed=False,analog_extra_ohm_by_grid=analog,digital_extra_ohm_by_grid={str(v['grid_mm']):v['copper_plus_unequal_chip_penalty_ohm'] for v in models if v['domain']=='digital'},analog_fine_grid_change_ohm=abs(analog['0.04']-analog['0.05']),analog_finest_diagnostic_margin_ohm=.003-analog['0.04'],diagnostics_below_positive_allocation=True,certified_resistance_bound=False,material_etch_solder_contacts_and_process_accepted=False,E28_only_digital_return_ohm_by_grid={str(v['grid_mm']):v['ohm'] for v in ret},full_return_2mohm_allocation_pass=False,source_bipolar_complete_drop_startup_PDNaudio_and_thermal_qualified=False,design_input_files_byte_replayed=len(files),archive_members_decompressed_and_hash_verified=len(expected),archive_bytes=archive.stat().st_size,native_closed=False,physical_qualified=False,fabrication_released=False)
(gen/'current-native.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print('PCB',receipt['candidate_pcb_sha256']);print('receipt',sha(gen/'current-native.json'));print('archive',archive.stat().st_size,'members',len(expected))
