"""Bounded LED_XLAT escape trial with explicit restoration of three blocking tracks."""
import copy
import itertools
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v4 import escape_options
from hardware.fabrication.digital_multilayer_escape_routes_v4 import multilayer_portals
from hardware.fabrication.digital_visibility_escape import route as visibility
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search

ROOT = Path(__file__).resolve().parent
REMOVED = {'47aa8893-63cd-519b-b6ec-d11095e3d85e', 'a60eac04-a119-52c5-a709-1958996b460f', 'd29d6f9e-b100-552d-b304-373b34c73ddb'}


def route(screen, net, face, start, contacts, deadline):
    for f, end in sorted(contacts, key=lambda p: math.dist(start, p[1])):
        if f != face:
            continue
        direct = [p for p in surface.candidate_paths(start, end) if screen.legal(net, face, p)]
        if direct:
            return dict(runs=[(face, min(direct, key=lambda p: LineString(p).length))], vias=[])
    obstacles = [g.buffer(d+.0005, quad_segs=32) for n, g, d in screen.geometry[face] if n != net]
    obstacles += [g.buffer(.4105, quad_segs=32) for n, f, g in screen.added if n != net and f == face]
    obstacles += [Point(p).buffer(.5105, quad_segs=32) for n, p in screen.new_vias if n != net]
    free = screen.outline.difference(unary_union(obstacles))
    for f, end in sorted(contacts, key=lambda p: math.dist(start, p[1]))[:6]:
        if f == face:
            p = visibility(screen, net, face, start, end, free, min(deadline, time.monotonic()+3))
            if p:
                return dict(runs=[(face, p)], vias=[])
    initial = {(face, tuple(start))}
    starts = multilayer_portals(initial, escape_options(screen, net, initial, 'start', min(deadline, time.monotonic()+6)), 'start')
    ends = multilayer_portals(contacts, escape_options(screen, net, contacts, 'end', min(deadline, time.monotonic()+6)), 'end')
    return search.route_multi(screen, net, starts, {f: ends for f in search.LAYERS}, deadline, max_visits=1500000)


def add(screen, net, result):
    assert all(screen.legal(net, f, p) for f, p in result['runs'])
    fresh = [p for p in result['vias'] if not any(n == net and math.dist(p, q) < 1e-7 for n, q in screen.vias+screen.new_vias)]
    assert all(screen.via_legal(net, p) for p in fresh)
    assert all(math.dist(p, q) > .563 for p, q in itertools.combinations(fresh, 2))
    screen.added += [(net, f, LineString(p)) for f, p in result['runs']]
    screen.new_vias += [(net, tuple(p)) for p in fresh]
    return dict(net=net, runs=result['runs'], new_vias_mm=fresh,
                planar_length_mm=sum(LineString(p).length for _, p in result['runs']))


def run():
    cp = ROOT/'staging/digital-exact-regions-inputs-41/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original = read_sexpr(pcb.read_text())
    removed = [n for n in children(original, 'segment') if first(n, 'uuid')[1] in REMOVED]
    assert len(removed) == 3 and all(float(first(n, 'width')[1]) == .2 for n in removed)
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in work['objects'] if o['uuid'] not in REMOVED]
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    surface.SIGNAL_LAYERS = search.LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    pad = next(o for o in work['objects'] if o.get('ref') == 'U3005' and o.get('pin') == '5')
    net = pad['net']
    assert net == 'LED_XLAT'
    via = [61.914772, 18.291228]
    lead = [pad['position_mm'], [61.914772, 20.525], via]
    tasks = [('LED_MOSI', 'F.Cu', [63.1375, 19.225], {('F.Cu', (60.7, 19.9))}),
             ('/CONTROLS/CONTROL_22', 'B.Cu', [60.2, 16.1], {('B.Cu', (64., 19.6))})]
    attempts, selected = [], None
    for order in (tasks, tasks[::-1]):
        screen = DigitalViaScreen(work, signal_layers=surface.SIGNAL_LAYERS)
        attempt = dict(order=[t[0] for t in order], repairs=[])
        attempts.append(attempt)
        attempt['escape_legal'] = screen.legal(net, 'F.Cu', lead) and screen.via_legal(net, via)
        if not attempt['escape_legal']:
            break
        routes = [add(screen, net, dict(runs=[('F.Cu', lead)], vias=[via]))]
        for n, f, start, contacts in order:
            result = route(screen, n, f, start, contacts, time.monotonic()+35)
            length = sum(LineString(p).length for _, p in result['runs']) if result else None
            attempt['repairs'].append(dict(net=n, found=bool(result), planar_length_mm=length))
            print(attempt, flush=True)
            if result is None or length > 20:
                break
            routes.append(add(screen, n, result))
        if len(routes) != 3:
            continue
        contacts = {(f, tuple(p)) for o in work['objects'] if o['net'] == net and o['group'] != pad['group']
                    for f in search.LAYERS if o['layers'].get(f)
                    for p in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else [])}
        ends = multilayer_portals(contacts, escape_options(screen, net, contacts, 'retained', time.monotonic()+10), 'retained')
        result = search.route_multi(screen, net, [dict(point=via, layers=list(search.LAYERS), runs=[], vias=[], cost=0., group='new')],
                                    {f: ends for f in search.LAYERS}, time.monotonic()+60, max_visits=2500000)
        length = sum(LineString(p).length for _, p in result['runs']) if result else None
        attempt.update(global_found=bool(result), global_length_mm=length)
        print(attempt, flush=True)
        if result and length < 40:
            routes.append(add(screen, net, result))
            selected = routes
            break
    paths = [cp, pcb, Path(__file__)]+[ROOT/n for n in ('digital_via_spacing_v2.py', 'digital_continuous_escape_options_v4.py', 'digital_multilayer_escape_routes_v4.py', 'digital_visibility_escape.py', 'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_pin_escape_routes.py', 'digital_native_spacing_search_v3.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')]
    receipt = dict(source_sha256={str(p): sha(p) for p in paths}, attempts=attempts,
                   candidate_emitted=bool(selected), fabrication_released=False)
    out = ROOT/'staging/digital-xlat-escape-repair-01'
    out.mkdir(exist_ok=False)
    if selected:
        board = [copy.deepcopy(n) for n in original if n not in removed]
        for r in selected:
            for f, path in r['runs']:
                for p, q in zip(path, path[1:]):
                    if math.dist(p, q) < 1e-7:
                        continue
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:xlat-repair:{sha(cp)}:{r["net"]}:{f}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), f], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:xlat-repair-via:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
        dest = out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        receipt.update(candidate_PCB_sha256=sha(dest), removed_objects=removed, removed_uuids=sorted(REMOVED), routes=selected,
                       geometry_delta=geometry_delta(original, board), native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Complete; candidate emitted:', bool(selected), flush=True)


if __name__ == '__main__':
    run()
