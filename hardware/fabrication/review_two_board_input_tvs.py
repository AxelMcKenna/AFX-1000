"""Independent geometry, mechanical, connectivity and reference audit of TBP34."""
import copy
import json
import math
from pathlib import Path
from shapely.affinity import rotate, translate
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE = STAGING/'two-board-power-inlet-corridor-native-02'
OUT = STAGING/'two-board-power-input-tvs-native-01'
FILLED = STAGING/'two-board-power-input-tvs-filled-01'
BEFORE = STAGING/'two-board-power-routing-inputs-2374-inlet-corridor-02/capture.json'
AFTER = STAGING/'two-board-power-routing-inputs-2372-input-tvs-01/capture.json'


def angle(f):
    p = first(f, 'at')
    return float(p[3]) if len(p) > 3 else 0


def run():
    sources = [Path(__file__), BEFORE, AFTER, OUT/'input-tvs-routing.json', FILLED/'local-plane-fill.json',
               BASE/'inlet-corridor-review.json', STAGING/'two-board-placement-05/capture.json',
               STAGING/'assembly-layout-04/allocation.json']
    before, after, report, fill = [json.loads(p.read_text()) for p in sources[1:5]]
    for d in [before, after, report, fill]:
        for p, h in d['source_sha256'].items():
            assert sha(REPO/p) == h, p
    for n, h in fill['artifact_sha256'].items():
        assert sha(FILLED/n) == h, n
    fidelity = verify_capture(after)
    move, = report['moves']
    assert move == dict(ref='P_D101', old_xy=[193.5, 137.5], new_xy=[186, 112], rotation_added_degrees=90, final_angle=180, side='B.Cu')
    assert not report['retired_tracks'] and not report['retired_vias'] and report['added_tracks'] == 0
    trees = [read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE, OUT]]
    fps = [{prop(f, 'Reference')[2]: f for f in children(t, 'footprint')} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[0]) == 1101
    for r, f in fps[0].items():
        n = fps[1][r]
        if r != 'P_D101':
            assert geometry(f) == geometry(n), r
            continue
        assert list(map(float, first(f, 'at')[1:3])) == move['old_xy']
        assert list(map(float, first(n, 'at')[1:3])) == move['new_xy']
        assert angle(f) == 90 and angle(n) == 180 and first(f, 'layer') == first(n, 'layer')
        restored = copy.deepcopy(n); first(restored, 'at')[:] = first(f, 'at')
        for tag in ['pad', 'property', 'fp_text']:
            aa, bb = children(f, tag), children(restored, tag); assert len(aa) == len(bb)
            for x, y in zip(aa, bb):
                ax, ay = children(x, 'at'), children(y, 'at'); assert len(ax) == len(ay)
                for p, q in zip(ax, ay):
                    assert list(map(float, p[1:3])) == list(map(float, q[1:3]))
                    a0 = float(p[3]) if len(p) > 3 else 0; a1 = float(q[3]) if len(q) > 3 else 0
                    assert (a1-a0) % 360 == 90
                    q[:] = p
        assert geometry(f) == geometry(restored)
    def shell(t):
        return [n for n in t if not (isinstance(n, list) and n and n[0] in ['footprint', 'segment', 'arc', 'via', 'net', 'zone'])]
    assert shell(trees[0]) == shell(trees[1])
    parts0, pins0 = read_netlist(BASE/'netlist.xml'); parts1, pins1 = read_netlist(OUT/'netlist.xml')
    assert parts0.keys() == parts1.keys() and len(parts1) == 1086 and pins0 == pins1
    assert all(parts0[r].findtext(k) == parts1[r].findtext(k) for r in parts0 for k in ['value', 'footprint'])
    old, new = [{o['uuid']: o for o in c['objects']} for c in [before, after]]
    physical = lambda o: {k: v for k, v in o.items() if k not in ['uuid', 'group']}
    def transformed(g):
        return translate(rotate(g, -90, origin=move['old_xy']), move['new_xy'][0]-move['old_xy'][0], move['new_xy'][1]-move['old_xy'][1])
    aliases = {}
    for u in old.keys()-new.keys():
        o = old[u]; assert o['kind'] == 'PAD'
        hits = [v for v in new.keys()-old.keys() if
                (new[v].get('ref') == 'P_D101' and new[v].get('pin') == o.get('pin') if o.get('ref') == 'P_D101'
                 else physical(new[v]) == physical(o))]
        assert len(hits) == 1, (u, hits)
        aliases[u] = hits[0]
    assert len(set(aliases.values())) == len(aliases)
    maxerror = 0; moved = 0
    for u, o in old.items():
        n = new[aliases.get(u, u)]
        if o.get('ref') != 'P_D101':
            assert physical(o) == physical(n), u
            continue
        moved += 1
        assert all(o[k] == n[k] for k in ['kind', 'ref', 'pin', 'net', 'drill_mm', 'npth'])
        assert o['layers'].keys() == n['layers'].keys() and (n['orientation_degrees']-o['orientation_degrees']) % 360 == 90
        assert transformed(Point(o['position_mm'])).distance(Point(n['position_mm'])) < 2e-6
        for layer, ps in o['layers'].items():
            error = transformed(shape(ps)).hausdorff_distance(shape(n['layers'][layer]))
            assert error < 2e-6; maxerror = max(maxerror, error)
    assert moved == 2
    added = new.keys()-{aliases.get(u, u) for u in old}
    assert added == {v['uuid'] for v in report['vias']} and len(added) == 12
    for v in report['vias']:
        o = new[v['uuid']]
        assert o['kind'] == 'PCB_VIA' and o['net'] == v['net'] and o['position_mm'] == v['position_mm']
        assert o['width_mm'] == .6 and o['drill_mm'] == .3 and o['via_type'] == 4
        assert o['span'] == ['F.Cu', 'B.Cu'] and set(o['layers']) == set(after['copper_layers'])
    memberships = {u: set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        translated = {aliases.get(u, u) for u in g}
        assert translated <= memberships[next(iter(translated))]
    pad = lambda r, p: next(o for o in new.values() if o.get('ref') == r and o.get('pin') == p)
    oldpad = lambda r, p: next(o for o in old.values() if o.get('ref') == r and o.get('pin') == p)
    connections = []
    for pin, anchor in [('1', ('P_Q101', '1')), ('2', ('P_U101', '8'))]:
        o, a = pad('P_D101', pin), pad(*anchor)
        prior = oldpad(*anchor); expected = {aliases.get(u, u) for u in before['all_groups'][prior['group']]}
        expected |= {o['uuid']} | {v['uuid'] for v in report['vias'] if v['net'] == o['net']}
        assert memberships[o['uuid']] == expected and a['uuid'] in expected
        connections.append(dict(pin=pin, net=o['net'], anchor=list(anchor), via_count=6, actual_pad_position_mm=o['position_mm']))
    assert before['native_uncapped_opens'] == 2374 and after['native_uncapped_opens'] == 2372
    auxold = oldpad('P_U102', '4'); auxnew = pad('P_U102', '4')
    assert memberships[auxnew['uuid']] == {aliases.get(u, u) for u in before['all_groups'][auxold['group']]}
    assert memberships[auxnew['uuid']].isdisjoint(memberships[pad('P_U101', '8')['uuid']])
    for pin in ['1', '2']:
        o = pad('G_NT1', pin); assert memberships[o['uuid']] == {o['uuid']}
    oldzones, zones = [{z['uuid']: z for z in c['zones']} for c in [before, after]]
    oldz, newz = [{str(first(z, 'uuid')[1]): z for z in children(t, 'zone')} for t in trees]
    changed = set(report['changed_existing_zone_fills']); declared = {z['uuid']: z for z in report['new_zones']}
    assert len(changed) == 6 and len(zones) == 21 and len(oldzones) == 19 and zones.keys()-oldzones.keys() == declared.keys()
    def without_fill(z):
        return [n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
    for u in oldzones:
        assert without_fill(oldz[u]) == without_fill(newz[u])
        if u not in changed:
            assert oldz[u] == newz[u] and oldzones[u] == zones[u]
    assert len(fill['unchanged_existing_zone_canonical_polygon_match']) == 13
    assert all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    contacts = []
    for u, r in declared.items():
        z = zones[u]; g = shape(z['polygons']); authored = Polygon(r['outer_mm'])
        assert z['layer'] == 'B.Cu' and z['net'] == r['net'] and len(z['polygons']) == 1
        assert authored.equals(shape(z['authored_outline'])) and authored.buffer(2e-6).covers(g)
        assert first(newz[u], 'connect_pads')[1] == 'yes'
        assert float(first(first(newz[u], 'connect_pads'), 'clearance')[1]) == .2
        assert float(first(newz[u], 'min_thickness')[1]) == .25
        direct = [o for o in new.values() if o['layers'].get('B.Cu') and o['net'] == z['net']
                  and g.intersection(shape(o['layers']['B.Cu'])).area > 1e-9]
        pin = '1' if z['net'] == 'PWR_DC_IN' else '2'; target = pad('P_D101', pin)
        assert target in direct and all(o['uuid'] in memberships[target['uuid']] for o in direct)
        newcontacts = {o['uuid'] for o in direct if o['uuid'] in added}
        assert newcontacts == {v['uuid'] for v in report['vias'] if v['net'] == z['net']} and len(newcontacts) == 6
        gap = min(g.distance(shape(o['layers']['B.Cu'])) for o in new.values() if o['net'] != z['net'] and o['layers'].get('B.Cu'))
        assert gap >= .1985
        contacts.append(dict(uuid=u, net=z['net'], layer='B.Cu', area_mm2=g.area, directly_contacted_pads=sorted([o['ref'], o['pin']] for o in direct if o['kind'] == 'PAD'),
                             directly_contacted_vias=sorted(o['uuid'] for o in direct if o['kind'] == 'PCB_VIA'), minimum_foreign_copper_gap_mm=gap))
    # Each new via directly reaches both paired force planes. All prior plane
    # contacts are preserved electrically; refills must not leave loose islands.
    for z in zones.values():
        for p in z['polygons']:
            g = Polygon(p['outer'], p['holes'])
            direct = [o for o in new.values() if o['net'] == z['net'] and o['layers'].get(z['layer'])
                      and g.intersection(shape(o['layers'][z['layer']])).area > 1e-9]
            assert direct and len({o['group'] for o in direct}) == 1, z['uuid']
    for v in report['vias']:
        pair = ['In2.Cu', 'In3.Cu'] if v['net'] == 'PWR_DC_IN' else ['In4.Cu', 'In5.Cu']
        for layer in pair:
            assert any(z['net'] == v['net'] and z['layer'] == layer and
                       shape(z['polygons']).intersection(shape(new[v['uuid']]['layers'][layer])).area > 1e-9 for z in zones.values())
    # Recheck every previously complete track projection on adjacent AGND
    # copper, preserving each distinct native ground group (including AUX).
    def references(cap, objs):
        refs = {}
        for z in cap['zones']:
            if z['net'] != 'PWR_AGND':
                continue
            g = shape(z['polygons'])
            groups = {o['group'] for o in objs.values() if o['net'] == z['net'] and o['layers'].get(z['layer'])
                      and g.intersection(shape(o['layers'][z['layer']])).area > 1e-9}
            assert len(groups) == 1
            key = (z['layer'], next(iter(groups))); refs.setdefault(key, []).append(g)
        return {k: unary_union(v) for k, v in refs.items()}
    ref0, ref1 = references(before, old), references(after, new)
    coverage = []; layers = after['copper_layers']
    for u, o in old.items():
        if o['kind'] != 'PCB_TRACK' or o['net'] == 'PWR_AGND':
            continue
        layer, = o['layers']; i = layers.index(layer)
        adjacent = {layers[j] for j in [i-1, i+1] if 0 <= j < len(layers)}
        g = LineString([o['position_mm'], o['end_mm']]).buffer(o['width_mm']/2)
        for v in old.values():
            if v['kind'] == 'PCB_VIA' and v['net'] == o['net']:
                g = g.difference(Point(v['position_mm']).buffer(v['width_mm']/2+.215))
        if g.is_empty:
            continue
        for (rlayer, gid), reference in ref0.items():
            if rlayer not in adjacent or g.difference(reference.buffer(.0015)).area >= 1e-6:
                continue
            anchor = aliases.get(before['all_groups'][gid][0], before['all_groups'][gid][0])
            target = ref1.get((rlayer, new[anchor]['group']))
            assert target is not None
            uncovered = g.difference(target.buffer(.0015)).area
            assert uncovered < 1e-6, (u, layer, rlayer, uncovered)
            coverage.append(dict(track_uuid=u, reference_layer=rlayer, prior_ground_group=gid, uncovered_mm2=uncovered))
    assert coverage
    # Independent moved-package envelope checks, including opposite-face tails.
    placement = json.loads(sources[6].read_text()); records = {r['id']: r for r in placement['parts']}
    for r, template in [('P_C204', 'P_C205'), ('P_C104', 'P_C102'), ('P_C101', 'P_C102'),
                        *[(r, 'P_R102') for r in ['P_R101', 'P_R103', 'P_R104']]]:
        for k in ['side', 'angle', 'body_relative_xy', 'courtyard_relative_xy', 'additional_planar_reserves', 'tails_relative_xy']:
            records[r][k] = copy.deepcopy(records[template][k])
    records['P_C114'] = copy.deepcopy(records['P_C401'])
    receivers = []
    for ref, f in fps[1].items():
        if ref == 'P_D101':
            continue
        try:
            receivers.append((ref, box(*courtyard(f, 'B.CrtYd'))))
        except AssertionError:
            pass
        if ref not in records:
            continue
        r = records[ref]; x, y = map(float, first(f, 'at')[1:3]); delta = angle(f)-r['angle']
        assert first(f, 'layer')[1][0] == r['side']
        envelopes = ([r['body_relative_xy']] if r['side'] == 'B' else []) + r['tails_relative_xy']
        envelopes += [q['bounds'] for q in r['additional_planar_reserves'] if q['side'] == 'B']
        receivers.extend((ref, translate(rotate(box(*b), -delta, origin=(0, 0)), x, y)) for b in envelopes)
    court = box(*courtyard(fps[1]['P_D101'], 'B.CrtYd'))
    assert all(court.buffer(.3, join_style=2).intersection(g).area < 1e-8 for ref, g in receivers)
    assert shape(after['outline']).buffer(-.5).covers(court)
    mounts = [o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts) == 15
    assert all(court.distance(Point(o['position_mm'])) >= max(3.6, max(o['drill_mm'])/2+.5)+.3 for o in mounts)
    z0 = placement['power_Z']; height = records['P_D101']['height_mm']
    assert height == 2.8 and height >= 2.44
    zrange = [z0-.2-height, z0+.2]; assert zrange[0] >= 3.05 and zrange[1] <= 43.35
    contexts = [c for c in placement['context'] if not c['id'].startswith('inlet_')]
    for name, x, y, z, dx, dy, t, *_ in json.loads(sources[7].read_text())['additional_panel_PCBS']:
        contexts.append(dict(id=name, xy=[x, y, x+dx, y+dy], z=[z, z+t]))
    for c in contexts:
        if min(zrange[1]+.25, c['z'][1]) > max(zrange[0]-.25, c['z'][0]):
            assert court.buffer(.25, join_style=2).intersection(box(*c['xy'])).area < 1e-8, c['id']
    smd = [shape(ps) for o in new.values() if o['kind'] == 'PAD' and not any(o['drill_mm'])
           for l, ps in o['layers'].items() if l in ['F.Cu', 'B.Cu'] and ps]
    st = STRtree(smd)
    gaps = [Point(o['position_mm']).distance(smd[int(st.nearest(Point(o['position_mm'])))])-o['drill_mm']/2
            for o in new.values() if o['kind'] == 'PCB_VIA']
    assert len(gaps) == 262 and min(gaps) >= .15-2e-6
    for folder in [BASE, OUT]:
        native = json.loads((folder/'review.json').read_text())
        for n, h in native['artifact_sha256'].items():
            assert sha(folder/n) == h, n
        sources.extend(folder/n for n in ['power_protection.kicad_pcb', 'netlist.xml', 'review.json', 'drc.json', 'erc.json'])
    drc, erc = [json.loads((OUT/n).read_text()) for n in ['drc.json', 'erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['severity'] == 'warning' and v['type'] == 'ground_pin_not_ground' for v in warnings)
    filledtree = read_sexpr((FILLED/'power_protection.kicad_pcb').read_text()); nativecopy = copy.deepcopy(trees[1])
    removed = 0
    for t in [filledtree, nativecopy]:
        for f in children(t, 'footprint'):
            paths = children(f, 'path')
            if not paths:
                continue
            assert all(p == paths[0] for p in paths)
            if t is nativecopy:
                assert len(paths) == 1
            else:
                removed += len(paths)-1
                for p in paths[1:]:
                    f.remove(p)
    assert filledtree == nativecopy
    sources.extend([FILLED/'power_protection.kicad_pcb', *[REPO/'hardware/fabrication'/n for n in [
        'verify_native_zone_unfracture.py', 'route_nf_surface.py', 'audit_two_board_power_delta.py']],
        REPO/'hardware/electronics/output_stage/check_placement.py', REPO/'hardware/fabrication/parts/input-tvs-01/smbj.pdf'])
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        native_zone_fidelity=fidelity, unchanged_complete_footprints=1100, moved_footprints=1,
        moved_pad_instances=2, maximum_moved_pad_polygon_error_mm=maxerror, pin_net_map_values_packages_unchanged=True,
        previous_native_connection_groups_preserved=len(before['all_groups']), old_opens=2374, new_opens=2372,
        connections_closed=2, TVS_terminal_connections=connections, new_zone_contacts=contacts,
        added_vias=12, total_vias=262, total_tracks=2444, zones=21, unchanged_existing_fills=13,
        all_new_vias_directly_contact_both_force_planes=True, all_filled_pieces_connected=True,
        AUX_group_and_local_copper_unchanged=True, G_NT1_isolated=True,
        previous_full_width_adjacent_reference_cases=coverage, moved_mechanical_screen_findings=0,
        TVS_bottom_installed_Z_range_mm=zrange, TVS_maximum_body_height_mm=2.44,
        all_via_minimum_drill_to_SMD_mm=min(gaps), geometry_errors=0, parity_errors=0, ERC_errors=0, ERC_warnings=2,
        native_physical_delta=False, duplicate_identical_instance_paths_removed=removed,
        surge_current_thermal_temperature_and_fuse_coordination_qualified=False,
        full_installed_fit_verified=False, stack_accepted=False, fabrication_released=False)
    with (OUT/'input-tvs-review.json').open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({k: result[k] for k in ['connections_closed', 'previous_native_connection_groups_preserved', 'total_vias', 'all_via_minimum_drill_to_SMD_mm']}))
    print('Preserved reference cases:', len(coverage))


if __name__ == '__main__':
    run()
