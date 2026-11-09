"""Rebuild LATCH and MCU_PERMIT between all actual pads around a new LED30 route."""
import argparse
import copy
import json
import math
import time
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_screen_branch import branch
from hardware.fabrication.digital_costed_region_route_v3 import route
from hardware.fabrication.digital_combine_costed_routes import center_vertices
from hardware.fabrication.digital_route_shortcuts import simplify
from hardware.fabrication.digital_native_route_cleanup import prune_single_face_vias
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=('30', '31'), required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    cp = ROOT / 'staging/digital-led16-closed-inputs-27/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    blockers = {'/LED/LATCH_5V', '/PROCESSOR/MCU_PERMIT'}
    target = '/LED/LED_' + args.target
    retired_objects = [o for o in cap['objects'] if o['net'] in blockers and o['kind'] in ('PCB_TRACK', 'PCB_VIA')]
    removed = {o['uuid'] for o in retired_objects}
    assert removed and not any(o['net'] == target and o['kind'] in ('PCB_TRACK', 'PCB_VIA') for o in cap['objects'])
    seeds = [o['position_mm'] for o in retired_objects if o['kind'] == 'PCB_VIA']
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .001
    surface.SIGNAL_LAYERS = FACES
    base = CloseMarginViaScreen(work, signal_layers=FACES)
    screen = branch(base)
    selected, attempts, centered = [], [], []
    deadline = time.monotonic() + 300
    complete = True
    for net in (target, '/PROCESSOR/MCU_PERMIT', '/LED/LATCH_5V'):
        pads = [o for o in cap['objects'] if o['net'] == net and o['kind'] == 'PAD']
        assert len(pads) == (2 if net == target else 3 if net.endswith('MCU_PERMIT') else 6)
        pads.sort(key=lambda o: (not any(o['drill_mm']), o['position_mm']))
        connected = [pads.pop(0)]
        contacts = [(f, connected[0]['position_mm']) for f in FACES if connected[0]['layers'].get(f)]
        while pads:
            dest = min(pads, key=lambda p: min(math.dist(p['position_mm'], q['position_mm']) for q in connected))
            result = route(screen, net, contacts,
                           [(f, dest['position_mm']) for f in FACES if dest['layers'].get(f)],
                           min(deadline, time.monotonic() + 40), max_refinements=60,
                           via_candidates=seeds)
            attempts.append(dict(net=net, destination=[dest['ref'],dest['pin']], search=result))
            print(net, dest['ref'], dest['pin'], 'route found', bool(result['route']), flush=True)
            if not result['route']:
                complete = False
                break
            raw = result['route']
            own_vias = [p for n,p in screen.vias + screen.new_vias if n == net]
            normal, changes = center_vertices(screen, dict(net=net, runs=raw['runs'], new_vias_mm=raw['vias']), own_vias)
            centered.append(dict(net=net, changes=changes))
            simple = simplify(screen, net, dict(runs=normal['runs'], vias=normal['new_vias_mm']))
            selected.append(add(screen, net, simple))
            connected.append(dest); pads.remove(dest)
            contacts.extend((f, dest['position_mm']) for f in FACES if dest['layers'].get(f))
            contacts.extend((f,p) for p in selected[-1]['new_vias_mm'] for f in FACES)
        if not complete:
            break
    emitted = complete and len(selected) == 8
    pruned = []
    if emitted:
        selected, pruned = prune_single_face_vias(work, selected)
        replay = branch(base)
        for r in selected:
            add(replay, r['net'], dict(runs=r['runs'], vias=r['new_vias_mm']))
    out = ROOT / 'staging' / args.label
    out.mkdir(exist_ok=False)
    names = ('audit_candidate.py', 'digital_serial1_joint_repair.py', 'digital_via_spacing_close_margin.py',
             'digital_via_spacing_v2.py', 'digital_screen_branch.py', 'digital_costed_region_route.py',
             'digital_costed_region_route_v2.py', 'digital_costed_region_route_v3.py', 'digital_polygon_path.py',
             'digital_region_reachability.py', 'digital_planned_region_screen.py', 'digital_combine_costed_routes.py',
             'digital_route_shortcuts.py', 'digital_native_route_cleanup.py', 'digital_xlat_escape_repair.py',
             'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')
    paths = [cp, pcb, Path(__file__), ROOT.parent / 'electronics/common/sexpr.py'] + [ROOT / n for n in names]
    report = dict(source_sha256={str(p): sha(p) for p in paths}, candidate_emitted=emitted,
                  attempts=attempts, removed_uuids=sorted(removed), routes=selected if emitted else [],
                  centered_vertices=centered, pruned_unused_vias=pruned, expected_opens=26,
                  native_rules_relaxed=False, fabrication_released=False)
    if emitted:
        before = read_sexpr(pcb.read_text())
        board = copy.deepcopy(before)
        retired = [n for tag in ('segment', 'via') for n in children(board, tag) if first(n, 'uuid')[1] in removed]
        assert len(retired) == len(removed)
        for n in retired:
            board.remove(n)
        for r in selected:
            for face, path in r['runs']:
                for p, q in zip(path, path[1:]):
                    if math.dist(p, q) < 1e-7:
                        continue
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED30-TRUNKS:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED30-TRUNKS-VIA:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
        dest = out / pcb.name
        dest.write_text(sexpr(board) + '\n')
        report.update(candidate_PCB_sha256=sha(dest), removed_objects=retired,
                      geometry_delta=geometry_delta(before, board), native_checks_pending=True)
    (out / 'construction.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Complete candidate:', emitted, flush=True)


if __name__ == '__main__':
    run()
