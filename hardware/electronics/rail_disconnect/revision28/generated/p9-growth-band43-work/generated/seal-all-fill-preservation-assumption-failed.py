import collections,hashlib,json,shutil,tarfile,re
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr
from hardware.electronics.rail_disconnect.revision28.outline_growth_review import check_outline_only
repo=Path.cwd();root=repo/'hardware/electronics/rail_disconnect/revision28';src=root/'generated/p9-six-load-n12-work';dst=root/'generated/p9-growth-band43-work';replay=root/'generated/p9-growth43-byte-replay';gen=dst/'generated'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(repo))
def designs(p):return [f for f in p.rglob('*') if f.is_file() and 'generated' not in f.relative_to(p).parts and f.suffix!='.kicad_prl']
files=designs(dst);assert all((replay/f.relative_to(dst)).read_bytes()==f.read_bytes() for f in files)
review=check_outline_only(read_sexpr((src/'rail_disconnect.kicad_pcb').read_text()),read_sexpr((dst/'rail_disconnect.kicad_pcb').read_text()))
old=json.loads((src/'generated/drc-six-load-n12-1.json').read_text());new=json.loads((gen/'drc-growth-band43-1.json').read_text())
def signature(row):return (row['type'],row.get('severity'),tuple(sorted(i['uuid'] for i in row.get('items',[]))))
for key in ('violations','schematic_parity'):assert collections.Counter(signature(r) for r in old[key])==collections.Counter(signature(r) for r in new[key])
def nets(rows):return collections.Counter(re.search(r'\[/?([^\]]+)\]',row['items'][0]['description'])[1] for row in rows)
assert nets(old['unconnected_items'])==nets(new['unconnected_items'])
filled=json.loads((gen/'all-filled-netlayers-compare.json').read_text());assert filled['no_force_pour_material_removed_above_clipping_control'];assert all(v['gained_area_mm2']<=v['self_subtraction_control_mm2']+1e-8 for v in filled['rows'])
assert len(new['unconnected_items'])==43 and len(new['violations'])==75 and not new['schematic_parity'] and not any(r['severity']=='error' for r in new['violations'])
contract=json.loads((gen/'full-contract.json').read_text());assert not contract['edge_cuts_equal'] and contract['zone_contract_equal'] and contract['board_setup_equal'];assert all(not contract[k] for k in ('missing_references','extra_references','changed_footprint_bodies_or_attributes','changed_pad_contracts','changed_complete_footprints'))
force=json.loads((gen/'force-compare.json').read_text());assert force['no_force_pour_material_removed_above_clipping_control']
review.update(byte_replayed_design_files=len(files),every_per_net_open_count_and_warning_item_uuid_unchanged=True,pad_uuid_identity_not_claimed=True,all_filled_netlayers_preserved_above_subtraction_control=True,all_parts_pads_zones_setup_native_contracts_preserved=True,only_authorized_outline_contract_changed=True,force_no_loss_above_native_self_subtraction_control=True)
(gen/'independent-outline-review.json').write_text(json.dumps(review,indent=2)+'\n')
archive_recipes=gen/'source-recipes';archive_recipes.mkdir(exist_ok=True)
for p in (root/'outline_growth_proposal.py',root/'outline_growth_review.py',root/'native.py',root/'native_contract_compare.py',root/'native_force_compare.py',repo/'tests/tooling/test_disconnect_revision28.py',Path(__file__)):
 shutil.copy2(p,archive_recipes/p.name)
assert sha(archive_recipes/'outline_growth_proposal.py')==json.loads((gen/'outline-growth.json').read_text())['recipe_sha256']
sources=designs(src)+files
artifacts=[p for p in gen.rglob('*') if p.is_file() and p.name not in ('current-native.json','native-inputs.tar.gz','native-input-index.json')]
index={rel(p):sha(p) for p in sources+artifacts}
(gen/'native-input-index.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n');artifacts.append(gen/'native-input-index.json')
archive=gen/'native-inputs.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in sources+artifacts:tar.add(p,arcname=rel(p),recursive=False)
expected={rel(p):sha(p) for p in sources+artifacts}
with tarfile.open(archive,'r:gz') as tar:
 assert {m.name for m in tar.getmembers()}==set(expected)
 for member in tar.getmembers():assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==expected[member.name]
receipt=dict(schema_version=1,scope='PRIVATE outline-only +9.25mm proposal from explicitly incomplete43-open source',candidate_pcb_path=rel(dst/'rail_disconnect.kicad_pcb'),candidate_pcb_sha256=sha(dst/'rail_disconnect.kicad_pcb'),source_sha256={rel(p):sha(p) for p in sources},artifact_sha256={rel(p):sha(p) for p in artifacts+[archive]},native_counts=dict(opens=43,hard_drc=0,warnings=75,parity=0,erc=0),all_per_net_opens_and_warning_item_ids_unchanged=True,native_unconnected_pad_uuid_stability_claimed=False,source_pad_uuid_absence_caveat="Legacy source pads lack explicit UUIDs; actual native pads receive fresh metadata IDs. Raw reports retained. Literal pad geometry/net/body and every filled net/layer are independently preserved.",all_filled_netlayers_preserved_above_subtraction_control=True,exactly_three_existing_edge_objects_changed=True,every_other_literal_board_object_unchanged=True,all_parts_pads_zones_and_setup_native_contracts_preserved=True,filled_force_loss_within_native_self_subtraction_control=True,design_input_files_byte_replayed=len(files),archive_members_decompressed_and_hash_verified=len(expected),archive_bytes=archive.stat().st_size,source_outline_mm=[156,45.25],candidate_outline_mm=[156,54.5],board_datum_world_mm=[8,108.5,5],new_maximum_world_y_mm=163.0,actual_source_ground_force_port_world_mm=[161,129.5],fed_wire_prototype_ground_force_port_world_mm=[161,126.5],wire_route_acceptance_inherited=False,existing_analog_copper_allocation_still_failed=True,full_native_closed=False,housing_panel_pose_power_hardware_and_support_fit_approved=False,physical_qualified=False,fabrication_released=False)
(gen/'current-native.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(receipt['candidate_pcb_sha256']);print('receipt',sha(gen/'current-native.json'));print('files',len(files),'archive',archive.stat().st_size)
