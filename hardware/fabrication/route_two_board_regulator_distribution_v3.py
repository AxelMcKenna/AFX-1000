"""Add regulator supply distribution and adjacent ground bridges to TBP35."""
import json
import shutil
import uuid
from pathlib import Path

from shapely.geometry import Point, box
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape

BASE = STAGING/'two-board-power-inlet-fuse-native-01'
CAP = STAGING/'two-board-power-routing-inputs-2372-inlet-fuse-01/capture.json'
OUT = STAGING/'two-board-power-regulator-distribution-03'


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text())
    for name, digest in cap['source_sha256'].items():
        assert sha(REPO/name) == digest, name
    board = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    codes = {str(n[2]): int(n[1]) for n in children(board, 'net')}
    pad = lambda ref, pin: next(o for o in cap['objects'] if o.get('ref') == ref and o.get('pin') == pin)
    feed, ground = 'PWR_MODULE_FEED_IN', 'PWR_AGND'
    wanted = {feed: {pad(r, p)['group'] for r, p in [('P_U101', '17'), ('P_U20', '8'), ('P_U23', '8')]},
              ground: {pad(r, p)['group'] for r, p in [('P_C103', '2'), ('P_U23', '5')]}}
    assert len(wanted[feed]) == 3 and len(wanted[ground]) == 2
    # Continuous feed above the AUX cell; descend within the two local VIN
    # cells. Existing through vias transfer into the retained In3 input planes.
    supply = unary_union([box(180, 124, 218.8, 127.4), box(196, 119.8, 301, 124.2),
                          box(180, 124, 186.5, 137.8), box(169.3, 133.3, 186.5, 137.8),
                          box(289, 123, 301, 128.3)])
    regions = [('regulator-feed', feed, 'In2.Cu', supply),
               ('digital-return-bridge', ground, 'In1.Cu', box(186, 123.4, 190, 128)),
               ('analog-return-bridge', ground, 'In1.Cu', box(222, 118.8, 290, 125.4))]
    edge = shape(cap['outline']).buffer(-.51, join_style=2)
    mounts = [o for o in cap['objects'] if o.get('npth')]
    newzones = []
    for label, net, layer, region in regions:
        region = region.intersection(edge)
        for o in mounts:
            region = region.difference(Point(o['position_mm']).buffer(max(o['drill_mm'])/2+.51, quad_segs=64))
        exclusions = []
        # Same-net labels do not authorize joining every physical return group.
        for o in cap['objects']:
            if o['net'] == net and o.get('group') not in wanted[net] and o['layers'].get(layer):
                g = shape(o['layers'][layer]).buffer(.21)
                if region.intersects(g):
                    region = region.difference(g); exclusions.append(o['uuid'])
        for z in cap['zones']:
            if z['layer'] == layer and z['net'] != net:
                region = region.difference(shape(z['authored_outline']).buffer(.21, join_style=2))
        # Keep the intentional AUX reference field separate despite its AGND
        # net name. Neither new ground bridge may overlap that zone's reserve.
        if net == ground:
            aux = next(z for z in cap['zones'] if z['uuid'] == 'dfd01f0a-edcf-55b7-aecb-2d44a419b9b3')
            assert region.distance(shape(aux['authored_outline'])) >= .2999
        region = region.simplify(.00001, preserve_topology=True)
        assert region.is_valid and region.geom_type == 'Polygon', (label, region.geom_type)
        u = str(uuid.uuid5(uuid.NAMESPACE_URL, 'AFX:TBPDISTRIB03:'+sha(CAP)+':'+label))
        rings = [region.exterior, *region.interiors]
        polygons = [[a('polygon'), [a('pts'), *[[a('xy'), round(x, 6), round(y, 6)] for x, y in ring.coords[:-1]]]] for ring in rings]
        board.append([a('zone'), [a('net'), codes[net]], [a('net_name'), net], [a('layer'), layer], [a('uuid'), u],
                      [a('priority'), 1 if net == ground else 0], [a('hatch'), a('edge'), .5], [a('connect_pads'), a('yes'), [a('clearance'), .2]],
                      [a('min_thickness'), .25], [a('filled_areas_thickness'), a('no')],
                      [a('fill'), a('yes'), [a('thermal_gap'), .25], [a('thermal_bridge_width'), .5],
                       [a('island_removal_mode'), 0]], *polygons])
        newzones.append(dict(label=label, uuid=u, net=net, layer=layer,
                             priority=1 if net == ground else 0, outer_mm=list(region.exterior.coords)[:-1], holes_mm=[list(r.coords)[:-1] for r in region.interiors],
                             authored_area_mm2=region.area, excluded_same_net_objects=exclusions))
    changed = {'2d29f18e-f863-557a-bd84-b2d1a216144c', 'c10eec5d-cf1f-58da-8d6d-48ce5d70e70d', 'd41ab58e-16e9-5d76-8b14-dc335aff8371',
               '22afdb17-c537-5cf1-9c2b-7155f7ec4443'}
    for z in children(board, 'zone'):
        if str(first(z, 'uuid')[1]) in changed:
            z[:] = [n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
    OUT.mkdir()
    sources = []
    for p in BASE.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(BASE)
        if rel.parts[0] in ['libraries', 'symbols'] or (len(rel.parts) == 1 and
                (p.suffix == '.kicad_sch' or p.name in ['power_protection.kicad_pcb', 'power_protection.kicad_pro',
                 'power_protection.kicad_dru', 'fp-lib-table', 'sym-lib-table', 'expected-circuit.json', 'symbol-paths.json'])):
            target = OUT/rel; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target); sources.append(p)
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p = OUT/'power_protection.kicad_sch'; sch = read_sexpr(p.read_text())
    first(first(sch, 'title_block'), 'rev')[1] = 'TBP36'
    p.write_text(sexpr(sch)+'\n')
    paths = [Path(__file__), CAP, STAGING/'two-board-inlet-resistance-02/independent-review.json', *sources]
    report = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        new_zones=newzones, refilled_existing_zones=sorted(changed),
        intended_previous_groups={n: sorted(groups) for n, groups in wanted.items()},
        added_tracks=0, added_vias=0, moved_footprints=[], circuit_changes=[],
        native_validation_pending=True, current_thermal_and_complete_return_qualification=False,
        fabrication_released=False)
    (OUT/'regulator-distribution-routing.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(zones_added=len(newzones), expected_zone_count=24, old_zones_to_refill=len(changed))))


if __name__ == '__main__':
    run()
