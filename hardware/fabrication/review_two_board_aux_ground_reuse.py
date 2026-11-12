"""Verify only the declared six ground joins changed the accepted TBP71 PCB."""
import json
import math
from pathlib import Path

from shapely.geometry import LineString
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha, read_netlist
from hardware.fabrication.plan_two_board_aux_ground_reuse import BASE, CAP
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

OUT = STAGING / 'two-board-power-aux-ground-reuse-native-01'
AFTER = STAGING / 'two-board-power-routing-inputs-aux-ground-reuse-01/capture.json'


def run():
    target = OUT / 'aux-ground-reuse-review.json'
    assert not target.exists()
    paths = [CAP, AFTER, OUT / 'aux-ground-reuse-routing.json', OUT / 'review.json']
    before, after, routing, native = [json.loads(p.read_text()) for p in paths]
    for path, data in zip(paths, (before, after, routing, native)):
        for field in ('source_sha256', 'artifact_sha256'):
            for name, digest in data.get(field, {}).items():
                p = Path(name)
                if not p.is_absolute():
                    p = (REPO if name.startswith(('hardware/', 'tests/')) else path.parent) / p
                assert sha(p) == digest, (path, name)
    fidelity = verify_capture(after)
    assert not routing['vias'] and not routing['edited_zone_outlines'] and not routing['refilled_existing_zones']
    assert native['geometry_findings'] == native['schematic_parity_findings'] == 0
    tracks = {u for route in routing['routes'] for u in route['segment_uuids']}
    assert len(tracks) == routing['added_tracks'] == 8
    old, new = [{o['uuid']: o for o in c['objects']} for c in (before, after)]
    physical = lambda o: {k: v for k, v in o.items() if k not in ('uuid', 'group')}
    aliases = {}
    for u in old.keys() - new.keys():
        assert old[u]['kind'] == 'PAD'
        matches = [v for v in new.keys() - old.keys() - tracks if physical(old[u]) == physical(new[v])]
        assert len(matches) == 1, u
        aliases[matches[0]] = u
    assert set(aliases) == new.keys() - old.keys() - tracks
    for o in after['objects']:
        o['uuid'] = aliases.get(o['uuid'], o['uuid'])
        o['group'] = aliases.get(o['group'], o['group'])
    after['all_groups'] = {aliases.get(g, g): [aliases.get(u, u) for u in members]
                           for g, members in after['all_groups'].items()}
    new = {o['uuid']: o for o in after['objects']}
    assert old.keys() == new.keys() - tracks
    assert all(physical(o) == physical(new[u]) for u, o in old.items())
    boards = [read_sexpr((p / 'power_protection.kicad_pcb').read_text()) for p in (BASE, OUT)]
    strip = lambda b: [n for n in b if not (isinstance(n, list) and n and n[0] == 'segment'
                                            and str(first(n, 'uuid')[1]) in tracks)]
    assert strip(boards[0]) == strip(boards[1]), 'Undeclared authored change'
    assert before['zones'] == after['zones'], 'Any plane change requires a different review'
    assert len(after['zones']) == 47
    allowed = set(routing['allowed_ground_groups'])
    main = routing['old_main_ground_group']
    assert allowed == {main, *[r['source_group'] for r in routing['routes']]}
    expected = {frozenset(g) for g in before['all_groups'].values()}
    merged = set()
    for group in allowed:
        members = before['all_groups'][group]
        assert all(old[u]['net'] == 'PWR_AGND' for u in members)
        expected.remove(frozenset(members))
        merged.update(members)
    expected.add(frozenset(merged))
    actual = {frozenset(set(g) - tracks) for g in after['all_groups'].values()} - {frozenset()}
    assert expected == actual, 'Unexpected native connectivity change'
    main_after = new[before['all_groups'][main][0]]['group']
    assert all(new[u]['group'] == main_after for u in tracks)
    fields, _ = anchored_fields(after)
    references = []
    for route in routing['routes']:
        assert old[route['target_uuid']]['group'] == main
        target_object = new[route['target_uuid']]
        assert math.dist(route['path_mm'][-1], target_object['position_mm']) < 1e-6
        source = next(o for o in old.values() if o.get('ref') == route['pad_ref'] and o.get('pin') == route['pad_pin'])
        assert source['group'] == route['source_group']
        assert math.dist(route['path_mm'][0], source['position_mm']) < 1e-6
        assert len(route['segment_uuids']) == len(route['path_mm']) - 1
        for uid, (start, end) in zip(route['segment_uuids'], zip(route['path_mm'], route['path_mm'][1:])):
            obj = new[uid]
            assert obj['kind'] == 'PCB_TRACK' and obj['net'] == 'PWR_AGND'
            assert list(obj['layers']) == [route['layer']] and obj['width_mm'] == .3
            assert math.dist(start, obj['position_mm']) < 1e-6 and math.dist(end, obj['end_mm']) < 1e-6
        band = LineString(route['path_mm']).buffer(.15)
        uncovered = band.difference(fields[route['reference_layer'], main_after].buffer(.0015)).area
        assert uncovered < 1e-6
        references.append(dict(ref=route['pad_ref'], reference_layer=route['reference_layer'],
                               length_mm=route['length_mm'], uncovered_area_mm2=uncovered))
    for f in BASE.glob('*.kicad_sch'):
        a, b = [read_sexpr((p / f.name).read_text()) for p in (BASE, OUT)]
        if f.name == 'power_protection.kicad_sch':
            assert first(first(b, 'title_block'), 'rev')[1] == 'TBP72-CANDIDATE'
            first(first(b, 'title_block'), 'rev')[:] = first(first(a, 'title_block'), 'rev')
        assert a == b, f.name
    _, old_pins = read_netlist(BASE / 'netlist.xml')
    _, new_pins = read_netlist(OUT / 'netlist.xml')
    assert old_pins == new_pins
    erc = json.loads((OUT / 'erc.json').read_text())
    violations = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(violations) == 2 and all(v['severity'] == 'warning' for v in violations)
    assert not erc['ignored_checks']
    assert before['native_uncapped_opens'] - after['native_uncapped_opens'] == len(allowed) - 1 == 6
    assert after['native_uncapped_opens'] == native['opens'] == 1937
    sources = [Path(__file__), *paths, BASE / 'final-review.json', OUT / 'erc.json', OUT / 'netlist.xml',
               REPO / 'hardware/fabrication/plan_two_board_startup_controls.py',
               REPO / 'hardware/fabrication/verify_native_zone_unfracture.py']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  native_opens=1937, closed_connections=6, added_tracks=8, added_vias=0,
                  all_original_objects_and_47_plane_fills_unchanged=True,
                  all_other_native_connectivity_groups_preserved=True,
                  reference_checks=references, zone_capture_fidelity=fidelity,
                  geometry_errors=0, parity_errors=0, erc_errors=0, erc_warnings=2,
                  high_frequency_decoupling_qualified=False, fabrication_released=False)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('native_opens', 'closed_connections', 'added_tracks', 'added_vias')}))


if __name__ == '__main__':
    run()
