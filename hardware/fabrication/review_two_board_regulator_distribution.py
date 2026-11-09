"""Independent audit of the regulator feed and force-return bridges."""
import json
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE = STAGING/'two-board-power-inlet-fuse-native-01'
OUT = STAGING/'two-board-power-regulator-distribution-native-03'
FILLED = STAGING/'two-board-power-regulator-distribution-filled-03'
BEFORE = STAGING/'two-board-power-routing-inputs-2372-inlet-fuse-01/capture.json'
AFTER = STAGING/'two-board-power-routing-inputs-2369-regulator-distribution-03/capture.json'


def run():
    sources = [Path(__file__), BEFORE, AFTER, OUT/'regulator-distribution-routing.json', FILLED/'local-plane-fill.json',
               BASE/'power_protection.kicad_pcb', OUT/'power_protection.kicad_pcb',
               BASE/'netlist.xml', OUT/'netlist.xml', OUT/'review.json', OUT/'erc.json',
               REPO/'hardware/fabrication/route_nf_surface.py', REPO/'hardware/fabrication/verify_native_zone_unfracture.py']
    before, after, report, fill = [json.loads(p.read_text()) for p in sources[1:5]]
    for p in [BEFORE, AFTER, OUT/'regulator-distribution-routing.json', FILLED/'local-plane-fill.json', OUT/'review.json']:
        d = json.loads(p.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, h in d.get(field, {}).items():
                q = Path(name)
                if not q.is_absolute():
                    q = (REPO if name.startswith(('hardware/', 'tests/')) else p.parent)/q
                assert sha(q) == h, (p, name)
    fidelity = verify_capture(after)
    assert report['added_tracks'] == report['added_vias'] == 0 and not report['moved_footprints'] and not report['circuit_changes']
    b0, b1 = [read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE, OUT]]
    strip_zones = lambda b: [n for n in b if not (isinstance(n, list) and n and n[0] == 'zone')]
    assert strip_zones(b0) == strip_zones(b1), 'Non-zone PCB change'
    parts0, pins0 = read_netlist(BASE/'netlist.xml'); parts1, pins1 = read_netlist(OUT/'netlist.xml')
    assert parts0.keys() == parts1.keys() and pins0 == pins1
    assert all(parts0[r].findtext(k) == parts1[r].findtext(k) for r in parts0 for k in ['value', 'footprint', 'datasheet'])
    old, new = [{o['uuid']: o for o in c['objects']} for c in [before, after]]
    physical = lambda o: {k: v for k, v in o.items() if k not in ['uuid', 'group']}
    aliases = {}
    for u in old.keys()-new.keys():
        assert old[u]['kind'] == 'PAD'
        hits = [v for v in new.keys()-old.keys() if physical(old[u]) == physical(new[v])]
        assert len(hits) == 1
        aliases[u] = hits[0]
    assert len(set(aliases.values())) == len(aliases)
    assert {aliases.get(u, u) for u in old} == set(new)
    assert all(physical(o) == physical(new[aliases.get(u, u)]) for u, o in old.items())
    memberships = {u: set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        translated = {aliases.get(u, u) for u in g}
        assert translated <= memberships[next(iter(translated))]
    pad = lambda ref, pin: next(o for o in new.values() if o.get('ref') == ref and o.get('pin') == pin)
    oldpad = lambda ref, pin: next(o for o in old.values() if o.get('ref') == ref and o.get('pin') == pin)
    joins = []
    for net, anchors in [('PWR_MODULE_FEED_IN', [('P_U101', '17'), ('P_U20', '8'), ('P_U23', '8')]),
                         ('PWR_AGND', [('P_C103', '2'), ('P_U23', '5')])]:
        expected = set().union(*[{aliases.get(u, u) for u in before['all_groups'][oldpad(*a)['group']]} for a in anchors])
        assert memberships[pad(*anchors[0])['uuid']] == expected
        assert all(memberships[pad(*a)['uuid']] == expected for a in anchors)
        joins.append(dict(net=net, anchors=anchors, old_groups=len(anchors), objects_in_joined_group=len(expected)))
    aux = oldpad('P_U102', '4')
    assert memberships[pad('P_U102', '4')['uuid']] == {aliases.get(u, u) for u in before['all_groups'][aux['group']]}
    assert memberships[pad('P_U102', '4')['uuid']].isdisjoint(memberships[pad('P_C103', '2')['uuid']])
    for pin in ['1', '2']:
        o = pad('G_NT1', pin); assert memberships[o['uuid']] == {o['uuid']}
    assert before['native_uncapped_opens'] == 2372 and after['native_uncapped_opens'] == 2369
    z0, z1 = [{z['uuid']: z for z in c['zones']} for c in [before, after]]
    t0, t1 = [{first(z, 'uuid')[1]: z for z in children(b, 'zone')} for b in [b0, b1]]
    changed = set(report['refilled_existing_zones'])
    declared = {z['uuid']: z for z in report['new_zones']}
    assert z1.keys()-z0.keys() == declared.keys() and len(z1) == 24
    without_fill = lambda z: [n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
    deltas = []
    for u in z0:
        assert without_fill(t0[u]) == without_fill(t1[u])
        if u not in changed:
            assert t0[u] == t1[u] and z0[u] == z1[u]
        else:
            a, b = shape(z0[u]['polygons']), shape(z1[u]['polygons'])
            deltas.append(dict(uuid=u, layer=z0[u]['layer'], net=z0[u]['net'], removed_mm2=a.difference(b).area, added_mm2=b.difference(a).area))
    assert len(fill['unchanged_existing_zone_canonical_polygon_match']) == 17 and all(fill['unchanged_existing_zone_canonical_polygon_match'].values())

    def component_contacts(g, layer, net, cap):
        # Zone bridges need not contain a pad themselves. Follow same-layer
        # filled copper to its physical contacts, with only capture-grid slack.
        candidates = [shape(z['polygons']) for z in cap['zones'] if z['layer'] == layer and z['net'] == net]
        region = g.buffer(.0015)
        while True:
            hits = [h for h in candidates if region.intersects(h)]
            expanded = unary_union([region, *[h.buffer(.0015) for h in hits]])
            if expanded.equals(region):
                break
            region = expanded
        contacts = [o for o in cap['objects'] if o['net'] == net and o['layers'].get(layer)
                    and region.intersection(shape(o['layers'][layer])).area > 1e-9]
        assert contacts
        return contacts

    zones = []
    for u, r in declared.items():
        z = z1[u]; g = shape(z['polygons'])
        assert z['net'] == r['net'] and z['layer'] == r['layer']
        authored = Polygon(r['outer_mm'], r['holes_mm'])
        assert authored.equals(shape(z['authored_outline'])) and authored.buffer(2e-6).covers(g)
        assert int(first(t1[u], 'priority')[1]) == r['priority']
        assert first(t1[u], 'connect_pads')[1] == 'yes' and float(first(first(t1[u], 'connect_pads'), 'clearance')[1]) == .2
        anchor = pad('P_U20', '8') if z['net'] == 'PWR_MODULE_FEED_IN' else pad('P_C103', '2')
        for poly in z['polygons']:
            contacts = component_contacts(Polygon(poly['outer'], poly['holes']), z['layer'], z['net'], after)
            assert all(o['uuid'] in memberships[anchor['uuid']] for o in contacts)
        gap = min(g.distance(shape(o['layers'][z['layer']])) for o in new.values()
                  if o['net'] != z['net'] and o['layers'].get(z['layer']))
        assert gap >= .1985
        zones.append(dict(uuid=u, label=r['label'], layer=z['layer'], area_mm2=g.area,
                          fill_pieces=len(z['polygons']), minimum_foreign_copper_gap_mm=gap))

    def references(cap):
        refs = {}
        for z in cap['zones']:
            if z['net'] != 'PWR_AGND':
                continue
            g = shape(z['polygons'])
            groups = {o['group'] for o in component_contacts(g, z['layer'], z['net'], cap)}
            assert len(groups) == 1, (z['uuid'], groups)
            refs.setdefault((z['layer'], next(iter(groups))), []).append(g)
        return {k: unary_union(v) for k, v in refs.items()}
    refs0, refs1 = references(before), references(after)
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
        for (rlayer, gid), reference in refs0.items():
            if rlayer not in adjacent or g.difference(reference.buffer(.0015)).area >= 1e-6:
                continue
            anchor = before['all_groups'][gid][0]; mapped = aliases.get(anchor, anchor)
            target = refs1[(rlayer, new[mapped]['group'])]
            uncovered = g.difference(target.buffer(.0015)).area
            assert uncovered < 1e-6, (u, layer, rlayer, uncovered)
            coverage.append(dict(track_uuid=u, reference_layer=rlayer, uncovered_mm2=uncovered))
    feed = next(z for z in after['zones'] if z['uuid'] in declared and z['net'] == 'PWR_MODULE_FEED_IN')
    region = shape(feed['polygons'])
    for o in new.values():
        if o['net'] == feed['net'] and o['layers'].get('In1.Cu'):
            region = region.difference(shape(o['layers']['In1.Cu']).buffer(.215))
    ground = refs1[('In1.Cu', pad('P_C103', '2')['group'])]
    uncovered = region.difference(ground.buffer(.0015))
    native = json.loads((OUT/'review.json').read_text())
    assert native['geometry_findings'] == native['schematic_parity_findings'] == 0
    erc = json.loads((OUT/'erc.json').read_text())
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['severity'] == 'warning' and v['type'] == 'ground_pin_not_ground' for v in warnings)
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        zone_capture_fidelity=fidelity, old_opens=2372, new_opens=2369, closed_connections=3,
        all_prior_groups_preserved=len(before['all_groups']), all_objects_physical_unchanged=len(old),
        all_footprints_unchanged=len(children(b0, 'footprint')), unchanged_pin_net_entries=len(pins0),
        exact_non_zone_board_tree_unchanged=True, native_group_merges=joins,
        all_previous_zone_outlines_unchanged=True, unchanged_existing_fills=17, refilled_zone_deltas=deltas,
        new_zones=zones, AUX_group_and_copper_preserved=True, G_NT1_still_isolated=True,
        previous_full_width_adjacent_ground_cases_preserved=len(coverage), prior_reference_coverage=coverage,
        new_feed_In1_ground_uncovered_mm2=uncovered.area,
        new_feed_reference_screen_area_mm2=region.area,
        new_feed_reference_scope='Same native main-ground group; exclude feed contacts with their 0.215 mm antipad margins.',
        geometry_errors=0, parity_errors=0, ERC_errors=0, ERC_warnings=2,
        complete_current_thermal_noise_and_return_qualification=False, fabrication_released=False)
    with (OUT/'regulator-distribution-review.json').open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({k: result[k] for k in ['new_opens', 'all_prior_groups_preserved', 'new_zones',
          'previous_full_width_adjacent_ground_cases_preserved', 'new_feed_In1_ground_uncovered_mm2']}))


if __name__ == '__main__':
    run()
