"""Independent exact-delta audit for the I_F1 orderable-part correction."""
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha

BASE = STAGING/'two-board-power-input-tvs-native-01'
OUT = STAGING/'two-board-power-inlet-fuse-native-01'
BEFORE = STAGING/'two-board-power-routing-inputs-2372-input-tvs-01/capture.json'
AFTER = STAGING/'two-board-power-routing-inputs-2372-inlet-fuse-01/capture.json'


def run():
    paths = [Path(__file__), BEFORE, AFTER, BASE/'power_protection.kicad_pcb',
             BASE/'netlist.xml', BASE/'expected-circuit.json', BASE/'input-tvs-review.json',
             OUT/'power_protection.kicad_pcb', OUT/'netlist.xml', OUT/'review.json',
             OUT/'expected-circuit.json', OUT/'inlet-fuse-change.json',
             STAGING/'two-board-placement-05/capture.json',
             REPO/'hardware/fabrication/parts/inlet-fuse-01/README.md']
    for p in [BEFORE, AFTER, OUT/'review.json', OUT/'inlet-fuse-change.json']:
        d = json.loads(p.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, digest in d.get(field, {}).items():
                q = Path(name)
                if not q.is_absolute():
                    q = (REPO if name.startswith(('hardware/', 'tests/')) else p.parent)/q
                assert sha(q) == digest, (p, name)
    old = '0451006.MRL 6A 125V'; new = '045106.3MRL 6.3A 125V'
    boards = [read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE, OUT]]
    f = next(f for f in children(boards[1], 'footprint') if prop(f, 'Reference')[2] == 'I_F1')
    assert prop(f, 'Value')[2] == new and prop(f, 'MPN')[2] == '045106.3MRL'
    prop(f, 'Value')[2] = prop(f, 'MPN')[2] = old
    assert boards[0] == boards[1], 'Unexpected board edit: full tree must restore exactly'
    a, b = [json.loads((p/'expected-circuit.json').read_text()) for p in [BASE, OUT]]
    assert b['I_F1']['value'] == new
    b['I_F1']['value'] = old
    assert a == b
    (parts0, pins0), (parts1, pins1) = [read_netlist(p/'netlist.xml') for p in [BASE, OUT]]
    assert parts0.keys() == parts1.keys() and len(parts1) == 1086 and pins0 == pins1
    changes = []
    for ref in parts0:
        for field in ['value', 'footprint', 'datasheet']:
            x, y = parts0[ref].findtext(field), parts1[ref].findtext(field)
            if x != y:
                changes.append((ref, field, x, y))
    assert changes == [('I_F1', 'value', old, new)], changes
    # Verify every copied CAD/support file independently. Schematic and library
    # symbols are compared after undoing exactly the one declared value change.
    compared = 0
    for p in OUT.rglob('*'):
        rel = p.relative_to(OUT)
        q = BASE/rel
        if not p.is_file() or not q.is_file() or not (rel.parts[0] in ['libraries', 'symbols'] or
                p.suffix in ['.kicad_sch', '.kicad_dru'] or p.name in ['fp-lib-table', 'sym-lib-table', 'symbol-paths.json']):
            continue
        x, y = q.read_text(), p.read_text()
        if p.name == 'power_protection.kicad_sch':
            aa, bb = read_sexpr(x), read_sexpr(y)
            assert first(first(bb, 'title_block'), 'rev')[1] == 'TBP35'
            first(first(bb, 'title_block'), 'rev')[1] = first(first(aa, 'title_block'), 'rev')[1]
            assert aa == bb
        elif p.name in ['I_rear_inlet.kicad_sch', 'TBP01_I_RMX_E23I2.kicad_sym']:
            assert old not in y and new in y and y.replace(new, old) == x
        else:
            assert x == y, rel
        paths.extend([p, q]); compared += 1
    c0, c1 = [json.loads(p.read_text()) for p in [BEFORE, AFTER]]
    for field in ['zones', 'open_nets', 'outline', 'copper_layers']:
        assert c0[field] == c1[field], field
    objects0, objects1 = [{o['uuid']: o for o in c['objects']} for c in [c0, c1]]
    physical = lambda o: {k: v for k, v in o.items() if k not in ['uuid', 'group']}
    aliases = {}
    for uid in objects0.keys()-objects1.keys():
        o = objects0[uid]
        assert o['kind'] == 'PAD'
        matches = [u for u in objects1.keys()-objects0.keys() if physical(o) == physical(objects1[u])]
        assert len(matches) == 1, (uid, matches)
        aliases[uid] = matches[0]
    assert len(set(aliases.values())) == len(aliases)
    assert {aliases.get(u, u) for u in objects0} == set(objects1)
    for uid, o in objects0.items():
        assert physical(o) == physical(objects1[aliases.get(uid, uid)]), uid
    for field in ['groups', 'all_groups']:
        left = {frozenset(aliases.get(u, u) for u in group) for group in c0[field].values()}
        right = {frozenset(group) for group in c1[field].values()}
        assert left == right, field
    assert c0['native_uncapped_opens'] == c1['native_uncapped_opens'] == 2372
    native = json.loads((OUT/'review.json').read_text())
    assert native['geometry_findings'] == native['schematic_parity_findings'] == 0
    erc = json.loads((OUT/'erc.json').read_text())
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['severity'] == 'warning' and v['type'] == 'ground_pin_not_ground' for v in warnings)
    record = next(r for r in json.loads((STAGING/'two-board-placement-05/capture.json').read_text())['parts'] if r['id'] == 'I_F1')
    assert record['height_mm'] >= 2.94
    x0, y0, x1, y1 = record['body_relative_xy']
    assert x0 <= -3.15 and x1 >= 3.15 and y0 <= -1.47 and y1 >= 1.47
    # Same series and lands: compare directly with the manufacturer's drawing.
    assert [list(map(float, first(p, 'size')[1:])) for p in children(f, 'pad')] == [[1.96, 3.15]]*2
    centres = [float(first(p, 'at')[1]) for p in children(f, 'pad')]
    assert abs(centres[1]-centres[0]-1.96-2.95) < 1e-9
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        only_component_value_change=list(changes[0]), exact_geometry_unchanged=True,
        complete_board_restored_by_only_two_property_values=True, copied_CAD_files_checked=compared,
        all_captured_objects_unchanged=len(c1['objects']), all_zones_unchanged=len(c1['zones']),
        all_native_groups_unchanged=len(c1['all_groups']), pin_net_entries_unchanged=len(pins1),
        regenerated_native_pad_UUID_aliases=aliases,
        power_opens=2372, native_geometry_and_parity_findings=0, ERC_errors=0, ERC_warnings=2,
        nominal_lands_match_manufacturer_dimensions=True, package_within_previous_body_height_allocation=True,
        prior_TBP34_copper_visual_review_applicable=True, complete_installed_fit_verified=False,
        inlet_current_thermal_and_fault_coordination_qualified=False, fabrication_released=False)
    with (OUT/'inlet-fuse-review.json').open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))


if __name__ == '__main__':
    run()
