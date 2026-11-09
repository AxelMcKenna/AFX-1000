"""Place the input TVS beside Q101 and connect it to paired inlet planes."""
import copy
import json
import shutil
import uuid
from pathlib import Path
from shapely.geometry import Point, box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position, angle, transform_object, mechanical_check
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE = STAGING/'two-board-power-inlet-corridor-native-02'
CAP = STAGING/'two-board-power-routing-inputs-2374-inlet-corridor-02/capture.json'
PLACEMENT = STAGING/'two-board-placement-05/capture.json'
OUT = STAGING/'two-board-power-input-tvs-01'
TARGET = [186.0, 112.0]


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text())
    for p, h in cap['source_sha256'].items():
        assert sha(REPO/p) == h, p
    board = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    fps = {prop(f, 'Reference')[2]: f for f in children(board, 'footprint')}
    old = fps['P_D101']; new = rotate_footprint(old, TARGET, 90)
    assert first(old, 'layer')[1] == first(new, 'layer')[1] == 'B.Cu'
    fps['P_D101'] = new
    placement = json.loads(PLACEMENT.read_text()); records = {r['id']: r for r in placement['parts']}
    for r, template in [('P_C204', 'P_C205'), ('P_C104', 'P_C102'), ('P_C101', 'P_C102'),
                        *[(r, 'P_R102') for r in ['P_R101', 'P_R103', 'P_R104']]]:
        for k in ['side', 'angle', 'body_relative_xy', 'courtyard_relative_xy', 'additional_planar_reserves', 'tails_relative_xy']:
            records[r][k] = copy.deepcopy(records[template][k])
    rec = copy.deepcopy(records['P_C401']); rec['id'] = 'P_C114'; placement['parts'].append(rec)
    mechanical_check(fps, {'P_D101'}, placement)
    objects = [transform_object(o, position(old), TARGET, 90) if o.get('ref') == 'P_D101' else o for o in cap['objects']]
    edge = routing.shape(cap['outline']).buffer(-.5)
    mounts = [(Point(o['position_mm']), max(3.6, max(o['drill_mm'])/2+.5)) for o in objects
              if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    court = box(*courtyard(new, 'B.CrtYd'))
    assert edge.covers(court) and all(court.distance(p) >= r+.3 for p, r in mounts)
    rows = [(o, routing.shape(o['layers']['B.Cu'])) for o in objects if o['layers'].get('B.Cu')]
    tree = STRtree([g for o, g in rows]); holes = []
    for o in objects:
        d = o.get('drill_mm', 0); r = max(d)/2 if isinstance(d, list) else d/2
        if r:
            holes.append((Point(o['position_mm']), r))
    for o, g in rows:
        if o.get('ref') != 'P_D101':
            continue
        assert edge.covers(g)
        for i in tree.query(g.buffer(.211)):
            q, h = rows[int(i)]
            if q.get('ref') != 'P_D101' and q['net'] != o['net']:
                assert g.distance(h) >= .21-1e-7, (o['pin'], q.get('ref'), q.get('pin'))
        assert all(g.distance(p)-r >= .15-2e-6 for p, r in holes)
    for i, f in enumerate(board):
        if isinstance(f, list) and f and f[0] == 'footprint' and prop(f, 'Reference')[2] == 'P_D101':
            board[i] = new
    codes = {str(n[2]): int(n[1]) for n in children(board, 'net')}
    uid = lambda label: str(uuid.uuid5(uuid.NAMESPACE_URL, 'AFX:TBPTVS01:'+sha(CAP)+':'+label))
    routing.SIGNAL_LAYERS = tuple(cap['copper_layers']); routing.WIDTH = .2
    screen = ViaScreen(dict(cap, objects=objects, zones=[]))
    dc, gnd = 'PWR_DC_IN', 'PWR_AGND'
    sites = [(dc, [x, 109.5]) for x in [187, 187.7, 188.4, 189.1]]
    sites += [(dc, [x, 114.8]) for x in [187, 187.7]]
    sites += [(gnd, [x, y]) for x in [182.8, 183.5, 184.2] for y in [109.5, 114.8]]
    changed = set(); vias = []
    for i, (net, p) in enumerate(sites):
        assert screen.via_legal(net, p), (net, p)
        screen.vias.append((net, p)); u = uid('via'+str(i))
        board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3],
                      [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), codes[net]], [a('uuid'), u]])
        vias.append(dict(uuid=u, net=net, position_mm=p, size_mm=.6, drill_mm=.3))
        for z in cap['zones']:
            if Point(p).distance(routing.shape(z['authored_outline'])) < .61:
                changed.add(z['uuid'])
    zones = []
    for label, net, g in [('TVS-source', dc, box(186, 109.05, 189.9, 117.5)),
                          ('TVS-return', gnd, box(181.2, 109.05, 185.7, 117.5))]:
        assert edge.covers(g) and all(g.distance(p) >= r+.3 for p, r in mounts)
        assert all(z['layer'] != 'B.Cu' or g.distance(routing.shape(z['authored_outline'])) >= .21 for z in cap['zones'])
        u = uid(label); ring = list(g.exterior.coords)[:-1]
        board.append([a('zone'), [a('net'), codes[net]], [a('net_name'), net], [a('layer'), 'B.Cu'], [a('uuid'), u],
            [a('hatch'), a('edge'), .5], [a('connect_pads'), a('yes'), [a('clearance'), .2]],
            [a('min_thickness'), .25], [a('filled_areas_thickness'), a('no')],
            [a('fill'), a('yes'), [a('thermal_gap'), .25], [a('thermal_bridge_width'), .5], [a('island_removal_mode'), 0]],
            [a('polygon'), [a('pts'), *[[a('xy'), *p] for p in ring]]]])
        zones.append(dict(uuid=u, label=label, net=net, layer='B.Cu', outer_mm=ring, holes_mm=[]))
    for o in [o for c in [cap['objects'], objects] for o in c if o.get('ref') == 'P_D101']:
        for z in cap['zones']:
            ps = o['layers'].get(z['layer'])
            if ps and routing.shape(ps).distance(routing.shape(z['authored_outline'])) < .21:
                changed.add(z['uuid'])
    for z in children(board, 'zone'):
        if str(first(z, 'uuid')[1]) in changed:
            z[:] = [n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
    shutil.copytree(BASE, OUT, ignore=shutil.ignore_patterns('*.log', 'drc.*', 'erc.*', 'netlist.xml', 'review.json',
        'circuit-audit.json', 'plots', '*-audit.json', '*-review.json', 'rejected-source-net-status.json', 'README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p = OUT/'power_protection.kicad_sch'; sch = read_sexpr(p.read_text())
    first(first(sch, 'title_block'), 'rev')[1] = 'TBP34'; p.write_text(sexpr(sch)+'\n')
    sources = [Path(__file__), CAP, PLACEMENT, BASE/'power_protection.kicad_pcb', BASE/'inlet-corridor-review.json',
               STAGING/'assembly-layout-04/allocation.json', *[REPO/'hardware/fabrication'/n for n in [
                   'repack_two_board_buck_input.py', 'route_two_board_buck_cell.py', 'route_two_board_power_layer_detours.py',
                   'route_two_board_power_local_v2.py', 'route_nf_surface.py']],
               REPO/'hardware/electronics/output_stage/check_placement.py',
               *[REPO/'hardware/fabrication/parts/input-tvs-01'/n for n in ['README.md', 'smbj.pdf', 'tps2663.pdf']]]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        moves=[dict(ref='P_D101', old_xy=position(old), new_xy=TARGET, rotation_added_degrees=90,
                    final_angle=angle(new), side='B.Cu')], vias=vias, new_zones=zones,
        changed_existing_zone_fills=sorted(changed), added_tracks=0, added_vias=len(vias),
        retired_tracks=[], retired_vias=[], all_values_packages_pin_nets_unchanged=True,
        native_validation_pending=True, independent_audit_pending=True,
        current_thermal_surge_and_fuse_coordination_qualified=False, fabrication_released=False)
    (OUT/'input-tvs-routing.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(vias=len(vias), new_zones=len(zones), refilled_existing_zones=sorted(changed))))


if __name__ == '__main__':
    run()
