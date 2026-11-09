"""Verify U23 quiet-return plane entry without losing any prior connectivity."""
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString, box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape

BASE = STAGING / 'two-board-power-u20-input-native-01'
OUT = STAGING / 'two-board-power-u23-quiet-native-01'
BEFORE = STAGING / 'two-board-power-routing-inputs-2462-u20-input/capture.json'
AFTER = STAGING / 'two-board-power-routing-inputs-2462-u23-quiet/capture.json'


def run():
    report_path = OUT / 'u23-quiet-routing.json'
    report, before, after = [json.loads(p.read_text()) for p in [report_path, BEFORE, AFTER]]
    assert not report['moves']
    for d in [report, before, after]:
        for name, h in d['source_sha256'].items():
            assert sha(REPO / name) == h, name
    for folder in [BASE, OUT]:
        native = json.loads((folder / 'review.json').read_text())
        for name, h in native['artifact_sha256'].items():
            assert sha(folder / name) == h, name
    trees = [read_sexpr((p / 'power_protection.kicad_pcb').read_text()) for p in [BASE, OUT]]
    fps = [{prop(f, 'Reference')[2]: f for f in children(t, 'footprint')} for t in trees]
    assert fps[0].keys() == fps[1].keys() and len(fps[1]) == 1100
    assert all(geometry(f) == geometry(fps[1][ref]) for ref, f in fps[0].items())
    def shell(t):
        return [n for n in t if not (isinstance(n, list) and n and n[0] in ['footprint', 'segment', 'via', 'arc', 'net', 'zone'])]
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
    aliases = {}
    for u in old.keys() - new.keys():
        assert old[u]['kind'] == 'PAD'
        hits = [v for v in new.keys() - old.keys() if physical(old[u]) == physical(new[v])]
        assert len(hits) == 1
        aliases[u] = hits[0]
    assert len(aliases) == len(set(aliases.values()))
    oldkeys = {aliases.get(u, u) for u in old}
    for uid, o in old.items():
        assert physical(o) == physical(new[aliases.get(uid, uid)]), uid
    target=report['changed_zone_uuid']
    assert len(before['zones'])==len(after['zones'])==4
    assert all(z in after['zones'] for z in before['zones'] if z['uuid']!=target)
    prior_zones={str(first(z,'uuid')[1]):z for z in children(trees[0],'zone')}
    current_zones={str(first(z,'uuid')[1]):z for z in children(trees[1],'zone')}
    assert prior_zones.keys()==current_zones.keys()
    assert all(current_zones[u]==z for u,z in prior_zones.items() if u!=target)
    def zone_settings(z):
        return [n for n in z if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
    assert zone_settings(prior_zones[target])==zone_settings(current_zones[target])
    groups = {u: set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped = {aliases.get(u, u) for u in g}
        assert mapped <= groups[next(iter(mapped))]
    def pads(ref, pin):
        return [o for o in new.values() if o.get('ref') == ref and o.get('pin') == pin]
    intended = {
        'U23-ground': [('P_U23','5'),('P_U23','9'),('P_U23','11'),('P_C220','2'),
                       ('P_R221','2'),('P_R222','2'),('P_R223','2'),('P_R225','2')],
    }
    verified_groups = {}
    for name, terminals in intended.items():
        g = groups[pads(*terminals[0])[0]['uuid']]
        assert all(o['uuid'] in g for ref,pin in terminals for o in pads(ref,pin)), name
        verified_groups[name] = g
    assert len({tuple(sorted(g)) for g in verified_groups.values()}) == len(intended)
    allowed = set().union(*verified_groups.values())
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
            assert u in allowed
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
    assert added == new.keys() - oldkeys and len(report['routes']) == 1 and len(report['vias']) == 1 and len(added) == 2
    for u in added:
        for ps in new[u]['layers'].values():
            if ps:
                assert all(shape(ps).distance(shape(z['authored_outline'])) > 2 for z in after['zones'] if z['uuid']!=target)
    smd = [shape(ps) for o in new.values() if o['kind'] == 'PAD' and not any(o['drill_mm'])
           for layer, ps in o['layers'].items() if layer in ['F.Cu', 'B.Cu'] and ps]
    tree = STRtree(smd)
    gaps = []
    for o in new.values():
        if o['kind'] == 'PCB_VIA':
            p = Point(o['position_mm'])
            gap = p.distance(smd[int(tree.nearest(p))]) - o['drill_mm'] / 2
            assert gap >= .15 - 2e-6
            gaps.append(gap)
    assert len(gaps) == 181 and sum(o['kind'] == 'PCB_TRACK' for o in new.values()) == 2257
    drc, erc = [json.loads((OUT / n).read_text()) for n in ['drc.json', 'erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['type'] == 'ground_pin_not_ground' and v['severity'] == 'warning' for v in warnings)
    assert before['native_uncapped_opens'] == after['native_uncapped_opens'] == 2462
    # Native fill provenance, including exact preservation of the other three planes.
    filled=STAGING/'two-board-power-u23-quiet-filled-01'
    fill_path=filled/'local-plane-fill.json';fill=json.loads(fill_path.read_text())
    for n,h in fill['source_sha256'].items():assert sha(REPO/n)==h,n
    for n,h in fill['artifact_sha256'].items():assert sha(filled/n)==h,n
    assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==3
    assert all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    filled_tree=read_sexpr((filled/'power_protection.kicad_pcb').read_text())
    assert {str(first(z,'uuid')[1]):z for z in children(filled_tree,'zone')}==current_zones
    old_zone=next(z for z in before['zones'] if z['uuid']==target)
    z=next(z for z in after['zones'] if z['uuid']==target)
    assert z['net']=='PWR_AGND' and z['layer']=='In1.Cu' and not z['keepout']
    plane=shape(z['polygons']);old_plane=shape(old_zone['polygons'])
    assert plane.is_valid and plane.geom_type=='Polygon' and len(z['polygons'])==1
    ring=[list(map(float,p[1:3])) for p in children(first(first(current_zones[target],'polygon'),'pts'),'xy')]
    assert ring==report['new_outline_mm']
    assert shape(old_zone['authored_outline']).covers(shape(z['authored_outline']))
    assert shape(z['authored_outline']).buffer(2e-6).covers(plane)
    assert math.isclose(plane.area,z['native_area_after_unfracture_mm2'],rel_tol=1e-8,abs_tol=1e-6)
    assert all(plane.distance(Point(m['position_mm'])) >= max(3.6,max(m['drill_mm'])/2+.5)+.3-2e-6 for m in mounts)
    foreign_gap=min(plane.distance(shape(o['layers']['In1.Cu'])) for o in new.values()
                    if o['net']!='PWR_AGND' and o['layers'].get('In1.Cu'))
    assert foreign_gap>=.1985
    def contacts(objects,g):
        return {u for u,o in objects.items() if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND'
                and g.buffer(.0015).covers(shape(o['layers']['In1.Cu']))}
    old_contacts=contacts(old,old_plane);new_contacts=contacts(new,plane)
    removed=next(o for o in old.values() if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND' and o['position_mm']==[292.8,129.8])
    assert old_contacts-new_contacts=={removed['uuid']}
    assert new_contacts-old_contacts=={report['vias'][0]['uuid']}
    assert plane.distance(shape(new[removed['uuid']]['layers']['In1.Cu']))>=.2
    assert removed['uuid'] in verified_groups['U23-ground']
    control_path=BASE/'buck-control-routing.json';control=json.loads(control_path.read_text())
    quiet=next(r for r in control['routes'] if r['label']=='configuration-return-In1')
    remote=LineString(quiet['path_mm']).buffer(.125).intersection(box(0,0,298.3,500))
    assert plane.distance(remote)>=.2
    original_quiet=next(o for o in new.values() if o['kind']=='PCB_VIA' and o['position_mm']==[299.25,132.2] and o['net']=='PWR_AGND')
    assert original_quiet['uuid'] in new_contacts
    sense=next(r for r in control['routes'] if r['label']=='output-sense-In2')
    corridor=LineString(sense['path_mm']).buffer(.1)
    for v in control['vias']:
        if v['net']=='/P_power_supply/P03_PRE6V':corridor=corridor.difference(Point(v['position_mm']).buffer(.515))
    uncovered=corridor.difference(plane.buffer(.0015)).area
    assert uncovered<1e-6,uncovered
    paths = [Path(__file__), report_path, BEFORE, AFTER, fill_path, control_path,
             REPO / 'hardware/fabrication/audit_two_board_power_delta.py',
             REPO / 'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE, OUT]:
        paths.extend(folder / n for n in ['power_protection.kicad_pcb', 'netlist.xml', 'review.json', 'drc.json', 'erc.json'])
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        components=1085, footprints=1100, unchanged_complete_pin_net_map=True,
        all_component_poses_values_and_packages_unchanged=True,
        all_old_copper_objects_unchanged=True,
        other_three_authored_zones_and_native_fills_unchanged=True,
        all_previous_native_connection_groups_preserved=len(before['all_groups']),
        local_route_sections=1, added_segments=1, added_vias=1,
        old_opens=2462, new_opens=2462, connections_closed=0,
        old_U23_ground_plane_area_mm2=old_plane.area,
        new_U23_ground_plane_area_mm2=plane.area,
        single_contiguous_U23_ground_polygon=True,
        changed_direct_plane_contact_removed=removed['uuid'],
        remote_MODE_return_still_connected=True,
        configuration_return_enters_force_plane_only_near_BP5=True,
        old_direct_ground_via_contacts=len(old_contacts),new_direct_ground_via_contacts=len(new_contacts),
        minimum_captured_foreign_copper_gap_mm=foreign_gap,
        sense_trace_projection_covered_except_own_via_antipads=True,
        sense_projection_uncovered_area_mm2=uncovered,
        minimum_all_via_drill_to_SMD_mm=min(gaps), vias_screened=181,
        geometry_findings=0, parity_findings=0, erc_errors=0, erc_warnings=2,
        whole_field_return_noise_and_impedance_qualified=False,
        electrical_thermal_and_manufacturing_qualified=False,full_installed_fit_verified=False,
        fabrication_released=False)
    with (OUT / 'u23-quiet-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    run()
