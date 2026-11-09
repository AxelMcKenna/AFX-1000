"""Connect LED_BLANK and completely restore a displaced CODEC_RUN branch."""
import copy
import itertools
import json
import math
import time
import uuid
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from hardware.fabrication.digital_polygon_path import route as polygon_route
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
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
LED = 'LED_BLANK'
POT = 'CODEC_RUN'
REMOVED = {'e62678be-4939-5f0b-8633-4a4e50f062b1'}


def run():
    cp = ROOT/'staging/digital-led35-dac-pot-inputs-33/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p,h in cap['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original = read_sexpr(pcb.read_text())
    removed = [n for n in children(original,'segment') if first(n,'uuid')[1] in REMOVED]
    assert len(removed) == 1
    assert all(first(n,'net')[1] == POT and first(n,'layer')[1] == 'B.Cu' and float(first(n,'width')[1]) == .2 for n in removed)
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in work['objects'] if o['uuid'] not in REMOVED]
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    surface.SIGNAL_LAYERS = search.LAYERS = ('F.Cu','In3.Cu','In5.Cu','B.Cu')
    repair.search = search
    start = next(o for o in work['objects'] if o.get('ref') == 'R1013' and o['net'] == LED)
    contacts = {(f,tuple(p)) for o in work['objects'] if o['net'] == LED and o['uuid'] != start['uuid'] for f in search.LAYERS if o['layers'].get(f) for p in [o['position_mm']]+([o['end_mm']] if o['kind']=='PCB_TRACK' else [])}
    previous_path = ROOT/'staging/digital-blank-codec-repair-01/construction.json'
    previous = json.loads(previous_path.read_text())
    assert all(sha(Path(p)) == h for p,h in previous['source_sha256'].items())
    attempts,selected = [],None
    deadline = time.monotonic()+180
    for order in ((LED,POT),):
        screen = DigitalViaScreen(work,signal_layers=search.LAYERS)
        routes = []
        attempt = dict(order=order,routes=[])
        attempts.append(attempt)
        for net in order:
            if net == LED:
                result = previous['attempts'][0]['routes'][0]['proposed_route']
                bound = 100
            else:
                result = previous['attempts'][0]['routes'][1]['proposed_route']
                bound = 80
            length = sum(LineString(p).length for f,p in result['runs']) if result else None
            attempt['routes'].append(dict(net=net,found=bool(result),length_mm=length,search_bound_mm=bound,proposed_route=result))
            print('Net',net,'found',bool(result),'length',length,flush=True)
            if result is None or length > bound:
                break
            routes.append(add(screen,net,result))
        if len(routes) == 2:
            selected = routes
            break
    paths = [cp, pcb, previous_path, Path(__file__)] + [ROOT/n for n in
        ('digital_planned_region_screen.py', 'digital_polygon_path.py', 'digital_region_reachability.py', 'audit_candidate.py', 'digital_xlat_escape_repair.py', 'digital_via_spacing_v2.py',
         'digital_continuous_escape_options_v4.py', 'digital_visibility_escape.py',
         'digital_multilayer_escape_routes_v4.py', 'digital_native_spacing_search_v4.py',
         'digital_continuous_via_bridges.py', 'digital_native_spacing_search_v3.py',
         'digital_native_spacing_search_v2.py', 'route_nf_surface.py', 'nf_minimum_logic.py',
         'nf_pin_escape_routes.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')]
    receipt = dict(source_sha256={str(p): sha(p) for p in paths}, attempts=attempts,
                   candidate_emitted=bool(selected), removed_uuids=sorted(REMOVED),
                   all_displaced_copper_requires_reconnection=True, native_rules_relaxed=False,
                   expanded_CODEC_RUN_search_bound_mm=80, original_search_bound_mm=65,
                   expanded_bound_reason="Evaluate complete joint routing with a 33.812666 mm CODEC_RUN section increase; no electrical acceptance inferred",
                   length_bounds_are_not_electrical_acceptance=True, fabrication_released=False)
    out = ROOT/'staging/digital-blank-codec-repair-02'
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
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:BLANK-CODEC:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2],
                                  [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:BLANK-CODEC-via:{sha(cp)}:{r["net"]}:{p}'))
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
