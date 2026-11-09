"""Reconnect the three boundaries of the minimal LATCH cut around LED30."""
import argparse
import copy
import json
import math
import time
import uuid
from pathlib import Path
from shapely.geometry import LineString, Point

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
    cp = ROOT / 'staging/digital-led16-closed-inputs-27/capture.json'
    rp = ROOT / 'staging/digital-led30-inner-global-probe-01/diagnosis.json'
    cap, prior = [json.loads(p.read_text()) for p in (cp, rp)]
    for record in (cap, prior):
        assert all(sha(Path(p)) == h for p,h in record['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    net = '/LED/LED_30'; latch = '/LED/LATCH_5V'
    surface.WIDTH = layers.WIDTH = .2; surface.MARGIN = .001; surface.SIGNAL_LAYERS = FACES
    removed = set(prior['removed_uuids'])
    cuts = [o for o in cap['objects'] if o['uuid'] in removed]
    assert len(cuts) == 6 and {o['net'] for o in cuts} == {latch}
    assert sum(o['kind'] == 'PCB_VIA' for o in cuts) == 1
    work = copy.deepcopy(cap); work['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed]
    base = CloseMarginViaScreen(work, signal_layers=FACES); screen = branch(base)
    selected = []
    for r in prior['routes']:
        assert r['net'] == net
        selected.append(add(screen,net,dict(runs=r['runs'],vias=r['new_vias_mm'])))
    assert len(selected) == 2
    attempts = []; centered = []
    anchors = [(('F.Cu',(33.2,9.3)),('F.Cu',(35.9,3.9))),
               (('F.Cu',(29.3,19.3)),('In3.Cu',(33.3,18.2)))]
    deadline = time.monotonic() + 110
    for start,dest in anchors:
        own_vias = [p for n,p in screen.vias + screen.new_vias if n == latch]
        result = route(screen, latch, [start], [dest], min(deadline,time.monotonic()+50),
                       max_refinements=100, via_candidates=own_vias)
        attempts.append(dict(net=latch,start=start,destination=dest,search=result))
        print('Restore LATCH boundary',start,dest,'found',bool(result['route']),flush=True)
        if not result['route']:
            break
        raw = result['route']
        normal, changes = center_vertices(screen,dict(net=latch,runs=raw['runs'],new_vias_mm=raw['vias']),own_vias)
        centered.extend(changes)
        r = add(screen,latch,simplify(screen,latch,dict(runs=normal['runs'],vias=normal['new_vias_mm'])))
        selected.append(r)
    emitted = len(selected) == 4
    pruned = []
    if emitted:
        selected,pruned = prune_single_face_vias(work,selected)
        replay = branch(base)
        for r in selected:
            add(replay,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    out = ROOT / 'staging/digital-led30-minimal-latch-02'
    out.mkdir(exist_ok=False)
    names = ('audit_candidate.py', 'digital_serial1_joint_repair.py', 'digital_via_spacing_close_margin.py',
             'digital_via_spacing_v2.py', 'digital_screen_branch.py', 'digital_costed_region_route.py',
             'digital_costed_region_route_v2.py', 'digital_costed_region_route_v3.py', 'digital_polygon_path.py',
             'digital_region_reachability.py', 'digital_planned_region_screen.py', 'digital_combine_costed_routes.py',
             'digital_route_shortcuts.py', 'digital_native_route_cleanup.py', 'digital_xlat_escape_repair.py',
             'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')
    paths = [cp, rp, pcb, Path(__file__), ROOT.parent / 'electronics/common/sexpr.py'] + [ROOT / n for n in names]
    report = dict(source_sha256={str(p): sha(p) for p in paths}, candidate_emitted=emitted,
                  attempts=attempts, restoration_boundaries=anchors, removed_uuids=sorted(removed), routes=selected if emitted else [],
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
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED30-MINIMAL:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED30-MINIMAL-VIA:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
        dest = out / pcb.name
        dest.write_text(sexpr(board) + '\n')
        report.update(candidate_PCB_sha256=sha(dest), removed_objects=retired,
                      geometry_delta=geometry_delta(before, board), native_checks_pending=True)
    (out / 'construction.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Complete candidate:', emitted, flush=True)


if __name__ == '__main__':
    run()
