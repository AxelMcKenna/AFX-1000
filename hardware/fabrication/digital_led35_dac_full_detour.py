"""Try LED_35 with complete DAC_DATA reconstruction; both nets must connect."""
import copy
import itertools
import json
import math
import time
import uuid
from pathlib import Path

from shapely.geometry import LineString
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add, route
import hardware.fabrication.digital_xlat_escape_repair as repair
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v4 as search

ROOT = Path(__file__).resolve().parent
REMOVED = {'49e7ded1-340e-5485-99c2-a865be4b0c60', 'd1704b7d-b7d5-504f-99b4-de01fd354df2', '7265202b-d3ae-53e8-a85b-8ae1bd9fa2bf', '0b265c1d-6af2-5ed2-8905-cc92d37c56c3'}
LED = '/LED/LED_35'
DAC = '/PROCESSOR/DAC_DATA'


def run():
    cp = ROOT / 'staging/digital-led-sink-inputs-34/capture.json'
    dp = ROOT / 'staging/digital-led35-rework-survey-01/diagnosis.json'
    cap = json.loads(cp.read_text())
    for receipt in (cap, json.loads(dp.read_text())):
        assert all(sha(Path(p)) == h for p, h in receipt['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original = read_sexpr(pcb.read_text())
    removed = [n for tag in ('segment', 'via') for n in children(original, tag) if first(n, 'uuid')[1] in REMOVED]
    assert len(removed) == 4 and all(first(n, 'net')[1] == DAC for n in removed)
    assert all(float(first(n, 'width')[1]) == .2 for n in removed if str(n[0]) == 'segment')
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in work['objects'] if o['uuid'] not in REMOVED]
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    surface.SIGNAL_LAYERS = search.LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    repair.search = search
    led_pad = next(o for o in cap['objects'] if o.get('ref') == 'U3002' and o.get('pin') == '16')
    header = next(o for o in cap['objects'] if o['kind'] == 'PAD' and o['net'] == LED and o['ref'].startswith('J'))
    via = (33.444941, 22.040900)
    attempts = []
    selected = None
    deadline = time.monotonic() + 240
    for order in itertools.permutations((LED, DAC)):
        screen = DigitalViaScreen(work, signal_layers=search.LAYERS)
        routes = [add(screen, LED, dict(runs=[('F.Cu', [led_pad['position_mm'], via])], vias=[via]))]
        attempt = dict(order=order, routes=[])
        attempts.append(attempt)
        for net in order:
            if net == LED:
                start = dict(point=via, layers=list(search.LAYERS), runs=[], vias=[], cost=0., group='source')
                end = dict(point=header['position_mm'], layers=list(search.LAYERS), runs=[], vias=[], cost=0., group='target')
                result = search.route_multi(screen, net, [start], {f: [end] for f in search.LAYERS},
                                            min(deadline, time.monotonic()+75), max_visits=5000000)
                bound = 180
            else:
                result = route(screen, net, 'F.Cu', [20.0, 18.0875],
                               {(f, (32.16, 23.0)) for f in search.LAYERS}, min(deadline, time.monotonic()+40))
                bound = 30
            length = sum(LineString(p).length for f, p in result['runs']) if result else None
            attempt['routes'].append(dict(net=net, found=bool(result), length_mm=length, search_bound_mm=bound))
            print(attempt, flush=True)
            if result is None or length > bound:
                break
            routes.append(add(screen, net, result))
        if len(routes) == 3:
            selected = routes
            break
    paths = [cp, dp, pcb, Path(__file__)] + [ROOT/n for n in
        ('audit_candidate.py', 'digital_xlat_escape_repair.py', 'digital_via_spacing_v2.py',
         'digital_continuous_escape_options_v4.py', 'digital_visibility_escape.py',
         'digital_multilayer_escape_routes_v4.py', 'digital_native_spacing_search_v4.py',
         'digital_continuous_via_bridges.py', 'digital_native_spacing_search_v3.py',
         'digital_native_spacing_search_v2.py', 'route_nf_surface.py', 'nf_minimum_logic.py',
         'nf_pin_escape_routes.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')]
    receipt = dict(source_sha256={str(p): sha(p) for p in paths}, attempts=attempts,
                   candidate_emitted=bool(selected), removed_uuids=sorted(REMOVED),
                   all_displaced_copper_requires_reconnection=True, native_rules_relaxed=False,
                   length_bounds_are_not_electrical_acceptance=True, fabrication_released=False)
    out = ROOT/'staging/digital-led35-dac-full-detour-01'
    out.mkdir(exist_ok=False)
    if selected:
        board = copy.deepcopy(original)
        for n in removed:
            board.remove(n)
        for r in selected:
            for face, path in r['runs']:
                for p, q in zip(path, path[1:]):
                    if math.dist(p, q) < 1e-7:
                        continue
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED35-DAC-full:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2],
                                  [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED35-DAC-full-via:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3],
                              [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
        dest = out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        receipt.update(candidate_PCB_sha256=sha(dest), routes=selected,
                       removed_objects=removed, geometry_delta=geometry_delta(original, board), native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Candidate emitted:', bool(selected), flush=True)


if __name__ == '__main__':
    run()
