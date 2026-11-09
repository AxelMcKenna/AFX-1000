"""Regroup and route the fast overvoltage monitor with a dedicated local bypass."""
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

BASE = STAGING/'two-board-power-input-thresholds-native-03'
CAP = STAGING/'two-board-power-routing-inputs-2405-input-thresholds/capture.json'
PLACEMENT = STAGING/'two-board-placement-05/capture.json'
OUT = STAGING/'two-board-power-fast-ov-01'
MOVES = {'P_U103': [[195.8, 111.3], 180], 'P_Q103': [[195.2, 131], 0], 'P_R115': [[194.5, 111.5], 0], 'P_R116': [[196.7, 111.5], 270], 'P_R117': [[199.2, 111.5], 90], 'P_R118': [[194.2, 115.55], 180], 'P_R119': [[191, 115.3], 270], 'P_C109': [[199.2, 111.5], 0], 'P_R120': [[197.1, 134.8], 180], 'P_R121': [[196.7, 135.1], 0]}
NEW_REF="P_C114"
DONOR="P_C401"
NEW_XY=[194.9,114.8]
NEW_ROT=180


def run():
    assert not OUT.exists()
    cap = json.loads(CAP.read_text())
    for p, h in cap['source_sha256'].items(): assert sha(REPO/p) == h, p
    board = read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    old = {prop(f, 'Reference')[2]: f for f in children(board, 'footprint')}
    fps = copy.deepcopy(old)
    def uid(label): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'AFX:TBPFASTOV01:'+sha(CAP)+':'+label))
    for o in cap['objects']:
        if o.get('ref') in MOVES and o.get('pin'): assert cap['all_groups'][o['group']] == [o['uuid']]
    for r,(p,rot) in MOVES.items(): fps[r]=rotate_footprint(old[r],p,rot)
    new=rotate_footprint(old[DONOR],NEW_XY,NEW_ROT)
    prop(new,'Reference')[2]=NEW_REF; first(new,'uuid')[1]=uid('C114-footprint')
    symbol_uid=uid('C114-symbol')
    oldpaths=json.loads((BASE/'symbol-paths.json').read_text())
    symbol_path=oldpaths[DONOR].rsplit('/',1)[0]+'/'+symbol_uid
    new[:]=[n for n in new if not(isinstance(n,list) and n and n[0]=='path')]
    new.append([a('path'),symbol_path])
    new_ids={}
    for pd in children(new,'pad'):
        ident=uid('C114-pad-'+str(pd[1])); first(pd,'uuid')[1]=ident; new_ids[str(pd[1])]=ident
    fps[NEW_REF]=new
    placement = json.loads(PLACEMENT.read_text()); records = {r['id']: r for r in placement['parts']}
    for r, template in [('P_C204', 'P_C205'), ('P_C104', 'P_C102'), ('P_C101', 'P_C102'), *[(r,'P_R102') for r in ['P_R101','P_R103','P_R104']]]:
        for k in ['side', 'angle', 'body_relative_xy', 'courtyard_relative_xy', 'additional_planar_reserves', 'tails_relative_xy']:
            records[r][k] = copy.deepcopy(records[template][k])
    assert not children(old['G_NT1'], 'model')
    placement['parts'].append(dict(id='G_NT1', height_mm=0.0, side='F', angle=0,
        body_relative_xy=[-1.2, -.8, 1.2, .8], additional_planar_reserves=[], tails_relative_xy=[]))
    new_record=copy.deepcopy(records[DONOR]);new_record['id']=NEW_REF;placement['parts'].append(new_record)
    moving=set(MOVES)|{NEW_REF}
    mechanical_check(fps, moving, placement)
    objects=[transform_object(o,position(old[o['ref']]),*MOVES[o['ref']]) if o.get('ref') in MOVES else o for o in cap['objects']]
    for o in cap['objects']:
        if o.get('ref')==DONOR:
            n=transform_object(o,position(old[DONOR]),NEW_XY,NEW_ROT)
            n.update(ref=NEW_REF,uuid=new_ids[o['pin']],group=new_ids[o['pin']]);objects.append(n)
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
    board.append(new)
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
    sites=[('sense',sense,[198,109.4]),('reference',ref,[193.7,109.6]),('reference-cap',ref,[199.5,113.7]),
        ('comparator-ground',gnd,[197.95,111.3]),('bypass-ground',gnd,[193.8,117]),('bypass-supply',aux,[195.8,114.6]),
        ('divider-VIN',vin,[193.8,113.2]),('VIN-source',vin,[193.2,117.8]),('input-bulk-ground',gnd,[194,118.3]),
        ('shutdown-ground',gnd,[194.9,132.9]),('shutdown-drain',run,[197.1,130.5]),
        ('shutdown-gate',gate,[196.3,129.7]),('gate-receiver',gate,[195.7,134.8]),
        ('output-receiver',out,[196,137]),('output-source',out,[198.3,113.6])]
    for label,net,p in sites:via(label,net,p)
    route('sense-pin',sense,'F.Cu',[xy('P_U103','3'),[198,109.4]],.2,2)
    route('sense-feedback',sense,'F.Cu',[xy('P_R117','2'),[198,109.4]],.2,2)
    route('sense-divider',sense,'B.Cu',[xy('P_R115','2'),xy('P_R116','1')],.2,2.5)
    route('sense-via',sense,'B.Cu',[xy('P_R116','1'),[196.7,109.4],[198,109.4]],.2,3)
    route('reference-pin',ref,'F.Cu',[xy('P_U103','4'),[193.7,109.6]],.2,1.7)
    route('reference-divider',ref,'B.Cu',[xy('P_R118','2'),xy('P_R119','1')],.2,3)
    route('reference-divider-feed',ref,'B.Cu',[xy('P_R119','1'),[192.8,114.3875],[192.8,109.6],[193.7,109.6]],.2,7.6)
    route('reference-inner',ref,'In2.Cu',[[193.7,109.6],[194.7,113],[194.7,115.3],[199.5,115.3],[199.5,113.7]],.2,12.5)
    route('reference-cap',ref,'B.Cu',[xy('P_C109','1'),[199.5,113.7]],.2,1.5)
    route('reference-cap-ground',gnd,'B.Cu',[xy('P_C109','2'),[197.95,111.3]],.25,2)
    route('sense-ground',gnd,'B.Cu',[xy('P_R116','2'),[197.95,111.3]],.25,2)
    route('comparator-ground',gnd,'F.Cu',[xy('P_U103','2'),[197.95,111.3]],.3,1.2)
    route('comparator-bypass-supply',aux,'F.Cu',[xy('P_U103','5'),xy(NEW_REF,'1')],.3,2)
    route('comparator-bypass-ground',gnd,'F.Cu',[xy(NEW_REF,'2'),[193.8,117]],.3,2)
    route('comparator-AUX-escape',aux,'F.Cu',[xy(NEW_REF,'1'),[195.1,114.025],[195.8,114.6]],.3,1.5)
    route('comparator-AUX-feed',aux,'In3.Cu',[[197.6,114.1],[195.8,114.6]],.3,2)
    route('reference-AUX-feed',aux,'B.Cu',[xy('P_R118','1'),[195.8,114.6]],.25,1.5)
    route('VIN-divider',vin,'B.Cu',[xy('P_R115','1'),[193.8,113.2]],.25,1.2)
    route('VIN-sense-inner',vin,'In4.Cu',[[193.8,113.2],[192.8,113.7],[193.2,117.8]],.25,5.5)
    route('VIN-AUX-feed',vin,'In4.Cu',[[193.2,117.8],[191.5,119.2],[189.2,119.2],[189.2,123.5],[188.95,125.3]],.4,12)
    route('bulk-ground',gnd,'B.Cu',[xy('P_C102','2'),[192,119.5],[194,118.3]],.4,5.5)
    route('reference-ground',gnd,'B.Cu',[xy('P_R119','2'),xy('P_C102','2')],.25,4)
    route('feedback-output',out,'F.Cu',[xy('P_U103','1'),xy('P_R117','1')],.2,2.5)
    route('output-source',out,'F.Cu',[xy('P_R117','1'),[198.3,113.6]],.2,1.6)
    route('output-inner',out,'In5.Cu',[[198.3,113.6],[200.3,117.8],[201,119],[201,124],[200.3,129.2],[198,134],[196,137]],.2,28)
    route('output-receiver',out,'F.Cu',[[196,137],xy('P_R121','1')],.2,1.5)
    route('gate-resistor',gate,'F.Cu',[xy('P_R121','2'),[195.7,134.8]],.2,1.6)
    route('gate-pulldown',gate,'B.Cu',[[195.7,134.8],xy('P_R120','1')],.2,2)
    route('gate-inner',gate,'In2.Cu',[[195.7,134.8],[196.2,133.3],[196.3,129.7]],.2,5.5)
    route('gate-pin',gate,'F.Cu',[[196.3,129.7],xy('P_Q103','1')],.2,2.3)
    route('shutdown-ground',gnd,'F.Cu',[xy('P_Q103','2'),[194.9,132.9]],.3,1.5)
    route('shutdown-ground-inner',gnd,'In6.Cu',[[194.9,132.9],[195.6,132.9]],.3,1)
    route('gate-pulldown-ground',gnd,'B.Cu',[xy('P_R120','2'),[198.3,135.7125],[198.3,132.9],[194.9,132.9]],.25,7.6)
    route('shutdown-drain',run,'F.Cu',[xy('P_Q103','3'),[197.1,130.5]],.2,1.2)
    route('shutdown-run-inner',run,'In4.Cu',[[197.1,130.5],[194,130]],.2,3.2)
    # Extend the existing U101 reference above the comparator and beneath its receiver.
    ground_id='d41ab58e-16e9-5d76-8b14-dc335aff8371'
    ground6='78fadc71-5bdb-5968-8ca8-0e3b4b40722f'
    rings={ground_id:[[193.5,118.8],[193.5,113],[193.1,113],[193.1,109.1],[200.4,109.1],[200.4,118.8],[223,118.8],[223,124.4],[205,124.4],[205,128.8],[200,128.8],[200,130.2],[195.2,130.2],[195.2,128],[189,128],[189,122.8],[193.5,122.8]],
           ground6:[[189,113],[193.1,113],[193.1,109.1],[200.5,109.1],[200.5,118.8],[223,118.8],[223,124.4],[205,124.4],[205,128.8],[201,128.8],[201,137.8],[195.2,137.8],[195.2,128],[189,128]]}
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
        if o.get('ref') not in MOVES:continue
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
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP31';p.write_text(sexpr(root)+'\n')
    schpath=OUT/'P_power_p03.kicad_sch';sch=read_sexpr(schpath.read_text())
    symbol=copy.deepcopy(next(n for n in children(sch,'symbol') if prop(n,'Reference')[2]==DONOR))
    old_at=first(symbol,'at');dx,dy=0,3556-float(old_at[2])
    def edit(n):
        if not isinstance(n,list) or not n:return
        if n[0]=='uuid':n[1]=uid('new-symbol-'+str(n[1]))
        if n[0]=='at':n[1]=float(n[1])+dx;n[2]=float(n[2])+dy
        if n[0]=='reference':n[1]=NEW_REF
        for x in n[1:]:edit(x)
    edit(symbol);first(symbol,'uuid')[1]=symbol_uid;prop(symbol,'Reference')[2]=NEW_REF;sch.append(symbol)
    from hardware.fabrication.integrate_two_board_power_v4 import anchor
    for pin,net in [('1',aux),('2',gnd)]:
        x,y=anchor(sch,NEW_REF,pin)
        sch.append([a('global_label'),net,[a('shape'),a('passive')],[a('at'),x,y,0 if pin=='2' else 180],[a('effects'),[a('font'),[a('size'),1.27,1.27]],[a('justify'),a('left')]], [a('uuid'),uid('label-'+pin)]])
    schpath.write_text(sexpr(sch)+'\n')
    expected=json.loads((BASE/'expected-circuit.json').read_text());expected[NEW_REF]=copy.deepcopy(expected[DONOR]);expected[NEW_REF]['source_ref']='C114'
    oldpaths[NEW_REF]=symbol_path
    (OUT/'expected-circuit.json').write_text(json.dumps(expected,indent=2,sort_keys=True)+'\n')
    (OUT/'symbol-paths.json').write_text(json.dumps(oldpaths,indent=2,sort_keys=True)+'\n')
    paths=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'P_power_p03.kicad_sch',BASE/'expected-circuit.json',BASE/'symbol-paths.json',BASE/'input-thresholds-audit.json',STAGING/'assembly-layout-04/allocation.json',
           *[REPO/'hardware/fabrication'/p for p in ['repack_two_board_buck_input.py','route_two_board_buck_cell.py','route_two_board_power_layer_detours.py','route_nf_surface.py','integrate_two_board_power_v4.py']],REPO/'hardware/electronics/output_stage/check_placement.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},moves=[dict(ref=r,old_xy=position(old[r]),new_xy=p,rotation_added_degrees=rot,final_angle=angle(fps[r]),old_side=first(old[r],'layer')[1],new_side=first(fps[r],'layer')[1]) for r,(p,rot) in MOVES.items()],
        added_component=dict(ref=NEW_REF,template=DONOR,xy=NEW_XY,rotation_from_template=NEW_ROT,value=expected[NEW_REF]['value'],pins=expected[NEW_REF]['pins'],reason='Dedicated same-face comparator supply bypass'),
        routes=routes,vias=vias,retired_tracks=[],retired_vias=[],changed_existing_zone_fills=sorted(changed),changed_existing_zone_outlines=outlines,new_zones=[],
        added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),all_existing_values_packages_pin_nets_unchanged=True,
        manufacturer_source='https://www.ti.com/lit/ds/symlink/tlv7011.pdf',manufacturer_section='5 and 10.1, SLVSDM5F',native_validation_pending=True,independent_audit_pending=True,
        full_current_thermal_transient_qualified=False,fabrication_released=False)
    (OUT/'fast-ov-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(tracks=result['added_tracks'],vias=len(vias),changed_zones=sorted(changed))))

if __name__=='__main__':run()
