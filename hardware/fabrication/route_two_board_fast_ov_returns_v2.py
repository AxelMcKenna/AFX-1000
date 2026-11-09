"""Improve the fast-OV shutdown loop and adjacent source/reference paths."""
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

BASE = STAGING/'two-board-power-fast-ov-native-03'
CAP = STAGING/'two-board-power-routing-inputs-2383-fast-ov/capture.json'
PLACEMENT = STAGING/'two-board-placement-05/capture.json'
OUT = STAGING/'two-board-power-fast-ov-return-02'
MOVES={'P_Q103':([196.2,131.15],180),'G_NT1':([199.65,132.3],0)}
RETIRED_LABELS={'gate-inner','gate-pin','shutdown-ground','shutdown-ground-inner','gate-pulldown-ground','shutdown-drain','shutdown-run-inner','comparator-AUX-feed','VIN-sense-inner','VIN-AUX-feed'}


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text())
    for p, h in cap['source_sha256'].items(): assert sha(REPO/p) == h, p
    board = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    old = {prop(f, 'Reference')[2]: f for f in children(board, 'footprint')}
    fps = copy.deepcopy(old)
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPFASTRETURN02:'+sha(CAP)+':'+label))
    previous=json.loads((BASE/'fast-ov-routing.json').read_text())
    retired_ids={u for r in previous['routes'] if r['label'] in RETIRED_LABELS for u in r['segment_uuids']}
    retired_ids.update(v['uuid'] for v in previous['vias'] if v['label'] in ['shutdown-gate','shutdown-ground','shutdown-drain'])
    retired=[o for o in cap['objects'] if o['uuid'] in retired_ids]
    assert len(retired)==23 and sum(o['kind']=='PCB_TRACK' for o in retired)==20 and sum(o['kind']=='PCB_VIA' for o in retired)==3
    for r,(p,rot) in MOVES.items():fps[r]=rotate_footprint(old[r],p,rot)
    placement = json.loads(PLACEMENT.read_text()); records = {r['id']: r for r in placement['parts']}
    for r, template in [('P_C204', 'P_C205'), ('P_C104', 'P_C102'), ('P_C101', 'P_C102'), *[(r,'P_R102') for r in ['P_R101','P_R103','P_R104']]]:
        for k in ['side', 'angle', 'body_relative_xy', 'courtyard_relative_xy', 'additional_planar_reserves', 'tails_relative_xy']:
            records[r][k] = copy.deepcopy(records[template][k])
    assert not children(old['G_NT1'], 'model')
    placement['parts'].append(dict(id='G_NT1', height_mm=0.0, side='F', angle=0,
        body_relative_xy=[-1.2, -.8, 1.2, .8], additional_planar_reserves=[], tails_relative_xy=[]))
    new_record=copy.deepcopy(records['P_C401']);new_record['id']='P_C114';placement['parts'].append(new_record)
    moving=set(MOVES)
    mechanical_check(fps, moving, placement)
    objects=[transform_object(o,position(old[o['ref']]),*MOVES[o['ref']]) if o.get('ref') in MOVES else o for o in cap['objects'] if o['uuid'] not in retired_ids]
    geoms = [(o, l, routing.shape(ps)) for o in objects for l, ps in o['layers'].items() if ps]
    trees = {l: ([(o, g) for o, k, g in geoms if k == l], STRtree([g for o, k, g in geoms if k == l])) for l in cap['copper_layers']}
    holes = [(o, Point(o['position_mm']), max(o['drill_mm'])/2) for o in objects if o.get('kind') == 'PAD' and any(o['drill_mm'])]
    holes += [(o, Point(o['position_mm']), o['drill_mm']/2) for o in objects if o['kind'] == 'PCB_VIA']
    outline = routing.shape(cap['outline']).buffer(-.5)
    mounts = [(Point(o['position_mm']), max(3.6, max(o['drill_mm'])/2+.5)) for o in objects if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    for r in moving:
        g = box(*courtyard(fps[r], first(fps[r], 'layer')[1][0]+'.CrtYd'))
        assert outline.covers(g) and all(g.distance(p) >= radius+.3 for p, radius in mounts)
    for o, l, g in geoms:
        if o.get('ref') not in moving: continue
        assert outline.covers(g)
        rows, tree = trees[l]
        for i in tree.query(g.buffer(.211)):
            q, h = rows[int(i)]
            if q.get('ref') != o['ref'] and q['net'] != o['net']: assert g.distance(h) >= .21-1e-7, (o['ref'], o.get('pin'), q.get('ref'), q.get('pin'), q['uuid'], g.distance(h))
        assert all(g.distance(p)-r >= .15-2e-6 for q, p, r in holes), (o['ref'], 'drill')
        assert all(z['layer'] != l or z['uuid']=='a147ef12-37f5-562e-9340-6c74b3790186' or g.distance(routing.shape(z['authored_outline'])) > .21 for z in cap['zones'])
    for i,f in enumerate(board):
        if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in MOVES:board[i]=fps[prop(f,'Reference')[2]]
    board[:]=[n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retired_ids)]
    codes = {str(n[2]): int(n[1]) for n in children(board, 'net')}
    routes = []; vias = []; added = []; changed = set()
    def pad(r, p): return next(o for o in objects if o.get('ref') == r and o.get('pin') == p)
    def xy(r, p): return pad(r, p)['position_mm']
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
    gnd='PWR_AGND';aux='PWR_V2V5_AUX';vin=pad('P_R115','1')['net'];run='PWR_POWER_RUN'
    sense=pad('P_U103','3')['net'];ref=pad('P_U103','4')['net'];out=pad('P_U103','1')['net'];gate=pad('P_Q103','1')['net']
    sites=[('shutdown-source-ground',gnd,[196.3,129.0]),('pulldown-ground',gnd,[198.2,134.9]),('shutdown-drain',run,[194.2,130.7])]
    for label,net,p in sites:via(label,net,p)
    route('comparator-AUX-feed-adjacent',aux,'In2.Cu',[[197.6,114.1],[195.8,114.6]],.3,2)
    route('VIN-sense-adjacent',vin,'In5.Cu',[[193.8,113.2],[192.8,113.7],[193.2,117.8]],.25,5.5)
    route('VIN-AUX-adjacent',vin,'In5.Cu',[[193.2,117.8],[191.5,119.2],[189.2,119.2],[189.2,123.5],[188.95,125.3]],.4,12)
    route('shutdown-gate-direct',gate,'F.Cu',[xy('P_Q103','1'),xy('P_R121','2')],.2,2.5)
    route('shutdown-source-ground',gnd,'F.Cu',[xy('P_Q103','2'),[196.3,129.0]],.3,1.5)
    route('pulldown-ground',gnd,'B.Cu',[xy('P_R120','2'),[198.2,134.9]],.25,1.5)
    route('shutdown-drain',run,'F.Cu',[xy('P_Q103','3'),[195.2625,130.9],[194.2,130.7]],.2,1.4)
    route('shutdown-to-SHDN',run,'In2.Cu',[[194.2,130.7],[194.2,129.1],[196,127.6],[198,127.6],[199,125.3]],.2,9)
    ground_id='d41ab58e-16e9-5d76-8b14-dc335aff8371'
    ground6='78fadc71-5bdb-5968-8ca8-0e3b4b40722f'
    auxref='dfd01f0a-edcf-55b7-aecb-2d44a419b9b3'
    rings={ground_id:[[193.5,118.8],[193.5,113],[193.1,113],[193.1,109.1],[200.4,109.1],[200.4,118.8],[223,118.8],[223,124.4],[205,124.4],[205,128.8],[201,128.8],[201,137.8],[195.1,137.8],[195.1,131.1],[193.9,131.1],[193.9,128],[189,128],[189,122.8],[193.5,122.8]],
        ground6:[[188.6,113],[192.5,113],[192.5,109.1],[201.3,109.1],[201.3,118.8],[223,118.8],[223,124.4],[205,124.4],[205,128.8],[201,128.8],[201,137.8],[195.2,137.8],[195.2,128],[188.6,128]],
        auxref:[[187.7,128.3],[193.65,128.3],[193.65,131.35],[194.8,131.35],[194.8,133.2],[191.6,133.2],[191.6,136.6],[186.7,136.6],[186.7,134.6],[187.7,134.6]]}
    rings['bc76c316-2c04-5ecb-85b7-3e5f80b26bf1']=[[186.5,128.3],[193.65,128.3],[193.65,131.35],[194.8,131.35],[194.8,133.2],[191.6,133.2],[191.6,136.6],[187.3,136.6],[187.3,131.2],[186.5,131.2]]
    outlines=[]
    from shapely.geometry import Polygon
    for z in children(board,'zone'):
        ident=str(first(z,'uuid')[1])
        if ident in rings:
            ring=rings[ident];g=Polygon(ring);assert g.is_valid and outline.covers(g)
            before=[list(map(float,p[1:3])) for p in children(first(first(z,'polygon'),'pts'),'xy')]
            first(first(z,'polygon'),'pts')[:]=[a('pts'),*[[a('xy'),*p] for p in ring]]
            outlines.append(dict(uuid=ident,old_outline_mm=before,new_outline_mm=ring));changed.add(ident)
    for o in cap['objects']:
        if o.get('ref') not in MOVES and o['uuid'] not in retired_ids:continue
        for z in cap['zones']:
            ps=o['layers'].get(z['layer'])
            if ps and routing.shape(ps).distance(routing.shape(z['authored_outline']))<.21:changed.add(z['uuid'])
    for o in objects:
        if o.get('ref') not in moving:continue
        for z in cap['zones']:
            ps=o['layers'].get(z['layer'])
            if ps and routing.shape(ps).distance(routing.shape(z['authored_outline']))<.21:changed.add(z['uuid'])
    for z in children(board,'zone'):
        if str(first(z,'uuid')[1]) in changed:z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    shutil.copytree(BASE, OUT, ignore=shutil.ignore_patterns('*.log', 'drc.*', 'erc.*', 'netlist.xml', 'review.json', 'circuit-audit.json', 'plots', '*-audit.json', '*-review.json', 'rejected-source-net-status.json', 'README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP32';p.write_text(sexpr(root)+'\n')
    paths=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'fast-ov-routing.json',BASE/'fast-ov-audit.json',BASE/'fast-ov-return-load-review.json',STAGING/'assembly-layout-04/allocation.json',
        *[REPO/'hardware/fabrication'/q for q in ['repack_two_board_buck_input.py','route_two_board_buck_cell.py','route_two_board_power_layer_detours.py','route_nf_surface.py']],REPO/'hardware/electronics/output_stage/check_placement.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},moves=[dict(ref=r,old_xy=position(old[r]),new_xy=p,rotation_added_degrees=rot,final_angle=angle(fps[r]),old_side=first(old[r],'layer')[1],new_side=first(fps[r],'layer')[1]) for r,(p,rot) in MOVES.items()],
        routes=routes,vias=vias,retired_tracks=[o for o in retired if o['kind']=='PCB_TRACK'],retired_vias=[o for o in retired if o['kind']=='PCB_VIA'],
        changed_existing_zone_fills=sorted(changed),changed_existing_zone_outlines=outlines,new_zones=[],
        added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),all_values_packages_pin_nets_unchanged=True,
        native_validation_pending=True,independent_audit_pending=True,electrical_current_thermal_transient_qualified=False,fabrication_released=False)
    (OUT/'fast-ov-return-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(added_tracks=result['added_tracks'],added_vias=len(vias),retired_tracks=20,retired_vias=3,changed_zones=sorted(changed))))

if __name__=='__main__':run()
