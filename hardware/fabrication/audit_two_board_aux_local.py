"""Check native AUX placement, local connections and all retained copper."""
import copy
import json
import math
from pathlib import Path
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape

BASE = STAGING / 'two-board-power-u23-quiet-native-01'
OUT = STAGING / 'two-board-power-aux-local-native-01'
BEFORE = STAGING / 'two-board-power-routing-inputs-2462-u23-quiet/capture.json'
AFTER = STAGING / 'two-board-power-routing-inputs-2447-aux-local/capture.json'


def orientation(f):
    at = first(f, 'at')
    return float(at[3]) if len(at) > 3 else 0


def run():
    report_path = OUT / 'aux-local-routing.json'
    report, before, after = [json.loads(p.read_text()) for p in [report_path, BEFORE, AFTER]]
    for d in [report, before, after]:
        for name, h in d['source_sha256'].items():
            assert sha(REPO / name) == h, name
    trees = [read_sexpr((p / 'power_protection.kicad_pcb').read_text()) for p in [BASE, OUT]]
    fps = [{prop(f, 'Reference')[2]: f for f in children(t, 'footprint')} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[1]) == 1100
    moves = {r['ref']: r for r in report['moves']}
    assert set(moves) == {'P_U102', 'P_C113', 'P_C106', 'P_C107', 'P_C110', 'P_R108', 'P_R109', 'P_R130'}
    for ref, old in fps[0].items():
        new = fps[1][ref]
        if ref not in moves:
            assert geometry(old) == geometry(new), ref
            continue
        r = moves[ref]
        assert list(map(float, first(old, 'at')[1:3])) == r['old_xy']
        assert list(map(float, first(new, 'at')[1:3])) == r['new_xy']
        assert (orientation(new) - orientation(old)) % 360 == r['rotation_added_degrees'] % 360
        restored = copy.deepcopy(new)
        first(restored, 'at')[:] = first(old, 'at')
        for tag in ['pad', 'property', 'fp_text']:
            aa, bb = children(old, tag), children(restored, tag)
            assert len(aa) == len(bb)
            for a, b in zip(aa, bb):
                ats, bts = children(a, 'at'), children(b, 'at')
                assert len(ats) == len(bts)
                for x, y in zip(ats, bts):
                    assert list(map(float, x[1:3])) == list(map(float, y[1:3]))
                    oa = float(x[3]) if len(x) > 3 else 0
                    na = float(y[3]) if len(y) > 3 else 0
                    assert (na - oa) % 360 == r['rotation_added_degrees'] % 360
                    y[:] = x
        assert geometry(old) == geometry(restored), ref
    def shell(t):
        return [n for n in t if not (isinstance(n, list) and n and n[0] in ['footprint', 'segment', 'via', 'arc', 'net'])]
    assert shell(trees[0]) == shell(trees[1])
    oldparts, oldpins = read_netlist(BASE / 'netlist.xml')
    parts, pins = read_netlist(OUT / 'netlist.xml')
    assert oldpins == pins and oldparts.keys() == parts.keys() and len(parts) == 1085
    for ref in parts:
        for field in ['value', 'footprint']:
            assert oldparts[ref].findtext(field) == parts[ref].findtext(field)
    old, new = [{o['uuid']: o for o in c['objects']} for c in [before, after]]
    def physical(o):
        return {k: v for k, v in o.items() if k not in ['uuid', 'group']}
    def expected_position(o):
        r = moves[o['ref']]
        return translate(rotate(Point(o['position_mm']), -r['rotation_added_degrees'], origin=r['old_xy']),
                         r['new_xy'][0] - r['old_xy'][0], r['new_xy'][1] - r['old_xy'][1])
    aliases = {}
    for u in old.keys() - new.keys():
        o = old[u]
        assert o['kind'] == 'PAD'
        if o.get('ref') in moves:
            assert not o.get('pin') and not any(o['layers'].values())
            hits = [v for v in new.keys() - old.keys() if new[v]['kind'] == 'PAD'
                    and new[v].get('ref') == o['ref'] and not new[v].get('pin')
                    and expected_position(o).distance(Point(new[v]['position_mm'])) < 2e-6]
        else:
            hits = [v for v in new.keys() - old.keys() if physical(o) == physical(new[v])]
        assert len(hits) == 1, (u, hits)
        aliases[u] = hits[0]
    assert len(aliases) == len(set(aliases.values()))
    oldkeys = {aliases.get(u, u) for u in old}
    maxerror = 0
    movedpads = 0
    for uid, o in old.items():
        n = new[aliases.get(uid, uid)]
        ref = o.get('ref')
        if ref not in moves:
            assert physical(o) == physical(n), uid
            continue
        movedpads += 1
        assert o['kind'] == n['kind'] == 'PAD'
        for field in ['ref', 'pin', 'net', 'drill_mm']:
            assert o[field] == n[field]
        assert expected_position(o).distance(Point(n['position_mm'])) < 2e-6
        r = moves[ref]
        assert (n['orientation_degrees'] - o['orientation_degrees']) % 360 == r['rotation_added_degrees'] % 360
        assert o['layers'].keys() == n['layers'].keys()
        for layer, ps in o['layers'].items():
            if not ps:
                assert not n['layers'][layer]
                continue
            g = translate(rotate(shape(ps), -r['rotation_added_degrees'], origin=r['old_xy']),
                          r['new_xy'][0] - r['old_xy'][0], r['new_xy'][1] - r['old_xy'][1])
            error = g.hausdorff_distance(shape(n['layers'][layer]))
            maxerror = max(maxerror, error)
            assert error < 3e-6, (ref, o['pin'], error)
    assert before['zones'] == after['zones'] and len(after['zones']) == 4
    groups = {u: set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped = {aliases.get(u, u) for u in g}
        assert mapped <= groups[next(iter(mapped))]
    def pad(ref, pin):
        return next(o for o in new.values() if o.get('ref') == ref and o.get('pin') == pin)
    intended = {
        'input-and-enable': [('P_U102','8'), ('P_U102','5'), ('P_C113','1')],
        'output': [('P_U102','1'), ('P_C106','1'), ('P_C107','1'), ('P_R108','1')],
        'ground': [('P_U102','4'), ('P_U102','9'), ('P_C106','2'), ('P_C107','2'), ('P_C113','2'), ('P_C110','2'), ('P_R109','2')],
        'delay': [('P_U102','7'), ('P_C110','1')],
        'feedback': [('P_U102','2'), ('P_R109','1'), ('P_R130','2')],
        'trim': [('P_R108','2'), ('P_R130','1')],
    }
    verified = {}
    for name, terminals in intended.items():
        g = groups[pad(*terminals[0])['uuid']]
        assert all(pad(*p)['uuid'] in g for p in terminals), name
        verified[name] = g
    assert len({tuple(sorted(g)) for g in verified.values()}) == 6
    for pin in ['3', '6']:
        assert groups[pad('P_U102', pin)['uuid']] == {pad('P_U102', pin)['uuid']}
    allowed = set().union(*verified.values())
    added = set()
    mounts = [o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts) == 15
    for r in report['routes']:
        points = r['path_mm']
        assert len(points) == len(r['segment_uuids']) + 1
        line = LineString(points)
        assert abs(line.length - r['length_mm']) < 2e-6 and line.length <= r['maximum_length_mm']
        for u, p, q in zip(r['segment_uuids'], points, points[1:]):
            assert u not in added and u not in oldkeys
            added.add(u)
            o = new[u]
            assert o['kind'] == 'PCB_TRACK' and o['net'] == r['net'] and o['width_mm'] == r['width_mm']
            assert set(o['layers']) == {r['layer']}
            assert math.dist(o['position_mm'], p) < 2e-6 and math.dist(o['end_mm'], q) < 2e-6
            assert u in allowed and set(r['segment_uuids']) <= groups[u]
            assert all(LineString([p, q]).distance(Point(m['position_mm'])) >
                       max(3.6, max(m['drill_mm']) / 2 + .5) + o['width_mm'] / 2 + .01 - 2e-6 for m in mounts)
    for v in report['vias']:
        u = v['uuid']
        assert u not in oldkeys and u not in added
        added.add(u)
        o = new[u]
        assert o['kind'] == 'PCB_VIA' and o['net'] == v['net']
        assert o['width_mm'] == .6 and o['drill_mm'] == .3 and o['via_type'] == 4
        assert o['position_mm'] == v['position_mm'] and o['span'] == ['F.Cu', 'B.Cu']
        assert set(o['layers']) == set(after['copper_layers']) and u in allowed
        assert all(Point(o['position_mm']).distance(shape(z['authored_outline'])) > .61 for z in after['zones'])
    assert added == new.keys() - oldkeys and len(report['routes']) == 20 and len(report['vias']) == 5 and len(added) == 37
    # Independent native-envelope and installation-context check of moved parts.
    placement_path = STAGING / 'two-board-placement-05/capture.json'
    placement = json.loads(placement_path.read_text())
    records = {r['id']: r for r in placement['parts']}
    assert records['P_C204']['value'] == records['P_C205']['value']
    assert records['P_C204']['height_mm'] == records['P_C205']['height_mm']
    assert first(fps[1]['P_C204'], 'layer')[1] == 'B.Cu' and orientation(fps[1]['P_C204']) == 0
    for key in ['side', 'angle', 'body_relative_xy', 'courtyard_relative_xy', 'additional_planar_reserves', 'tails_relative_xy']:
        records['P_C204'][key] = copy.deepcopy(records['P_C205'][key])
    receivers = {'F': [], 'B': []}
    for ref, f in fps[1].items():
        for side in ['F', 'B']:
            try:
                receivers[side].append((ref, box(*courtyard(f, side + '.CrtYd'))))
            except AssertionError:
                pass
        rec = records.get(ref)
        if rec and ref not in moves:
            assert first(f, 'layer')[1][0] == rec['side'], ref
            x, y = map(float, first(f, 'at')[1:3])
            delta = orientation(f) - rec['angle']
            def envelope(b):
                return translate(rotate(box(*b), -delta, origin=(0, 0)), x, y)
            receivers[rec['side']].append((ref, envelope(rec['body_relative_xy'])))
            for e in rec['additional_planar_reserves']:
                receivers[e['side']].append((ref, envelope(e['bounds'])))
            for b in rec['tails_relative_xy']:
                assert rec['side'] == 'F'
                receivers['B'].append((ref, envelope(b)))
    contexts = [c for c in placement['context'] if not c['id'].startswith('inlet_')]
    allocation_path = STAGING / 'assembly-layout-04/allocation.json'
    for name, x, y, z, dx, dy, t, *_ in json.loads(allocation_path.read_text())['additional_panel_PCBS']:
        contexts.append(dict(id=name, xy=[x,y,x+dx,y+dy], z=[z,z+t]))
    outline = shape(after['outline']).buffer(-.5)
    for ref in moves:
        f = fps[1][ref]
        side = first(f, 'layer')[1][0]
        g = box(*courtyard(f, side + '.CrtYd'))
        assert outline.covers(g)
        assert all(g.buffer(.3, join_style=2).intersection(h).area < 1e-8 for other,h in receivers[side] if other != ref), ref
        assert all(g.distance(Point(m['position_mm'])) >= max(3.6, max(m['drill_mm'])/2 + .5) + .3 - 1e-6 for m in mounts)
        height = records[ref]['height_mm']
        z0 = placement['power_Z']
        z = [z0-.2+1.44,z0+.2+1.76+height] if side == 'F' else [z0-.2-height,z0+.2]
        assert z[0] >= 3.05 and z[1] <= 43.35
        for c in contexts:
            if min(z[1]+.25,c['z'][1]) > max(z[0]-.25,c['z'][0]):
                assert g.buffer(.25,join_style=2).intersection(box(*c['xy'])).area < 1e-8, (ref,c['id'])
    for ref in ['P_U102','P_C106','P_C113','P_C110','P_C107']:
        assert first(fps[1][ref], 'layer')[1] == 'F.Cu'
    smd = [shape(ps) for o in new.values() if o['kind'] == 'PAD' and not any(o['drill_mm'])
           for layer,ps in o['layers'].items() if layer in ['F.Cu','B.Cu'] and ps]
    smdtree = STRtree(smd)
    gaps = []
    for o in new.values():
        if o['kind'] == 'PCB_VIA':
            p = Point(o['position_mm'])
            gap = p.distance(smd[int(smdtree.nearest(p))]) - o['drill_mm']/2
            assert gap >= .15 - 2e-6
            gaps.append(gap)
    assert len(gaps) == 186 and sum(o['kind'] == 'PCB_TRACK' for o in new.values()) == 2289
    for folder in [BASE, OUT]:
        native = json.loads((folder / 'review.json').read_text())
        for name,h in native['artifact_sha256'].items():
            assert sha(folder / name) == h
    drc, erc = [json.loads((OUT / n).read_text()) for n in ['drc.json','erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['type'] == 'ground_pin_not_ground' and v['severity'] == 'warning' for v in warnings)
    assert before['native_uncapped_opens'] == 2462 and after['native_uncapped_opens'] == 2447
    paths = [Path(__file__),report_path,BEFORE,AFTER,placement_path,allocation_path,
             REPO/'hardware/electronics/output_stage/check_placement.py',
             REPO/'hardware/fabrication/audit_two_board_power_delta.py', REPO/'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE, OUT]:
        paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
                  components=1085,footprints=1100,unchanged_complete_pin_net_map=True,
                  all_old_tracks_vias_unchanged=True, all_unmoved_pads_unchanged=True,
                  all_values_packages_and_sides_preserved=True,moved_footprints=8,changed_pad_instances=movedpads,
                  maximum_native_pad_polygon_error_mm=maxerror,
                  all_previous_native_connection_groups_preserved=len(before['all_groups']),
                  all_four_authored_zones_and_native_fills_unchanged=True,
                  local_route_sections=20,added_segments=32,added_vias=5,
                  old_opens=2462,new_opens=2447,connections_closed=15,
                  verified_terminal_groups=intended,PG_and_NC_not_routed=True,
                  regulator_and_capacitors_same_front_side=True,
                  local_route_lengths_mm={r['label']:r['length_mm'] for r in report['routes']},
                  minimum_all_via_drill_to_SMD_mm=min(gaps),vias_screened=186,
                  moved_courtyard_context_findings=0,geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
                  AUX_input_output_ground_regions_and_thermal_vias_complete=False,
                  AUX_load_derating_startup_and_thermal_qualified=False,
                  full_installed_fit_verified=False,electrical_and_manufacturing_qualified=False,fabrication_released=False)
    with (OUT/'aux-local-audit.json').open('x') as f:
        json.dump(result,f,indent=2)
        f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','local_route_lengths_mm','verified_terminal_groups']},indent=2))


if __name__ == '__main__':
    run()
