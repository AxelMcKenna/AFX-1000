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
    rp = ROOT / 'staging/digital-led30-whole-trunks-01/construction.json'
    cap, prior = [json.loads(p.read_text()) for p in (cp, rp)]
    for record in (cap, prior):
        assert all(sha(Path(p)) == h for p,h in record['source_sha256'].items())
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    net = '/LED/LED_30'; latch = '/LED/LATCH_5V'
    assert prior['attempts'][0]['net'] == net
    raw = prior['attempts'][0]['search']['route']
    surface.WIDTH = layers.WIDTH = .2; surface.MARGIN = .001; surface.SIGNAL_LAYERS = FACES
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in prior['removed_uuids']]
    broad = CloseMarginViaScreen(work, signal_layers=FACES)
    normal, centered = center_vertices(broad, dict(net=net, runs=raw['runs'], new_vias_mm=raw['vias']), [])
    simple = simplify(broad, net, dict(runs=normal['runs'], vias=normal['new_vias_mm']))
    cuts = []
    for o in cap['objects']:
        if o['uuid'] not in prior['removed_uuids']:
            continue
        gs = {f:surface.shape(ps) for f,ps in o['layers'].items() if ps}
        hit = any(LineString(p).distance(gs[f]) <= .3015 for f,p in simple['runs'] if f in gs)
        hit |= any(Point(p).distance(g) <= .501 for p in simple['vias'] for g in gs.values())
        if hit:
            cuts.append(o)
    assert len(cuts) == 14 and {o['net'] for o in cuts} == {latch}
    assert sum(o['kind'] == 'PCB_VIA' for o in cuts) == 1
    removed = {o['uuid'] for o in cuts}
    work = copy.deepcopy(cap); work['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed]
    base = CloseMarginViaScreen(work, signal_layers=FACES); screen = branch(base)
    selected = [add(screen, net, simple)]; attempts = []
    anchors = [('F.Cu', (26.9,21.3)), ('In3.Cu',(33.3,18.2)), ('F.Cu',(33.2,9.3))]
    contacts = [anchors[0]]
    deadline = time.monotonic() + 110
    for dest in anchors[1:]:
        own_vias = [p for n,p in screen.vias + screen.new_vias if n == latch]
        result = route(screen, latch, contacts, [dest], min(deadline,time.monotonic()+50),
                       max_refinements=100, via_candidates=own_vias)
        attempts.append(dict(net=latch,destination=dest,search=result))
        print('Restore LATCH boundary',dest,'found',bool(result['route']),flush=True)
        if not result['route']:
            break
        raw = result['route']
        normal, changes = center_vertices(screen,dict(net=latch,runs=raw['runs'],new_vias_mm=raw['vias']),own_vias)
        centered.extend(changes)
        r = add(screen,latch,simplify(screen,latch,dict(runs=normal['runs'],vias=normal['new_vias_mm'])))
        selected.append(r); contacts.append(dest)
        contacts.extend((f,p) for p in r['new_vias_mm'] for f in FACES)
    emitted = len(selected) == 3
    pruned = []
    if emitted:
        selected,pruned = prune_single_face_vias(work,selected)
        replay = branch(base)
        for r in selected:
            add(replay,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    out = ROOT / 'staging/digital-led30-minimal-latch-01'
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
