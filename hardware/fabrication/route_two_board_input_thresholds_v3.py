"""Place and connect the input UV/OV dividers and their clamp bias network."""
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

BASE = STAGING/'two-board-power-input-bypass-native-03'
CAP = STAGING/'two-board-power-routing-inputs-2420-input-bypass/capture.json'
PLACEMENT = STAGING/'two-board-placement-05/capture.json'
OUT = STAGING/'two-board-power-input-thresholds-03'
MOVES = {'P_R101': ([197.4, 126.5], 0), 'P_R102': ([195.2, 126.5], 180),
         'P_R103': ([190.2, 126.5], 0), 'P_R104': ([193, 126.5], 180),
         'P_R105': ([200.3, 126.5], 180), 'P_R106': ([202.5, 126.5], 180),
         'P_R115': ([204.7, 126.5], 0)}
FLIPS = {'P_R101': 0, 'P_R103': 0, 'P_R104': 180}
RETIRED_LABELS = {'PG-inner-resistor','PG-resistor-escape','PGTH-receiver',
                  'PGTH-divider','PGTH-return','PGTH-output-sense'}


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text())
    for p, h in cap['source_sha256'].items(): assert sha(REPO/p) == h, p
    board = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    old = {prop(f, 'Reference')[2]: f for f in children(board, 'footprint')}
    fps = copy.deepcopy(old)
    prior=json.loads((BASE/'input-bypass-routing.json').read_text())
    RETIRED={u for r in prior['routes'] if r['label'] in RETIRED_LABELS for u in r['segment_uuids']}
    RETIRED.update(['8d8e2145-7804-5c3b-a32b-de8c1cc2ef29','fa876ce9-8c42-58a4-93fe-0d9d3ba89a88',
                    '9432f8fe-9ffc-586c-bc04-d636e0568e90','fdb76936-70a6-5a03-bdca-4ea9ec2a483c'])
    retired = [o for o in cap['objects'] if o['uuid'] in RETIRED]
    assert len(retired)==16 and sum(o['kind']=='PCB_TRACK' for o in retired)==14 and sum(o['kind']=='PCB_VIA' for o in retired)==2
    assert {o['net'] for o in retired}=={'/P_power_supply/POWER_READY','/P_power_supply/INPUT_PGTH','PWR_MODULE_FEED_IN','PWR_AGND','PWR_POWER_RUN'}
    for o in cap['objects']:
        if o.get('ref') in MOVES and o.get('pin') and o['ref'] not in ['P_R105','P_R106']:
            assert cap['all_groups'][o['group']] == [o['uuid']]
    for r, (p, rot) in MOVES.items(): fps[r] = rotate_footprint(old[r], p, rot)
    # Native back-side R102 is the identical package for all three flips.
    for r,rot in FLIPS.items():
        assert old[r][1]==old['P_R102'][1]
        f=rotate_footprint(old['P_R102'],MOVES[r][0],rot)
        for k in ['Reference','Value','Datasheet']:
            if prop(old[r],k) is not None:prop(f,k)[2]=prop(old[r],k)[2]
        first(f,'uuid')[:]=first(old[r],'uuid')
        f[:]=[n for n in f if not(isinstance(n,list) and n and n[0]=='path')]
        f.extend(copy.deepcopy(children(old[r],'path')))
        original={str(p[1]):p for p in children(old[r],'pad')}
        for padnode in children(f,'pad'):
            first(padnode,'uuid')[:]=first(original[str(padnode[1])],'uuid')
            first(padnode,'net')[:]=first(original[str(padnode[1])],'net')
        fps[r]=f
    placement = json.loads(PLACEMENT.read_text()); records = {r['id']: r for r in placement['parts']}
    for r, template in [('P_C204', 'P_C205'), ('P_C104', 'P_C102'), ('P_C101', 'P_C102'), *[(r,'P_R102') for r in FLIPS]]:
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
        if r in FLIPS:
            t = next(q for q in cap['objects'] if q.get('ref') == 'P_R102' and q.get('pin') == o['pin'])
            n = transform_object(t, position(old['P_R102']), MOVES[r][0], FLIPS[r])
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
    def uid(label): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'AFX:TBPINPUTTHRESHOLDS03:'+sha(CAP)+':'+label))
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
    pg='/P_power_supply/POWER_READY';dc='PWR_DC_IN';gnd='PWR_AGND';aux='PWR_V2V5_AUX'
    threshold=pad('P_R106','1')['net'];output='PWR_MODULE_FEED_IN';run='PWR_POWER_RUN'
    uv=pad('P_R102','1')['net'];ov=pad('P_R104','1')['net']
    sites=[('PG-resistor',pg,[191.4,122.4]),('RUN-receiver',run,[199,125.3]),
        ('UV-pin',uv,[194,124.2]),('OV-pin',ov,[194.8,124.5]),('OV-divider',ov,[191.9,125.0]),
        ('DC-OV',dc,[188.5,127.7]),('DC-UV',dc,[197.3,129]),
        ('PGTH-divider',threshold,[201.4,128.2]),('PGTH-ground',gnd,[202.1,124.1]),
        ('OV-clamp',ov,[195.9,116.9]),('AUX-clamp',aux,[197.6,114.1]),
        ('clamp-ground',gnd,[195.8,119.5]),('AUX-source',aux,[190.8,137.3]),('AUX-pullup',aux,[190,122.3])]
    for label,net,p in sites:via(label,net,p)
    route('PG-resistor-inner',pg,'In5.Cu',[[199.6,122.2],[193.8,120.4],[191.4,120.4],[191.4,122.4]],.2,11)
    route('PG-resistor-back',pg,'B.Cu',[[191.4,122.4],xy('P_R110','2')],.2,1.5)
    route('RUN-inner-extension',run,'In4.Cu',[[197.5,125.5],[199,125.3]],.2,1.6)
    route('RUN-pin-escape',run,'F.Cu',[xy('P_U101','12'),[197.75,125.3],[199,125.3]],.2,2.2)
    route('UV-pin-escape',uv,'F.Cu',[xy('P_U101','6'),[194.35,123.9],[194,124.2]],.2,1)
    route('UV-receiver',uv,'B.Cu',[[194,124.2],[193.85,124.6],[194.4,125.8],xy('P_R102','1')],.2,3)
    route('UV-divider',uv,'B.Cu',[xy('P_R102','1'),xy('P_R101','2')],.2,2.5)
    route('OV-pin-escape',ov,'F.Cu',[xy('P_U101','7'),[194.8,124.5]],.2,.7)
    route('OV-inner',ov,'In2.Cu',[[194.8,124.5],[194.4,125.3],[191.9,125.0]],.2,3.5)
    route('OV-receiver',ov,'B.Cu',[[191.9,125.0],[191.9,125.5875]],.2,1)
    route('OV-divider',ov,'B.Cu',[xy('P_R103','2'),xy('P_R104','1')],.2,3)
    route('UV-ground',gnd,'B.Cu',[xy('P_R102','2'),[194,126.7]],.25,1.5)
    route('OV-ground',gnd,'B.Cu',[xy('P_R104','2'),[194,126.7]],.25,1.4)
    route('DC-OV-escape',dc,'B.Cu',[[188.5,127.7],xy('P_R103','1')],.3,2.3)
    route('DC-UV-escape',dc,'B.Cu',[[197.3,129],xy('P_R101','1')],.3,1.8)
    route('DC-OV-inner',dc,'In5.Cu',[[193.5,123.55],[190.8,123.8],[188.5,127.7]],.3,7.5)
    route('DC-UV-inner',dc,'In5.Cu',[[193.5,123.55],[195.2,122.7],[197.9,123.9],[197.3,129]],.3,10.5)
    route('PGTH-inner',threshold,'In2.Cu',[[199.45,123.35],[201.4,128.2]],.2,5.5)
    route('PGTH-divider',threshold,'B.Cu',[xy('P_R105','2'),xy('P_R106','1')],.2,2.5)
    route('PGTH-divider-escape',threshold,'B.Cu',[[201.4,127.4125],[201.4,128.2]],.2,1)
    route('PGTH-output-sense',output,'B.Cu',[xy('P_C104','1'),xy('P_R105','1')],.25,3.5)
    route('PGTH-ground',gnd,'B.Cu',[xy('P_R106','2'),[202.1,124.1]],.25,2)
    route('OV-clamp-escape',ov,'F.Cu',[xy('P_D102','1'),[195.9,116.9]],.2,1.8)
    route('OV-clamp-inner',ov,'In2.Cu',[[195.9,116.9],[197,119],[197,121.7],[194.8,124.5]],.2,9)
    route('AUX-clamp-escape',aux,'F.Cu',[[197.6,114.1],xy('P_D102','3')],.3,1.5)
    route('AUX-clamp-capacitor',aux,'B.Cu',[[197.6,114.1],xy('P_C108','1')],.3,2.2)
    route('AUX-clamp-bleed',aux,'B.Cu',[xy('P_C108','1'),[195,116],xy('P_R111','1')],.25,4.5)
    route('clamp-ground-join',gnd,'B.Cu',[xy('P_C108','2'),xy('P_R111','2')],.3,3.3)
    route('clamp-ground-stitch',gnd,'B.Cu',[xy('P_R111','2'),[195.8,119.5]],.3,1.8)
    # The source via lands on the retained 0.4mm capacitor supply bus, not its FB sense spur.
    route('AUX-clamp-bias-feed',aux,'In3.Cu',[[190.8,137.3],[195.6,134],[195.6,121],[197,120],[197,117.5],[197.6,114.1]],.35,29)
    route('AUX-pullup-feed',aux,'In3.Cu',[[195.6,126],[190,126],[190,122.3]],.25,10)
    route('AUX-pullup-escape',aux,'B.Cu',[[190,122.3],xy('P_R110','1')],.25,1.5)
    # Extend the existing U101 reference across the shifted PGTH divider.
    ground_id='d41ab58e-16e9-5d76-8b14-dc335aff8371'
    ring=[[193.5,118.8],[223,118.8],[223,124.4],[205,124.4],[205,128.8],
          [200,128.8],[200,130.2],[195.2,130.2],[195.2,128],[189,128],[189,122.8],[193.5,122.8]]
    zone=next(z for z in children(board,'zone') if str(first(z,'uuid')[1])==ground_id)
    old_ring=[list(map(float,p[1:3])) for p in children(first(first(zone,'polygon'),'pts'),'xy')]
    first(first(zone,'polygon'),'pts')[:]=[a('pts'),*[[a('xy'),*p] for p in ring]]
    changed.add(ground_id)
    # These are the only existing regions allowed to refill. No outlines,
    # priorities, rules, or native zone settings are altered.
    allowed = {'d0572a8e-b95d-5c59-9a7c-1d3514a507b4', 'a147ef12-37f5-562e-9340-6c74b3790186', 'd41ab58e-16e9-5d76-8b14-dc335aff8371', '85d2f33d-203c-5c6d-8918-7fecc35747b8', '6fbc9376-48e6-543a-acf8-9c2d3722952f'}
    allowed.update(['94ece1a2-cfec-59cf-ba79-c618ed566f57','bc76c316-2c04-5ecb-85b7-3e5f80b26bf1','dfd01f0a-edcf-55b7-aecb-2d44a419b9b3'])
    # Departing pads and explicitly retired copper can also expose old fills.
    for o in cap['objects']:
        if o.get('ref') not in MOVES and o['uuid'] not in RETIRED: continue
        for z in cap['zones']:
            ps = o['layers'].get(z['layer'])
            if ps and routing.shape(ps).distance(routing.shape(z['authored_outline'])) < .21: changed.add(z['uuid'])
    # Native refill also reconstructs a tiny boundary at the retained VIN
    # plane's BGATE-adjacent entry. Declare and independently check that
    # refilled region instead of claiming its polygon remains byte-exact.
    vin_id='8cb9e48c-15ab-5fc9-84a1-9d7a07c28925'
    allowed.add(vin_id);changed.add(vin_id)
    assert changed <= allowed, changed-allowed
    for z in children(board, 'zone'):
        if str(first(z, 'uuid')[1]) in changed: z[:] = [n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')]
    # Adjacent reference for the B.Cu protection/divider network. This region
    # stays clear of the AUX regulator ground vias below y=128 at x<195.2.
    ref_ring=[[189,113],[200.5,113],[200.5,118.8],[223,118.8],[223,124.4],
              [205,124.4],[205,128.8],[200,128.8],[200,130.2],[195.2,130.2],[195.2,128],[189,128]]
    from shapely.geometry import Polygon
    ref_shape=Polygon(ref_ring);assert ref_shape.is_valid and outline.covers(ref_shape)
    assert all(ref_shape.distance(p)>=r+.3 for p,r in mounts)
    ref_uid=uid('input-protection-In6-ground')
    board.append([a('zone'),[a('net'),codes[gnd]],[a('net_name'),gnd],[a('layer'),'In6.Cu'],[a('uuid'),ref_uid],
        [a('hatch'),a('edge'),.5],[a('connect_pads'),a('yes'),[a('clearance'),.2]],
        [a('min_thickness'),.25],[a('filled_areas_thickness'),a('no')],
        [a('fill'),a('yes'),[a('thermal_gap'),.25],[a('thermal_bridge_width'),.5],[a('island_removal_mode'),0]],
        [a('polygon'),[a('pts'),*[[a('xy'),*p] for p in ref_ring]]]])
    shutil.copytree(BASE, OUT, ignore=shutil.ignore_patterns('*.log', 'drc.*', 'erc.*', 'netlist.xml', 'review.json', 'circuit-audit.json', 'plots', '*-audit.json', '*-review.json', 'rejected-source-net-status.json', 'README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p = OUT/'power_protection.kicad_sch'; s = read_sexpr(p.read_text()); first(first(s, 'title_block'), 'rev')[1] = 'TBP30'; p.write_text(sexpr(s)+'\n')
    paths = [Path(__file__), CAP, PLACEMENT, BASE/'power_protection.kicad_pcb', BASE/'input-bypass-audit.json', BASE/'input-bypass-routing.json', STAGING/'assembly-layout-04/allocation.json',
        *[REPO/'hardware/fabrication'/p for p in ['repack_two_board_buck_input.py', 'route_two_board_buck_cell.py', 'route_two_board_power_layer_detours.py', 'route_nf_surface.py']], REPO/'hardware/electronics/output_stage/check_placement.py']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        moves=[dict(ref=r, old_xy=position(old[r]), new_xy=p, rotation_added_degrees=rot, final_angle=angle(fps[r]), old_side=first(old[r], 'layer')[1], new_side=first(fps[r], 'layer')[1]) for r, (p, rot) in MOVES.items()],
        flipped_parts=sorted(FLIPS), flipped_template='P_R102', routes=routes, vias=vias,
        new_zones=[dict(uuid=ref_uid,label='input-protection-In6-ground',net=gnd,layer='In6.Cu',outline_mm=ref_ring)],
        retired_tracks=[o for o in retired if o['kind'] == 'PCB_TRACK'], retired_vias=[o for o in retired if o['kind'] == 'PCB_VIA'], changed_existing_zone_fills=sorted(changed), all_zone_settings_unchanged=True, native_VIN_entry_refill_explicitly_declared=True, changed_existing_zone_outlines=[dict(uuid=ground_id,old_outline_mm=old_ring,new_outline_mm=ring)],
        all_values_packages_pin_nets_unchanged=True, placement_and_pad_drill_screen=True,
        added_tracks=sum(len(r['segment_uuids']) for r in routes), added_vias=len(vias),
        divider_and_clamp_bias_routes_are_not_full_load_distribution=True,
        manufacturer_source='https://www.ti.com/lit/ds/symlink/tps2663.pdf', manufacturer_section='9.6.1, SLVSE94G',
        native_validation_pending=True, independent_audit_pending=True,
        exact_passive_MPN_and_derating_pending=True, UV_OV_and_clamp_connected_candidate=True, full_source_and_final_reference_pending=True,
        full_current_thermal_transient_qualified=False, fabrication_released=False)
    (OUT/'input-thresholds-routing.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(tracks=result['added_tracks'], vias=len(vias), changed_zones=sorted(changed))))


if __name__ == '__main__': run()
