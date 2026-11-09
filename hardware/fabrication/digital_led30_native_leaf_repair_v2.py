"""Reconnect the native-isolated U3002 LATCH leaf after LED30 routing."""
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
import hardware.fabrication.nf_ct_leaf_cleanup as cleanup


def run():
    cp = ROOT / 'staging/digital-led30-connectivity-probe-inputs-27/capture.json'
    op = ROOT / 'staging/digital-led16-closed-inputs-27/capture.json'
    rp = ROOT / 'staging/digital-led30-minimal-latch-04/construction.json'
    cap, original, prior = [json.loads(p.read_text()) for p in (cp,op,rp)]
    for record in (cap,original,prior):
        assert all(sha(Path(p)) == h for p,h in record['source_sha256'].items())
    pcb = next(Path(p) for p in original['source_sha256'] if p.endswith('.kicad_pcb'))
    net = '/LED/LATCH_5V'
    source = next(o for o in cap['objects'] if o.get('ref') == 'U3002' and o.get('pin') == '30')
    groups = {o['group'] for o in cap['objects'] if o['net'] == net}
    assert len(groups) == 2 and None not in groups
    # Retain the existing native vias as usable contacts; their existing holes
    # must not be mistaken for sites where a new via must be drilled.
    trim = {'df5780b3-927d-5997-9bf4-602a99d6276a',
            '421957c2-bd01-5fd9-999f-fa39891efa05',
            '3fcb3824-9954-5532-a1fb-50f3692c3cd3'}
    leaves = [o for o in cap['objects'] if o['uuid'] in trim]
    active = [o for o in cap['objects'] if o['uuid'] not in trim]
    assert len(leaves) == 3 and all(o['net'] == net and o['kind'] == 'PCB_TRACK' for o in leaves)
    print('Retired native LATCH leaves:',len(leaves),flush=True)
    removed = set(prior['removed_uuids']) | {o['uuid'] for o in leaves}
    old_ids = {o['uuid'] for o in original['objects']}
    assert removed <= old_ids and len(removed) == len(prior['removed_uuids']) + len(leaves)
    work = copy.deepcopy(cap); work['objects'] = active
    surface.WIDTH = layers.WIDTH = .2; surface.MARGIN = .001; surface.SIGNAL_LAYERS = FACES
    screen = CloseMarginViaScreen(work,signal_layers=FACES)
    ends = sorted({(f,tuple(p)) for o in active if o['net'] == net and o['group'] != source['group']
                   for f in FACES if o['layers'].get(f)
                   for p in [o['position_mm']] + ([o['end_mm']] if 'end_mm' in o else [])})
    assert ends
    starts = sorted({(f,tuple(p)) for o in active if o['net'] == net and o['group'] == source['group']
                     for f in FACES if o['layers'].get(f)
                     for p in [o['position_mm']] + ([o['end_mm']] if 'end_mm' in o else [])})
    result = route(screen,net,starts,ends,time.monotonic()+110,max_refinements=160)
    attempts = [dict(net=net,native_source_group=source['group'],retained_group_targets=len(ends),native_source_contacts=len(starts),search=result)]
    selected = copy.deepcopy(prior['routes']); centered = []; pruned = []
    emitted = bool(result['route'])
    if emitted:
        raw = result['route']
        own_vias = [p for n,p in screen.vias if n == net]
        normal,centered = center_vertices(screen,dict(net=net,runs=raw['runs'],new_vias_mm=raw['vias']),own_vias)
        simple = simplify(screen,net,dict(runs=normal['runs'],vias=normal['new_vias_mm']))
        selected.append(add(screen,net,simple))
        replay_capture = copy.deepcopy(original)
        replay_capture['objects'] = [o for o in original['objects'] if o['uuid'] not in removed]
        selected,pruned = prune_single_face_vias(replay_capture,selected)
        replay = CloseMarginViaScreen(replay_capture,signal_layers=FACES)
        for r in selected:
            add(replay,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
        print('New LATCH leaf length:',selected[-1]['planar_length_mm'],flush=True)
    out = ROOT / 'staging/digital-led30-native-leaf-repair-02'
    out.mkdir(exist_ok=False)
    names = ('audit_candidate.py', 'digital_serial1_joint_repair.py', 'digital_via_spacing_close_margin.py',
             'digital_via_spacing_v2.py', 'digital_screen_branch.py', 'digital_costed_region_route.py',
             'digital_costed_region_route_v2.py', 'digital_costed_region_route_v3.py', 'digital_polygon_path.py',
             'digital_region_reachability.py', 'digital_planned_region_screen.py', 'digital_combine_costed_routes.py',
             'digital_route_shortcuts.py', 'digital_native_route_cleanup.py', 'digital_xlat_escape_repair.py',
             'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')
    paths = [cp, op, rp, pcb, ROOT/'nf_ct_leaf_cleanup.py', Path(__file__), ROOT.parent / 'electronics/common/sexpr.py'] + [ROOT / n for n in names]
    report = dict(source_sha256={str(p): sha(p) for p in paths}, candidate_emitted=emitted,
                  attempts=attempts, native_leaf_retirements=[o['uuid'] for o in leaves], removed_uuids=sorted(removed), routes=selected if emitted else [],
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
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED30-NATIVE-LEAF:{sha(cp)}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:LED30-NATIVE-LEAF-VIA:{sha(cp)}:{r["net"]}:{p}'))
                board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
        dest = out / pcb.name
        dest.write_text(sexpr(board) + '\n')
        report.update(candidate_PCB_sha256=sha(dest), removed_objects=retired,
                      geometry_delta=geometry_delta(before, board), native_checks_pending=True)
    (out / 'construction.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Complete candidate:', emitted, flush=True)


if __name__ == '__main__':
    run()
