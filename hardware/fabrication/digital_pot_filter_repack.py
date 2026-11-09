"""Translate only R1040 and reconnect its raw/ADC nets with existing rules intact."""
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
from hardware.fabrication.digital_xlat_escape_repair import route, add
from hardware.fabrication.digital_latch_supply_repack import polys
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search

ROOT = Path(__file__).resolve().parent
RAW, ADC = '/PROCESSOR/POT_RAW_09', '/PROCESSOR/POT_ADC_09'
SPUR = '3d975814-3478-589e-852c-ac1c628c708f'


def run():
    cp = ROOT/'staging/digital-exact-regions-inputs-41/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    original = read_sexpr(pcb.read_text())
    fps = {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f for f in children(original, 'footprint')}
    old = fps['R1040']
    assert list(map(float, first(old, 'at')[1:3])) == [70, 30] and first(old, 'layer')[1] == 'F.Cu'
    removed = [n for n in children(original, 'segment') if first(n, 'uuid')[1] == SPUR]
    assert len(removed) == 1 and first(removed[0], 'net')[1] == RAW
    pads = [o for o in cap['objects'] if o.get('ref') == 'R1040']
    assert len(pads) == 2 and {o['net'] for o in pads} == {RAW, ADC}
    base = copy.deepcopy(cap)
    base['objects'] = [o for o in base['objects'] if o.get('ref') != 'R1040' and o['uuid'] != SPUR]
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    surface.SIGNAL_LAYERS = search.LAYERS = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    profile = Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
    courts = {r: box(*courtyard(f, 'F.CrtYd')) for r, f in fps.items() if r != 'R1040' and first(f, 'layer')[1] == 'F.Cu'}
    oldcourt = box(*courtyard(old, 'F.CrtYd'))
    through = [box(*pad_box(f, p, .5)) for r, f in fps.items() if first(f, 'layer')[1] != 'F.Cu' for p in children(f, 'pad') if p[2] == 'thru_hole']
    mounts = [box(x-3.6,y-3.6,x+3.6,y+3.6) for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]]
    geometries = [(o['net'], surface.shape(o['layers']['F.Cu'])) for o in base['objects'] if o['layers'].get('F.Cu')]
    tree = STRtree([g for n, g in geometries])
    screen = DigitalViaScreen(base, signal_layers=surface.SIGNAL_LAYERS)
    drilled = [(Point(p), r) for _, p, r, _ in screen.drilled]
    contacts = {n: {(f, tuple(p)) for o in base['objects'] if o['net'] == n for f in search.LAYERS if o['layers'].get(f) for p in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else [])} for n in (RAW, ADC)}
    poses, counts = [], dict(screened=0, mechanical=0, pad_clear=0)
    for x, y in itertools.product([54+i*.25 for i in range(89)], [24+i*.25 for i in range(65)]):
        counts['screened'] += 1
        dx, dy = x-70, y-30
        cc = translate(oldcourt, dx, dy)
        if not profile.covers(cc) or cc.distance(profile.boundary) < .5-1e-8 or any(cc.distance(m) < .15-1e-8 for m in mounts):
            continue
        if any(cc.distance(g) < .3-1e-8 for g in courts.values()) or any(cc.intersection(g).area > 1e-10 for g in through):
            continue
        counts['mechanical'] += 1
        moved = []
        for p in pads:
            g = translate(surface.shape(p['layers']['F.Cu']), dx, dy)
            if any(n != p['net'] and g.distance(h) < .21-1e-8 for i in tree.query(g.buffer(.22)) for n, h in [geometries[int(i)]]):
                break
            if any(q.distance(g)-r < .16-1e-8 for q, r in drilled):
                break
            row = copy.deepcopy(p)
            row['position_mm'] = [p['position_mm'][0]+dx, p['position_mm'][1]+dy]
            row['layers'] = {'F.Cu': polys(g)}
            moved.append(row)
        if len(moved) == 2:
            counts['pad_clear'] += 1
            score = sum(min(math.dist(p['position_mm'], q) for f, q in contacts[p['net']]) for p in moved)
            poses.append(dict(position_mm=[x,y], pads=moved, score=score))
    poses.sort(key=lambda p: p['score'])
    print('Placement screen', counts, flush=True)
    attempts, selected = [], None
    deadline = time.monotonic()+600
    for pose in poses[:32]:
        if time.monotonic() > deadline:
            break
        work = copy.deepcopy(base)
        work['objects'] += pose['pads']
        screen = DigitalViaScreen(work, signal_layers=surface.SIGNAL_LAYERS)
        routes = []
        attempt = dict(position_mm=pose['position_mm'], routes=[])
        attempts.append(attempt)
        for net, max_length in ((RAW, 20), (ADC, 70)):
            p = next(p for p in pose['pads'] if p['net'] == net)
            result = route(screen, net, 'F.Cu', p['position_mm'], contacts[net], min(deadline, time.monotonic()+30))
            length = sum(LineString(p).length for f, p in result['runs']) if result else None
            attempt['routes'].append(dict(net=net, found=bool(result), length_mm=length))
            print(attempt, flush=True)
            if result is None or length > max_length:
                break
            routes.append(add(screen, net, result))
        if len(routes) == 2:
            selected = pose, routes
            break
    paths = [cp, pcb, Path(__file__)]+[ROOT/n for n in ('digital_xlat_escape_repair.py','digital_latch_supply_repack.py','digital_core_layout.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v4.py','digital_multilayer_escape_routes_v4.py','digital_visibility_escape.py','route_nf_surface.py','nf_minimum_logic.py','nf_pin_escape_routes.py','digital_native_spacing_search_v3.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    receipt = dict(source_sha256={str(p): sha(p) for p in paths}, placement_counts=counts, attempts=attempts,
                   candidate_emitted=bool(selected), fabrication_released=False)
    out = ROOT/'staging/digital-pot-filter-repack-01'
    out.mkdir(exist_ok=False)
    if selected:
        pose, routes = selected
        board = copy.deepcopy(original)
        moved = next(f for f in children(board, 'footprint') if first(f, 'uuid')[1] == first(old, 'uuid')[1])
        first(moved, 'at')[1:3] = pose['position_mm']
        board.remove(next(n for n in children(board, 'segment') if first(n, 'uuid')[1] == SPUR))
        for r in routes:
            for face, path in r['runs']:
                for p, q in zip(path, path[1:]):
                    if math.dist(p,q) < 1e-7:
                        continue
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:pot-filter:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),r['net']],[a('uuid'),uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:pot-filter-via:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),r['net']],[a('uuid'),uid]])
        dest = out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        receipt.update(candidate_PCB_sha256=sha(dest), removed_objects=removed, removed_uuids=[SPUR], routes=routes,
                       component_move=dict(ref='R1040',before_mm=[70.,30.],after_mm=pose['position_mm'],side='F',rotation_unchanged=True),
                       geometry_delta=geometry_delta(original,board),native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Completed; candidate emitted:', bool(selected), flush=True)


if __name__ == '__main__':
    run()
