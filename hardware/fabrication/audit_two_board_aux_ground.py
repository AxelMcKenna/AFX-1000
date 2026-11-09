"""Verify AUX return separation, native guard copper and thermal stitching."""
import json
import math
from pathlib import Path
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE = STAGING / 'two-board-power-aux-local-native-01'
OUT = STAGING / 'two-board-power-aux-ground-native-02'
BEFORE = STAGING / 'two-board-power-routing-inputs-2447-aux-local/capture.json'
AFTER = STAGING / 'two-board-power-routing-inputs-2447-aux-ground-02/capture.json'


def run():
    report_path = OUT / 'aux-ground-routing.json'
    report, before, after = [json.loads(p.read_text()) for p in [report_path, BEFORE, AFTER]]
    fidelity = verify_capture(after)
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
    assert len(before['zones']) == 4 and len(after['zones']) == 8
    changed=report['changed_U20_ground_zone_uuid']
    assert changed=='c10eec5d-cf1f-58da-8d6d-48ce5d70e70d'
    assert all(z in after['zones'] for z in before['zones'] if z['uuid']!=changed)
    groups = {u: set(g) for g in after['all_groups'].values() for u in g}
    for g in before['all_groups'].values():
        mapped = {aliases.get(u, u) for u in g}
        assert mapped <= groups[next(iter(mapped))]
    def pad(ref,pin):
        return next(o for o in new.values() if o.get('ref') == ref and o.get('pin') == pin)
    terminals = [('P_U102','4'),('P_U102','9'),('P_C106','2'),('P_C107','2'),
                 ('P_C113','2'),('P_C110','2'),('P_R109','2')]
    allowed = groups[pad('P_U102','9')['uuid']]
    assert all(pad(*p)['uuid'] in allowed for p in terminals)
    assert {(new[u].get('ref'),new[u].get('pin')) for u in allowed if new[u]['kind']=='PAD'} == set(terminals)
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
    assert added == new.keys() - oldkeys and len(report['routes']) == 4 and len(report['vias']) == 4 and len(added) == 8
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
    assert len(gaps) == 190 and sum(o['kind'] == 'PCB_TRACK' for o in new.values()) == 2293
    drc, erc = [json.loads((OUT / n).read_text()) for n in ['drc.json', 'erc.json']]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks'] and not erc['ignored_checks']
    warnings = [v for s in erc['sheets'] for v in s.get('violations', [])]
    assert len(warnings) == 2 and all(v['type'] == 'ground_pin_not_ground' and v['severity'] == 'warning' for v in warnings)
    assert before['native_uncapped_opens'] == after['native_uncapped_opens'] == 2447
    filled = STAGING/'two-board-power-aux-ground-filled-02'
    fill_path = filled/'local-plane-fill.json'
    fill = json.loads(fill_path.read_text())
    for name,h in fill['source_sha256'].items():assert sha(REPO/name)==h,name
    for name,h in fill['artifact_sha256'].items():assert sha(filled/name)==h,name
    assert len(fill['unchanged_existing_zone_canonical_polygon_match'])==3
    assert all(fill['unchanged_existing_zone_canonical_polygon_match'].values())
    filled_tree=read_sexpr((filled/'power_protection.kicad_pcb').read_text())
    actual_zones={str(first(z,'uuid')[1]):z for z in children(trees[1],'zone')}
    assert {str(first(z,'uuid')[1]):z for z in children(filled_tree,'zone')}==actual_zones
    old_zones={str(first(z,'uuid')[1]):z for z in children(trees[0],'zone')}
    assert all(actual_zones[u]==z for u,z in old_zones.items() if u!=changed)
    declared={r['uuid']:r for r in report['zones']}
    assert set(declared)==set(actual_zones)-set(old_zones)
    expected_pads={
        'AUX-input-return':{('P_U102','4'),('P_U102','9'),('P_C113','2'),('P_C110','2'),('P_R109','2')},
        'AUX-output-return':{('P_U102','4'),('P_C106','2'),('P_C107','2')},
        'AUX-feedback-guard':set(), 'AUX-thermal-reference':set()}
    planes={};zone_records=[]
    outline=shape(after['outline']).buffer(-.5)
    for z in after['zones']:
        if z['uuid'] not in declared:continue
        r=declared[z['uuid']];label=r['label'];node=actual_zones[z['uuid']]
        assert not z['keepout'] and z['net']==r['net']=='PWR_AGND'
        assert z['layer']==r['layer']==first(node,'layer')[1]
        assert [list(map(float,p[1:3])) for p in children(first(first(node,'polygon'),'pts'),'xy')]==r['outline_mm']
        assert first(node,'connect_pads')[1]=='yes'
        assert float(first(first(node,'connect_pads'),'clearance')[1])==.2
        assert float(first(node,'min_thickness')[1])==.25
        g=shape(z['polygons']);boundary=shape(z['authored_outline'])
        assert g.is_valid and g.geom_type=='Polygon' and len(z['polygons'])==1,label
        assert boundary.buffer(2e-6).covers(g) and outline.covers(boundary)
        assert math.isclose(g.area,z['native_area_after_unfracture_mm2'],rel_tol=1e-8,abs_tol=1e-6)
        assert all(g.distance(Point(m['position_mm']))>=max(3.6,max(m['drill_mm'])/2+.5)+.3-2e-6 for m in mounts)
        copper=[o for o in new.values() if o['layers'].get(z['layer'])]
        gap=min(g.distance(shape(o['layers'][z['layer']])) for o in copper if o['net']!='PWR_AGND')
        assert gap>=.1985,(label,gap)
        contacts=[o for o in copper if o['net']=='PWR_AGND' and g.distance(shape(o['layers'][z['layer']]))<.0015]
        contacted_pads={(o.get('ref'),o.get('pin')) for o in contacts if o['kind']=='PAD'}
        assert contacted_pads==expected_pads[label],(label,contacted_pads)
        contacted_vias={o['uuid'] for o in contacts if o['kind']=='PCB_VIA'}
        expected_vias=set() if label=='AUX-output-return' else {v['uuid'] for v in report['vias']}
        assert contacted_vias==expected_vias,(label,contacted_vias)
        assert all(o['uuid'] in allowed for o in contacts)
        planes[label]=g
        zone_records.append(dict(label=label,layer=z['layer'],area_mm2=g.area,
            holes=sum(len(p['holes']) for p in z['polygons']),single_contiguous_native_polygon=True,
            directly_contacted_pads=sorted(contacted_pads),directly_contacted_vias=sorted(contacted_vias),
            minimum_captured_foreign_copper_gap_mm=gap))
    assert planes['AUX-input-return'].distance(planes['AUX-output-return'])>=.399
    # Multilayer copper cut check. Remove only the native GND-pin land (with
    # 2um numerical margin) from F.Cu. No output return may remain connected
    # to the input/EP/feedback ground through any other local copper or via.
    cut=shape(pad('P_U102','4')['layers']['F.Cu']).buffer(.002)
    nodes=[]
    for layer in after['copper_layers']:
        polys=[shape(new[u]['layers'][layer]) for u in allowed if new[u]['layers'].get(layer)]
        polys += [shape(z['polygons']) for z in after['zones'] if z['uuid'] in declared and z['layer']==layer]
        if not polys:continue
        merged=unary_union([g.buffer(.000002) for g in polys])
        if layer=='F.Cu':merged=merged.difference(cut)
        pieces=[merged] if merged.geom_type=='Polygon' else list(merged.geoms)
        nodes.extend((layer,p) for p in pieces if p.area>1e-10)
    parent=list(range(len(nodes)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for u in allowed:
        o=new[u]
        if o['kind']!='PCB_VIA':continue
        hits=[i for i,(l,g) in enumerate(nodes) if o['layers'].get(l) and g.intersection(shape(o['layers'][l])).area>1e-8]
        assert len(hits)==len(after['copper_layers'])
        for i in hits[1:]:parent[root(i)]=root(hits[0])
    def node_for(ref,pin):
        o=pad(ref,pin)
        hits=[i for i,(l,g) in enumerate(nodes) if o['layers'].get(l) and g.intersection(shape(o['layers'][l])).area>1e-8]
        assert len(hits)==1,(ref,pin,hits)
        return root(hits[0])
    input_root=node_for('P_U102','9');output_root=node_for('P_C106','2')
    assert input_root!=output_root
    assert all(node_for(r,p)==input_root for r,p in [('P_C113','2'),('P_C110','2'),('P_R109','2')])
    assert node_for('P_C107','2')==output_root
    # The full width of every local FB trace projects onto the added In1
    # reference copper, excluding the two FB via antipads themselves.
    fb=pad('P_U102','2')['net']
    fbtracks=[o for o in new.values() if o['kind']=='PCB_TRACK' and o['net']==fb]
    assert len(fbtracks)==5
    projection=unary_union([LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2) for o in fbtracks])
    fbvias=[o for o in new.values() if o['kind']=='PCB_VIA' and o['net']==fb]
    assert len(fbvias)==2
    for o in fbvias:projection=projection.difference(Point(o['position_mm']).buffer(.515))
    uncovered=projection.difference(planes['AUX-thermal-reference'].buffer(.0015)).area
    assert uncovered<1e-6,uncovered
    # The small U20 recess must remove copper only in the declared empty
    # rectangle, preserving every old direct ground-via contact and the sense
    # reference projection. The native changed-zone settings stay unchanged.
    def settings(z):
        return [n for n in z if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
    assert settings(old_zones[changed])==settings(actual_zones[changed])
    for z,key in [(old_zones[changed],'old_U20_ground_outline_mm'),(actual_zones[changed],'new_U20_ground_outline_mm')]:
        assert [list(map(float,p[1:3])) for p in children(first(first(z,'polygon'),'pts'),'xy')]==report[key]
    oldplane=shape(next(z for z in before['zones'] if z['uuid']==changed)['polygons'])
    newplane=shape(next(z for z in after['zones'] if z['uuid']==changed)['polygons'])
    assert newplane.is_valid and newplane.geom_type=='Polygon'
    difference=oldplane.difference(newplane)
    declared_recess=box(186.4,134.3,187,136.9)
    assert abs(declared_recess.area-1.56)<1e-8 and newplane.difference(oldplane).area<1e-8
    assert declared_recess.difference(difference.buffer(2e-6)).area<1e-8
    # Native .25mm minimum-thickness fill rounds the two new outer corners
    # within half that width. Verify their exact permitted envelopes as well
    # as the main rectangular cut, rather than assuming a square-corner fill.
    corner_envelopes=unary_union([box(186.875,134.175,187,134.3),box(186.875,136.9,187,137.025)])
    assert difference.difference(declared_recess.union(corner_envelopes).buffer(2e-6)).area<1e-8
    assert 1.56<=difference.area<=1.56+2*.125**2
    assert newplane.distance(planes['AUX-thermal-reference'])>=.299
    def contacts(objects,g):
        return {u for u,o in objects.items() if o['kind']=='PCB_VIA' and o['net']=='PWR_AGND'
                and g.buffer(.0015).covers(shape(o['layers']['In1.Cu']))}
    oldcontacts=contacts(old,oldplane);newcontacts=contacts(new,newplane)
    assert oldcontacts==newcontacts and oldcontacts
    control_path=BASE/'u20-control-routing.json';control=json.loads(control_path.read_text())
    sense=next(r for r in control['routes'] if r['label']=='output-sense-In2')
    sense_projection=LineString(sense['path_mm']).buffer(sense['width_mm']/2)
    for v in control['vias']:
        if v['net']=='PWR_5V_DIG_SRC':sense_projection=sense_projection.difference(Point(v['position_mm']).buffer(.515))
    sense_uncovered=sense_projection.difference(newplane.buffer(.0015)).area
    assert sense_uncovered<1e-6
    paths=[Path(__file__),report_path,BEFORE,AFTER,fill_path,control_path,
           REPO/'hardware/fabrication/verify_native_zone_unfracture.py',
           REPO/'tests/tooling/test_native_zone_unfracture.py',
           REPO/'hardware/fabrication/audit_two_board_power_delta.py',REPO/'hardware/fabrication/route_nf_surface.py']
    for folder in [BASE,OUT]:paths.extend(folder/n for n in ['power_protection.kicad_pcb','netlist.xml','review.json','drc.json','erc.json'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        components=1085,footprints=1100,unchanged_complete_pin_net_map=True,
        all_component_poses_values_packages_unchanged=True,all_old_copper_objects_unchanged=True,
        three_previous_authored_zones_and_native_fills_unchanged=True,
        U20_authored_ground_recess_area_mm2=declared_recess.area,
        U20_native_ground_removed_area_mm2=difference.area,
        U20_ground_area_before_mm2=oldplane.area,U20_ground_area_after_mm2=newplane.area,
        all_U20_direct_ground_via_contacts_preserved=len(oldcontacts),
        U20_sense_projection_uncovered_area_mm2=sense_uncovered,
        all_previous_native_connection_groups_preserved=len(before['all_groups']),
        local_route_sections=4,added_segments=4,added_vias=4,new_zones=4,
        old_opens=2447,new_opens=2447,connections_closed=0,
        local_plane_checks=zone_records,zone_unfracture_geometric_fidelity=fidelity,
        input_output_returns_join_only_through_GND_pin_land=True,
        multilayer_pin_land_cut_disconnected_input_and_output=True,
        no_other_circuit_ground_pad_joined=True,
        thermal_vias_outside_SMD_lands=True,
        FB_trace_projection_covered_except_own_via_antipads=True,FB_projection_uncovered_area_mm2=uncovered,
        minimum_all_via_drill_to_SMD_mm=min(gaps),vias_screened=190,
        geometry_findings=0,parity_findings=0,erc_errors=0,erc_warnings=2,
        actual_thermal_resistance_and_load_margin_qualified=False,
        AUX_input_output_distribution_and_PG_routing_complete=False,
        full_installed_fit_verified=False,electrical_and_manufacturing_qualified=False,fabrication_released=False)
    with (OUT/'aux-ground-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':run()
