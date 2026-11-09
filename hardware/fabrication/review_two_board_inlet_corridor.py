"""Independent native geometry/connectivity review of the TBP33 inlet candidate.

This checks copper, not electrical current capacity or installed thermal margin.
Multiple filled pieces are allowed only when every piece contacts the intended
native electrical group; their count and contacts remain explicit in the report.
"""
import copy
import json
from pathlib import Path

from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE = STAGING / 'two-board-power-fast-ov-return-native-02'
OUT = STAGING / 'two-board-power-inlet-corridor-native-01'
FILLED = STAGING / 'two-board-power-inlet-corridor-filled-01'
BEFORE = STAGING / 'two-board-power-routing-inputs-2383-fast-ov-return-02/capture.json'
AFTER = STAGING / 'two-board-power-routing-inputs-2374-inlet-corridor-01/capture.json'


def run():
    sources = [Path(__file__), BEFORE, AFTER, OUT/'inlet-corridor-routing.json',
               FILLED/'local-plane-fill.json', BASE/'fast-ov-return-plane-review.json',
               BASE/'fast-ov-return-audit.json']
    before, after, report, fill = [json.loads(p.read_text()) for p in sources[1:5]]
    for d in [before, after, report, fill]:
        for p, h in d['source_sha256'].items():
            assert sha(REPO/p) == h, p
    for n, h in fill['artifact_sha256'].items():
        assert sha(FILLED/n) == h, n
    fidelity = verify_capture(after)
    old, new = [{o['uuid']: o for o in c['objects']} for c in [before, after]]
    physical = lambda o: {k: v for k, v in o.items() if k not in ['uuid', 'group']}
    aliases = {}
    for u in old.keys()-new.keys():
        assert old[u]['kind'] == 'PAD'
        hits = [v for v in new.keys()-old.keys() if physical(old[u]) == physical(new[v])]
        assert len(hits) == 1, u
        aliases[u] = hits[0]
    assert len(set(aliases.values())) == len(aliases)
    for u, o in old.items():
        assert physical(o) == physical(new[aliases.get(u, u)]), u
    added = new.keys()-{aliases.get(u, u) for u in old}
    assert added == {v['uuid'] for v in report['vias']} and len(added) == 16
    for v in report['vias']:
        o = new[v['uuid']]
        assert o['kind'] == 'PCB_VIA' and o['net'] == v['net'] == 'PWR_DC_IN'
        assert o['position_mm'] == v['position_mm'] and o['width_mm'] == .6 and o['drill_mm'] == .3
        assert o['span'] == ['F.Cu', 'B.Cu'] and o['via_type'] == 4
        assert set(o['layers']) == set(after['copper_layers'])
    assert not report['moved_footprints'] and not report['retired_tracks'] and not report['retired_vias']
    groups = {u: set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped = {aliases.get(u, u) for u in g}
        assert mapped <= groups[next(iter(mapped))]
    pad = lambda r, p: next(o for o in new.values() if o.get('ref') == r and o.get('pin') == p)
    pads = lambda g: sorted([new[u]['ref'], new[u]['pin']] for u in g if new[u]['kind'] == 'PAD')
    dc = groups[pad('I_F1', '2')['uuid']]
    ground = groups[pad('I_J1', '2')['uuid']]
    assert pad('P_Q101', '1')['uuid'] in dc and pad('P_U101', '8')['uuid'] in ground
    reverse = {aliases.get(u, u): u for u in old}
    merges = []
    for g in after['all_groups'].values():
        prior = {old[reverse[u]]['group'] for u in g if u in reverse and old[reverse[u]]['group']}
        if len(prior) < 2:
            continue
        merges.append(dict(net=new[g[0]]['net'], previous_groups=len(prior),
            old_pad_groups=sorted(sorted([old[u]['ref'], old[u]['pin']] for u in before['all_groups'][k]
                                        if old[u]['kind'] == 'PAD') for k in prior)))
    assert sorted((r['net'], r['previous_groups']) for r in merges) == [('PWR_AGND', 9), ('PWR_DC_IN', 2)]
    assert before['native_uncapped_opens'] == 2383 and after['native_uncapped_opens'] == 2374
    assert sum(r['previous_groups']-1 for r in merges) == 9
    aux = groups[pad('P_U102', '4')['uuid']]
    oldaux = next(o for o in old.values() if o.get('ref') == 'P_U102' and o.get('pin') == '4')
    assert aux == {aliases.get(u, u) for u in before['all_groups'][oldaux['group']]}
    assert aux.isdisjoint(ground)
    for r, pins in [('G_NT1', ['1', '2']), ('P_D101', ['1', '2'])]:
        for p in pins:
            o = pad(r, p)
            assert groups[o['uuid']] == {o['uuid']}, (r, p)

    trees = [read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE, OUT]]
    fps = [{prop(f, 'Reference')[2]: f for f in children(t, 'footprint')} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[0]) == 1101
    assert all(geometry(f) == geometry(fps[1][r]) for r, f in fps[0].items())
    def shell(t):
        return [n for n in t if not (isinstance(n, list) and n and n[0] in ['footprint', 'segment', 'via', 'arc', 'net', 'zone'])]
    assert shell(trees[0]) == shell(trees[1])
    p0, pins0 = read_netlist(BASE/'netlist.xml')
    p1, pins1 = read_netlist(OUT/'netlist.xml')
    assert pins0 == pins1 and p0.keys() == p1.keys() and len(p1) == 1086
    assert all(p0[r].findtext(k) == p1[r].findtext(k) for r in p0 for k in ['value', 'footprint'])
    oldz, newz = [{str(first(z, 'uuid')[1]): z for z in children(t, 'zone')} for t in trees]
    changed = set(report['changed_existing_zone_fills'])
    declared = {z['uuid']: z for z in report['new_zones']}
    assert len(changed) == 3 and len(oldz) == 14 and len(newz) == 19
    assert newz.keys()-oldz.keys() == declared.keys()
    def settings(z):
        return [n for n in z if not (isinstance(n, list) and n and n[0] in ['polygon', 'filled_polygon'])]
    for u, z in oldz.items():
        assert settings(z) == settings(newz[u]), u
        if u not in changed:
            assert z == newz[u], u
        if u != report['expanded_source_zone']['uuid']:
            assert children(z, 'polygon') == children(newz[u], 'polygon'), u
        else:
            assert children(z, 'polygon') == [report['expanded_source_zone']['old_polygon']]
    zones = {z['uuid']: z for z in after['zones']}
    previous = {z['uuid']: z for z in before['zones']}
    assert all(zones[u] == z for u, z in previous.items() if u not in changed)
    assert len(fill['unchanged_existing_zone_canonical_polygon_match']) == 11
    assert all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    expanded = Polygon(report['expanded_source_zone']['new_outer_mm'])
    assert expanded.hausdorff_distance(shape(zones[report['expanded_source_zone']['uuid']]['authored_outline'])) < 2e-6
    mounts = [o for o in new.values() if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts) == 15
    zone_checks = []
    for u, r in declared.items():
        z = zones[u]; g = shape(z['polygons']); authored = Polygon(r['outer_mm'], r['holes_mm'])
        assert (z['net'], z['layer']) == (r['net'], r['layer'])
        assert authored.hausdorff_distance(shape(z['authored_outline'])) < 2e-6
        # The writer rounds every coordinate to 1nm. Compare that exact
        # serialized outline, then bound displacement from the unrounded plan.
        rounded = lambda ring: [[round(x, 6), round(y, 6)] for x, y in ring]
        serialized = Polygon(rounded(r['outer_mm']), [rounded(h) for h in r['holes_mm']])
        assert serialized.symmetric_difference(shape(z['authored_outline'])).area < 1e-9
        assert authored.symmetric_difference(serialized).area <= authored.length*1e-6
        assert len(z['authored_outline']) == 1 and len(z['authored_outline'][0]['holes']) == len(r['holes_mm'])
        assert shape(after['outline']).buffer(-.5).buffer(2e-6).covers(g)
        assert authored.buffer(2e-6).covers(g)
        assert first(newz[u], 'connect_pads')[1] == 'yes'
        assert float(first(first(newz[u], 'connect_pads'), 'clearance')[1]) == .2
        assert float(first(newz[u], 'min_thickness')[1]) == .25
        mountgaps = {o['ref']: g.distance(Point(o['position_mm']))-max(3.6, max(o['drill_mm'])/2+.5) for o in mounts}
        assert min(mountgaps.values()) >= .30-2e-6
        expected = dc if z['net'] == 'PWR_DC_IN' else ground
        pieces = []
        for p in z['polygons']:
            part = Polygon(p['outer'], p['holes'])
            direct = [o for o in new.values() if o['net'] == z['net'] and o['layers'].get(z['layer'])
                      and part.intersection(shape(o['layers'][z['layer']])).area > 1e-9]
            assert direct and all(o['uuid'] in expected for o in direct)
            pieces.append(dict(area_mm2=part.area, bounds_mm=list(part.bounds),
                pads=sorted([o['ref'], o['pin']] for o in direct if o['kind'] == 'PAD'),
                vias=sorted(o['uuid'] for o in direct if o['kind'] == 'PCB_VIA')))
        gap = min(g.distance(shape(o['layers'][z['layer']])) for o in new.values()
                  if o['net'] != z['net'] and o['layers'].get(z['layer']))
        assert gap >= .1985, (u, gap)
        neck = g.intersection(LineString([(240, 30), (240, 40)])) if z['layer'] != 'F.Cu' else None
        zone_checks.append(dict(uuid=u, layer=z['layer'], net=z['net'], native_filled_pieces=pieces,
            authored_holes=len(r['holes_mm']), minimum_mount_reserve_gap_mm=min(mountgaps.values()),
            minimum_foreign_copper_gap_mm=gap,
            H_NEW2_cross_section_total_mm=neck.length if neck is not None else None,
            H_NEW2_cross_section_segments_mm=[q.length for q in neck.geoms] if neck is not None else []))
    # Both planes reach every source and inlet transition via directly.
    for r in zone_checks:
        if r['net'] == 'PWR_DC_IN' and r['layer'] != 'F.Cu':
            assert len(r['native_filled_pieces']) == 1
            contacted = set(r['native_filled_pieces'][0]['vias'])
            assert added <= contacted and len(contacted) == 17
    # Source lands and all five source vias share the expanded front copper.
    src = shape(zones[report['expanded_source_zone']['uuid']]['polygons'])
    sourcevias = [o for o in new.values() if o['kind'] == 'PCB_VIA' and o['net'] == 'PWR_DC_IN'
                  and src.intersection(shape(o['layers']['F.Cu'])).area > 1e-9]
    assert len(sourcevias) == 5
    assert all(src.intersection(shape(pad('P_Q101', p)['layers']['F.Cu'])).area > 1e-9 for p in ['1', '2', '3'])
    # Existing AUX copper is byte-for-byte unchanged, as are all its objects:
    # this preserves the previously audited single-land return joining topology.
    auxids = ['d0572a8e-b95d-5c59-9a7c-1d3514a507b4', '94ece1a2-cfec-59cf-ba79-c618ed566f57',
              'bc76c316-2c04-5ecb-85b7-3e5f80b26bf1', 'dfd01f0a-edcf-55b7-aecb-2d44a419b9b3']
    assert all(zones[u] == previous[u] for u in auxids)
    # Recheck full-width projections for all 33 current fast-OV sections.
    groundzones = []
    for z in zones.values():
        if z['net'] != 'PWR_AGND':
            continue
        g = shape(z['polygons'])
        if any(new[u]['layers'].get(z['layer']) and g.intersection(shape(new[u]['layers'][z['layer']])).area > 1e-9 for u in ground):
            groundzones.append(z)
    layers = after['copper_layers']
    routes = []
    for name in ['fast-ov-routing.json', 'fast-ov-return-routing.json']:
        p = OUT/name; sources.append(p)
        routes.extend(r for r in json.loads(p.read_text())['routes'] if all(u in new for u in r['segment_uuids']))
    assert len(routes) == 33
    coverage = []
    for r in routes:
        g = LineString(r['path_mm']).buffer(r['width_mm']/2)
        for o in new.values():
            if o['kind'] == 'PCB_VIA' and o['net'] == r['net'] and o['net'] != 'PWR_AGND':
                g = g.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
        i = layers.index(r['layer'])
        candidates = [layers[j] for j in [i-1, i+1] if 0 <= j < len(layers)]
        areas = {l: g.difference(unary_union([shape(z['polygons']) for z in groundzones if z['layer'] == l]).buffer(.0015)).area for l in candidates}
        assert min(areas.values()) < 1e-6, (r['label'], areas)
        coverage.append(dict(label=r['label'], layer=r['layer'], adjacent_reference_uncovered_mm2=areas))
    smd = [shape(ps) for o in new.values() if o['kind'] == 'PAD' and not any(o['drill_mm'])
           for l, ps in o['layers'].items() if l in ['F.Cu', 'B.Cu'] and ps]
    st = STRtree(smd)
    gaps = [Point(o['position_mm']).distance(smd[int(st.nearest(Point(o['position_mm'])))])-o['drill_mm']/2
            for o in new.values() if o['kind'] == 'PCB_VIA']
    assert len(gaps) == 250 and min(gaps) >= .15-2e-6
    for folder in [BASE, OUT]:
        native = json.loads((folder/'review.json').read_text())
        for n, h in native['artifact_sha256'].items():
            assert sha(folder/n) == h, n
        sources.extend(folder/n for n in ['power_protection.kicad_pcb', 'netlist.xml', 'review.json', 'drc.json', 'erc.json'])
    drc, erc = [json.loads((OUT/n).read_text()) for n in ['drc.json', 'erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['severity'] == 'warning' and v['type'] == 'ground_pin_not_ground' for v in warnings)
    # Verify filled/native delta is solely duplicate identical instance paths.
    filledtree = read_sexpr((FILLED/'power_protection.kicad_pcb').read_text())
    nativecopy = copy.deepcopy(trees[1]); removed = 0
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
    sources.extend([FILLED/'power_protection.kicad_pcb', REPO/'hardware/fabrication/verify_native_zone_unfracture.py',
                    REPO/'hardware/fabrication/route_nf_surface.py', REPO/'hardware/fabrication/audit_two_board_power_delta.py'])
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        native_zone_fidelity=fidelity, complete_footprints_unchanged=1101, pin_net_map_unchanged=True,
        all_prior_connection_groups_preserved=len(before['all_groups']), new_group_merges=merges,
        old_opens=2383, new_opens=2374, connections_closed=9, added_vias=16, total_vias=250,
        total_tracks=sum(o['kind'] == 'PCB_TRACK' for o in new.values()), new_zones=zone_checks,
        unchanged_existing_zones=11, expanded_source_contact_vias=len(sourcevias),
        all_via_minimum_drill_to_SMD_mm=min(gaps), fast_OV_reference_coverage=coverage,
        AUX_ground_group_and_local_copper_unchanged=True, G_NT1_isolated=True, input_TVS_still_unconnected=True,
        geometry_errors=0, parity_errors=0, ERC_errors=0, ERC_warnings=2,
        filled_native_physical_delta=False, duplicate_identical_instance_paths_removed=removed,
        current_sharing_and_capacity_verified=False, thermal_margin_verified=False,
        stack_accepted=False, full_system_return_qualified=False, fabrication_released=False)
    with (OUT/'inlet-corridor-review.json').open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps({k: result[k] for k in ['all_prior_connection_groups_preserved', 'connections_closed', 'total_tracks', 'total_vias', 'all_via_minimum_drill_to_SMD_mm', 'current_sharing_and_capacity_verified']}))


if __name__ == '__main__':
    run()
