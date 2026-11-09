"""Place the IN_SYS bypass and PGTH divider locally; preserve the PG branch."""
import copy
import json
import shutil
import uuid
from pathlib import Path
from shapely.geometry import Point, LineString, box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position, angle, transform_object, mechanical_check
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE = STAGING/'two-board-power-input-source-native-03'
CAP = STAGING/'two-board-power-routing-inputs-2427-input-source/capture.json'
PLACEMENT = STAGING/'two-board-placement-05/capture.json'
OUT = STAGING/'two-board-power-input-bypass-03'
MOVES = {'P_C101': ([196.1, 121.9], -90), 'P_R111': ([196, 118.3], -90),
         'P_R110': ([191.3, 123.5], 0), 'P_R106': ([196.1, 126.5], 180)}
RETIRED = {'911a166d-d432-504e-85da-61a256200c2b', '08398e68-ded5-5bda-86dc-0e133eef5db8',
           '17a3fc0d-93e3-5b3c-b787-47827a436954', '59ec8ecc-3f4c-54fc-8da8-984768bd7179', 'c3d67fb2-a626-5e38-9cd7-bf1030277e3f', '8e1ac0bc-1787-5573-806b-5d5f35d4a730'}


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text())
    for p, h in cap['source_sha256'].items(): assert sha(REPO/p) == h, p
    board = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    old = {prop(f, 'Reference')[2]: f for f in children(board, 'footprint')}
    fps = copy.deepcopy(old)
    retired = [o for o in cap['objects'] if o['uuid'] in RETIRED]
    assert len(retired) == 6 and all(o['net'] == '/P_power_supply/POWER_READY' for o in retired)
    assert sum(o['kind'] == 'PCB_TRACK' for o in retired) == 5 and sum(o['kind'] == 'PCB_VIA' for o in retired) == 1
    for o in cap['objects']:
        if o.get('ref') in MOVES and o.get('pin') and (o['ref'], o['pin']) != ('P_R110', '2'):
            assert cap['all_groups'][o['group']] == [o['uuid']]
    for r, (p, rot) in MOVES.items(): fps[r] = rotate_footprint(old[r], p, rot)
    # Flip C101 with the identical native back-side C102 package, preserving
    # the original circuit identity, 2.2u/100V value, and every pad assignment.
    assert old['P_C101'][1] == old['P_C102'][1]
    f = rotate_footprint(old['P_C102'], MOVES['P_C101'][0], 0)
    for k in ['Reference', 'Value', 'Datasheet']:
        if prop(old['P_C101'], k) is not None: prop(f, k)[2] = prop(old['P_C101'], k)[2]
    first(f, 'uuid')[:] = first(old['P_C101'], 'uuid')
    f[:] = [n for n in f if not (isinstance(n, list) and n and n[0] == 'path')]
    f.extend(copy.deepcopy(children(old['P_C101'], 'path')))
    original = {str(p[1]): p for p in children(old['P_C101'], 'pad')}
    for p in children(f, 'pad'):
        first(p, 'uuid')[:] = first(original[str(p[1])], 'uuid')
        first(p, 'net')[:] = first(original[str(p[1])], 'net')
    fps['P_C101'] = f
    placement = json.loads(PLACEMENT.read_text()); records = {r['id']: r for r in placement['parts']}
    for r, template in [('P_C204', 'P_C205'), ('P_C104', 'P_C102'), ('P_C101', 'P_C102')]:
        for k in ['side', 'angle', 'body_relative_xy', 'courtyard_relative_xy', 'additional_planar_reserves', 'tails_relative_xy']:
            records[r][k] = copy.deepcopy(records[template][k])
    assert not children(old['G_NT1'], 'model')
    placement['parts'].append(dict(id='G_NT1', height_mm=0.0, side='F', angle=0,
        body_relative_xy=[-1.2, -.8, 1.2, .8], additional_planar_reserves=[], tails_relative_xy=[]))
    mechanical_check(fps, set(MOVES), placement)
    objects = []
    for o in cap['objects']:
        if o['uuid'] in RETIRED: continue
        r = o.get('ref')
        if r == 'P_C101':
            t = next(q for q in cap['objects'] if q.get('ref') == 'P_C102' and q.get('pin') == o['pin'])
            n = transform_object(t, position(old['P_C102']), MOVES[r][0], 0)
            for k in ['ref', 'uuid', 'net', 'group']: n[k] = o[k]
        elif r in MOVES: n = transform_object(o, position(old[r]), *MOVES[r])
        else: n = o
        objects.append(n)
    geoms = [(o, l, routing.shape(ps)) for o in objects for l, ps in o['layers'].items() if ps]
    trees = {l: ([(o, g) for o, k, g in geoms if k == l], STRtree([g for o, k, g in geoms if k == l])) for l in cap['copper_layers']}
    holes = [(o, Point(o['position_mm']), max(o['drill_mm'])/2) for o in objects if o.get('kind') == 'PAD' and any(o['drill_mm'])]
    holes += [(o, Point(o['position_mm']), o['drill_mm']/2) for o in objects if o['kind'] == 'PCB_VIA']
    outline = routing.shape(cap['outline']).buffer(-.5)
    mounts = [(Point(o['position_mm']), max(3.6, max(o['drill_mm'])/2+.5)) for o in objects if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    for r in MOVES:
        g = box(*courtyard(fps[r], first(fps[r], 'layer')[1][0]+'.CrtYd'))
        assert outline.covers(g) and all(g.distance(p) >= radius+.3 for p, radius in mounts)
    for o, l, g in geoms:
        if o.get('ref') not in MOVES: continue
        assert outline.covers(g)
        rows, tree = trees[l]
        for i in tree.query(g.buffer(.211)):
            q, h = rows[int(i)]
            if q.get('ref') != o['ref'] and q['net'] != o['net']: assert g.distance(h) >= .21-1e-7, (o['ref'], o.get('pin'), q.get('ref'), q.get('pin'), q['uuid'], g.distance(h))
        assert all(g.distance(p)-r >= .15-2e-6 for q, p, r in holes), (o['ref'], 'drill')
        assert all(z['layer'] != l or g.distance(routing.shape(z['authored_outline'])) > .21 for z in cap['zones'])
    board[:] = [n for n in board if not (isinstance(n, list) and n and n[0] in ['segment', 'via'] and str(first(n, 'uuid')[1]) in RETIRED)]
    for i, f in enumerate(board):
        if isinstance(f, list) and f and f[0] == 'footprint' and prop(f, 'Reference')[2] in MOVES: board[i] = fps[prop(f, 'Reference')[2]]
    codes = {str(n[2]): int(n[1]) for n in children(board, 'net')}
    routes = []; vias = []; added = []; changed = set()
    def pad(r, p): return next(o for o in objects if o.get('ref') == r and o.get('pin') == p)
    def xy(r, p): return pad(r, p)['position_mm']
    def uid(label): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'AFX:TBPINPUTBYPASS03:'+sha(CAP)+':'+label))
    routing.SIGNAL_LAYERS = tuple(cap['copper_layers']); routing.WIDTH = .2
    screen = ViaScreen(dict(cap, objects=objects, zones=[]))
    def via(label, net, p):
        if not screen.via_legal(net, p):
            print('Nearby copper', [(o.get('ref'), o.get('pin'), l, o['net'], round(Point(p).distance(g), 4)) for o, l, g in geoms if Point(p).distance(g) < .52], flush=True)
            options = sorted((Point(p).distance(Point(x/10, y/10)), [x/10, y/10]) for x in range(round(p[0]*10)-10, round(p[0]*10)+11) for y in range(round(p[1]*10)-10, round(p[1]*10)+11) if screen.via_legal(net, [x/10, y/10]))
            print('Nearby legal vias', options[:8], flush=True)
        assert screen.via_legal(net, p), (label, 'via clearance', p)
        assert all(n == net or Point(p).distance(g) >= .3+w/2+.21-1e-7 for n, l, w, g in added), (label, 'added copper')
        for z in cap['zones']:
            if Point(p).distance(routing.shape(z['authored_outline'])) < .61: changed.add(z['uuid'])
        u = uid(label)
        board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), codes[net]], [a('uuid'), u]])
        vias.append(dict(uuid=u, label=label, net=net, position_mm=p, size_mm=.6, drill_mm=.3)); screen.vias.append((net, p))
        for l in cap['copper_layers']: added.append((net, l, .6, Point(p)))
    def route(label, net, layer, path, width, limit):
        line = LineString(path)
        assert line.length <= limit and outline.buffer(-width/2-.01).covers(line), label
        rows, tree = trees[layer]
        for i in tree.query(line.buffer(width/2+.211)):
            o, g = rows[int(i)]
            if o['net'] != net: assert line.distance(g) >= width/2+.21-1e-7, (label, o.get('ref'), o.get('pin'), o['uuid'], line.distance(g))
        for n, l, w, g in added:
            if n != net and l == layer: assert line.distance(g) >= width/2+w/2+.21-1e-7, (label, 'added', n, line.distance(g))
        assert all(line.distance(p) >= r+width/2+.01 for p, r in mounts), label
        for z in cap['zones']:
            if z['layer'] == layer and line.distance(routing.shape(z['authored_outline'])) < width/2+.21: changed.add(z['uuid'])
        ids = []
        for i, (p, q) in enumerate(zip(path, path[1:])):
            u = uid(label+str(i)); ids.append(u)
            board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), width], [a('layer'), layer], [a('net'), codes[net]], [a('uuid'), u]])
        routes.append(dict(label=label, net=net, layer=layer, path_mm=path, width_mm=width, length_mm=line.length, maximum_length_mm=limit, segment_uuids=ids))
        added.append((net, layer, width, line)); print(label, round(line.length, 4), flush=True)
    pg = '/P_power_supply/POWER_READY'; dc = 'PWR_DC_IN'; gnd = 'PWR_AGND'
    threshold = pad('P_R106', '1')['net']; output = 'PWR_MODULE_FEED_IN'
    via('PG-source', pg, [199.6, 122.2])
    via('PG-resistor', pg, [193.5, 124.9]); via('PG-distribution', pg, [206.6, 125.8])
    via('IN_SYS', dc, [193.5, 123.55]); via('bypass-ground', gnd, [198.7, 124.5])
    via('PGTH', threshold, [199.45, 123.35]); via('divider-ground', gnd, [196.6, 128.5])
    via('DC-sense-source', dc, [193.9, 114.3])
    route('PG-source-escape', pg, 'F.Cu', [[199.25, 122.25], [199.6, 122.2]], .2, .5)
    route('PG-inner-distribution', pg, 'In3.Cu', [[199.6, 122.2], [200.5, 122.5], [206.6, 125.8]], .2, 10)
    route('PG-inner-resistor', pg, 'In3.Cu', [[199.6, 122.2], [195.4, 122.5], [193.5, 124.9]], .2, 8)
    route('PG-resistor-escape', pg, 'B.Cu', [[193.5, 124.9], xy('P_R110', '2')], .2, 2)
    route('IN_SYS-pin', dc, 'F.Cu', [xy('P_U101', '5'), [193.5, 123.25], [193.5, 123.55]], .2, 1.5)
    route('IN_SYS-bypass', dc, 'B.Cu', [[193.5, 123.55], xy('P_C101', '1')], .35, 2)
    route('bypass-return', gnd, 'B.Cu', [xy('P_C101', '2'), [198.7, 124.5]], .4, 3.2)
    route('PGTH-pin', threshold, 'F.Cu', [xy('P_U101', '15'), [199.0, 122.75], [199.45, 123.35]], .2, 1.5)
    route('PGTH-receiver', threshold, 'B.Cu', [[199.45, 123.35], [199.5, 124.8], xy('P_R105', '2')], .2, 2.5)
    route('PGTH-divider', threshold, 'B.Cu', [xy('P_R105', '2'), [198.3, 126.25], [196.8, 126.25], xy('P_R106', '1')], .2, 4)
    route('PGTH-return', gnd, 'B.Cu', [xy('P_R106', '2'), [196.6, 128.5]], .25, 1.3)
    route('PGTH-output-sense', output, 'B.Cu', [xy('P_R105', '1'), [200.25, 127.4125], [200.25, 123.5], xy('P_C104', '1')], .25, 7)
    route('DC-sense-source', dc, 'F.Cu', [xy('P_Q101', '1'), [193.9, 114.3]], .35, 2)
    route('DC-sense-inner', dc, 'In3.Cu', [[193.9, 114.3], [194.8, 118], [194.8, 121.5], [193.5, 123.55]], .35, 10)
    # These are the only existing regions allowed to refill. No outlines,
    # priorities, rules, or native zone settings are altered.
    allowed = {'d0572a8e-b95d-5c59-9a7c-1d3514a507b4', 'a147ef12-37f5-562e-9340-6c74b3790186', 'd41ab58e-16e9-5d76-8b14-dc335aff8371', '85d2f33d-203c-5c6d-8918-7fecc35747b8', '6fbc9376-48e6-543a-acf8-9c2d3722952f'}
    allowed.add('94ece1a2-cfec-59cf-ba79-c618ed566f57')
    # Removing the former front-side C101 pad also changes the AUX output
    # plane clearance. Refill that region explicitly, even though none of
    # the newly added copper occupies its outline.
    for o in cap['objects']:
        if o.get('ref') not in MOVES and o['uuid'] not in RETIRED: continue
        for z in cap['zones']:
            ps = o['layers'].get(z['layer'])
            if ps and routing.shape(ps).distance(routing.shape(z['authored_outline'])) < .21: changed.add(z['uuid'])
    assert changed <= allowed, changed-allowed
    for z in children(board, 'zone'):
        if str(first(z, 'uuid')[1]) in changed: z[:] = [n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
    shutil.copytree(BASE, OUT, ignore=shutil.ignore_patterns('*.log', 'drc.*', 'erc.*', 'netlist.xml', 'review.json', 'circuit-audit.json', 'plots', '*-audit.json', '*-review.json', 'rejected-source-net-status.json', 'README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p = OUT/'power_protection.kicad_sch'; s = read_sexpr(p.read_text()); first(first(s, 'title_block'), 'rev')[1] = 'TBP29'; p.write_text(sexpr(s)+'\n')
    paths = [Path(__file__), CAP, PLACEMENT, BASE/'power_protection.kicad_pcb', BASE/'input-source-audit.json', STAGING/'assembly-layout-04/allocation.json',
        *[REPO/'hardware/fabrication'/p for p in ['repack_two_board_buck_input.py', 'route_two_board_buck_cell.py', 'route_two_board_power_layer_detours.py', 'route_nf_surface.py']], REPO/'hardware/electronics/output_stage/check_placement.py']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        moves=[dict(ref=r, old_xy=position(old[r]), new_xy=p, rotation_added_degrees=rot, final_angle=angle(fps[r]), old_side=first(old[r], 'layer')[1], new_side=first(fps[r], 'layer')[1]) for r, (p, rot) in MOVES.items()],
        flipped_part='P_C101', flipped_template='P_C102', routes=routes, vias=vias,
        retired_tracks=[o for o in retired if o['kind'] == 'PCB_TRACK'], retired_vias=[o for o in retired if o['kind'] == 'PCB_VIA'], changed_existing_zone_fills=sorted(changed), all_zone_outlines_settings_unchanged=True,
        all_values_packages_pin_nets_unchanged=True, placement_and_pad_drill_screen=True,
        added_tracks=sum(len(r['segment_uuids']) for r in routes), added_vias=len(vias),
        source_sense_route_is_not_full_load_distribution=True,
        manufacturer_source='https://www.ti.com/lit/ds/symlink/tps2663.pdf', manufacturer_section='9.6.1, SLVSE94G',
        native_validation_pending=True, independent_audit_pending=True,
        exact_passive_MPN_and_derating_pending=True, UV_OV_and_clamp_pending=True,
        full_current_thermal_transient_qualified=False, fabrication_released=False)
    (OUT/'input-bypass-routing.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(tracks=result['added_tracks'], vias=len(vias), changed_zones=sorted(changed))))


if __name__ == '__main__': run()
