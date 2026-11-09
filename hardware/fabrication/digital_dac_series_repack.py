"""Move R1014 locally, restore both series nets and reserve the LED_35 route."""
import copy
import itertools
import json
import math
import time
import uuid
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import Point, LineString, Polygon, box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add, route
import hardware.fabrication.digital_xlat_escape_repair as repair
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v4 as search

ROOT = Path(__file__).resolve().parent
SRC, DATA, LED = '/PROCESSOR/DAC_DATA_SRC', '/PROCESSOR/DAC_DATA', '/LED/LED_35'


def polys(g):
    return [dict(outer=list(g.exterior.coords), holes=[list(h.coords) for h in g.interiors])]


def run():
    cp = ROOT/'staging/digital-led-sink-inputs-34/capture.json'
    tp = ROOT/'staging/digital-dac-series-templates-01/templates.json'
    lp = ROOT/'staging/digital-led35-dac-continuous-repair-01/construction.json'
    cap, templates, led_receipt = [json.loads(p.read_text()) for p in (cp, tp, lp)]
    for receipt in (cap, templates, led_receipt):
        assert all(sha(Path(p)) == h for p, h in receipt['source_sha256'].items())
    assert all(sha(tp.parent/r['file']) == r['sha256'] for r in templates['templates'])
    led = led_receipt['attempts'][0]['routes'][0]['proposed_route']
    assert led_receipt['attempts'][0]['routes'][0]['net'] == LED
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original = read_sexpr(pcb.read_text())
    fps = {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f for f in children(original, 'footprint')}
    old = fps['R1014']
    assert list(map(float, first(old, 'at')[1:])) == [20, 19, 90] and first(old, 'layer')[1] == 'F.Cu'
    removed = [n for tag in ('segment', 'via') for n in children(original, tag) if first(n, 'net')[1] in (SRC, DATA)]
    ids = {first(n, 'uuid')[1] for n in removed}
    assert len(ids) == 14
    base = copy.deepcopy(cap)
    base['objects'] = [o for o in base['objects'] if o['uuid'] not in ids and o.get('ref') != 'R1014']
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    surface.SIGNAL_LAYERS = search.LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    repair.search = search
    screen = DigitalViaScreen(base, signal_layers=search.LAYERS)
    add(screen, LED, led)
    profile = Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
    sides = {r: first(f, 'layer')[1][0] for r, f in fps.items()}
    courts = {r: box(*courtyard(f, sides[r]+'.CrtYd')) for r, f in fps.items() if r != 'R1014'}
    through = {r: [box(*pad_box(f, p, .5)) for p in children(f, 'pad') if p[2] == 'thru_hole'] for r, f in fps.items() if r != 'R1014'}
    mounts = [box(x-3.6,y-3.6,x+3.6,y+3.6) for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]]
    geometries = {side: [(o['net'], surface.shape(o['layers'][side+'.Cu'])) for o in base['objects'] if o['layers'].get(side+'.Cu')] for side in ('F','B')}
    for side, rows in geometries.items():
        rows += [(LED, LineString(p).buffer(.1, quad_segs=32)) for f, p in led['runs'] if f == side+'.Cu']
        rows += [(LED, Point(p).buffer(.3, quad_segs=32)) for p in led['vias']]
    trees = {s: STRtree([g for n, g in rows]) for s, rows in geometries.items()}
    drilled = [(Point(p), r) for _, p, r, _ in screen.drilled] + [(Point(p), .15) for p in led['vias']]
    endpoints = {n: next(o for o in base['objects'] if o['kind'] == 'PAD' and o['net'] == n) for n in (SRC, DATA)}
    poses = []
    counts = dict(screened=0, mechanical=0, pad_clear=0)
    for template in templates['templates']:
        fp = read_sexpr((tp.parent/template['file']).read_text())
        side = template['side']
        court = box(*courtyard(fp, side+'.CrtYd'))
        for x, y in itertools.product([20+i*.5 for i in range(45)], [16+i*.5 for i in range(39)]):
            counts['screened'] += 1
            cc = translate(court, x, y)
            if not profile.covers(cc) or cc.distance(profile.boundary) < .5-1e-8 or any(cc.distance(m) < .15-1e-8 for m in mounts):
                continue
            if any(cc.distance(g) < .3-1e-8 for r, g in courts.items() if sides[r] == side):
                continue
            if any(cc.intersection(g).area > 1e-10 for r, rows in through.items() if sides[r] != side for g in rows):
                continue
            counts['mechanical'] += 1
            pads = []
            for p in template['pads']:
                g = translate(surface.shape(p['polygons']), x, y)
                if any(n != p['net'] and g.distance(h) < .21-1e-8 for i in trees[side].query(g.buffer(.22)) for n, h in [geometries[side][int(i)]]):
                    break
                if any(q.distance(g)-r < .16-1e-8 for q, r in drilled):
                    break
                pads.append(dict(uuid=p['uuid'], ref='R1014', pin=p['pin'], net=p['net'], kind='PAD',
                                 position_mm=[p['position_mm'][0]+x,p['position_mm'][1]+y],
                                 drill_mm=[0,0], layers={side+'.Cu':polys(g)}, group=None))
            if len(pads) != 2:
                continue
            counts['pad_clear'] += 1
            moved = copy.deepcopy(fp)
            first(moved, 'at')[1:3] = [x,y]
            score = sum(math.dist(p['position_mm'], endpoints[p['net']]['position_mm']) for p in pads)
            poses.append(dict(side=side, angle=template['angle'], position_mm=[x,y], template=template['file'], pads=pads, footprint=moved, score=score))
    poses.sort(key=lambda p: p['score'])
    print('Placement screen:', counts, flush=True)
    attempts = []
    selected = None
    deadline = time.monotonic()+600
    for pose in poses[:32]:
        if time.monotonic() > deadline:
            break
        work = copy.deepcopy(base)
        work['objects'] += pose['pads']
        for order in ((SRC, DATA), (DATA, SRC)):
            if time.monotonic() > deadline:
                break
            screen = DigitalViaScreen(work, signal_layers=search.LAYERS)
            routes = [add(screen, LED, led)]
            attempt = dict(side=pose['side'], angle=pose['angle'], position_mm=pose['position_mm'], order=order, routes=[])
            attempts.append(attempt)
            for net in order:
                pad = next(p for p in pose['pads'] if p['net'] == net)
                target = endpoints[net]
                contacts = {(f, tuple(target['position_mm'])) for f in search.LAYERS if target['layers'].get(f)}
                result = route(screen, net, pose['side']+'.Cu', pad['position_mm'], contacts, min(deadline, time.monotonic()+20))
                length = sum(LineString(p).length for f, p in result['runs']) if result else None
                bound = 20 if net == SRC else 30
                attempt['routes'].append(dict(net=net, found=bool(result), length_mm=length, search_bound_mm=bound))
                print(attempt, flush=True)
                if result is None or length > bound:
                    break
                routes.append(add(screen, net, result))
            if len(routes) == 3:
                selected = pose, routes
                break
        if selected:
            break
    paths = [cp, tp, lp, pcb, Path(__file__)] + [tp.parent/r['file'] for r in templates['templates']] + [ROOT/n for n in
        ('audit_candidate.py','digital_core_layout.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py',
         'digital_continuous_escape_options_v4.py','digital_multilayer_escape_routes_v4.py','digital_visibility_escape.py',
         'digital_native_spacing_search_v4.py','digital_native_spacing_search_v3.py','digital_native_spacing_search_v2.py',
         'digital_continuous_via_bridges.py','nf_minimum_logic.py','nf_pin_escape_routes.py','route_nf_surface.py',
         'nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    paths.append(ROOT.parent/'electronics/output_stage/check_placement.py')
    receipt = dict(source_sha256={str(p):sha(p) for p in paths}, placement_counts=counts, attempts=attempts,
                   candidate_emitted=bool(selected), removed_uuids=sorted(ids), native_rules_relaxed=False,
                   search_bounds_are_not_electrical_acceptance=True, fabrication_released=False)
    out = ROOT/'staging/digital-dac-series-repack-01'
    out.mkdir(exist_ok=False)
    if selected:
        pose, routes = selected
        board = copy.deepcopy(original)
        board[board.index(old)] = pose['footprint']
        for n in removed:
            board.remove(n)
        for r in routes:
            for face, path in r['runs']:
                for p, q in zip(path, path[1:]):
                    if math.dist(p,q) < 1e-7:
                        continue
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DAC-repack:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DAC-repack-via:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
        dest = out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        receipt.update(candidate_PCB_sha256=sha(dest), routes=routes, removed_objects=removed,
                       component_move=dict(ref='R1014',before_mm=[20,19],before_side='F',before_angle=90,
                                           after_mm=pose['position_mm'],after_side=pose['side'],after_angle=pose['angle'],template=pose['template']),
                       geometry_delta=geometry_delta(original,board),native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Candidate emitted:', bool(selected), flush=True)


if __name__ == '__main__':
    run()
