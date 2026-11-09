"""Replay both shortened nets together before emitting a combined candidate."""
import argparse
import copy
import json
import math
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta
from hardware.fabrication.digital_serial1_joint_repair import ROOT, FACES, SERIAL
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

CONTROL = '/CONTROLS/CONTROL_30'


def center_vertices(screen, route, existing_vias):
    """Join same-face graph edges and center nearby vertices on their own vias."""
    runs, changes = [], []
    for face, path in copy.deepcopy(route['runs']):
        if runs and runs[-1][0] == face and math.dist(runs[-1][1][-1], path[0]) < 1e-7:
            runs[-1][1].extend(path[1:])
        else:
            runs.append([face, path])
    via_points = [*existing_vias, *route['new_vias_mm']]
    for face, path in runs:
        for i in range(1, len(path)-1):
            nearby = [p for p in via_points if 1e-7 < math.dist(path[i], p) < .400001]
            if not nearby:
                continue
            p = min(nearby, key=lambda p: math.dist(path[i], p))
            proposed = [path[i-1], p, path[i+1]]
            proposed = [v for j, v in enumerate(proposed) if j == 0 or math.dist(v, proposed[j-1]) > 1e-7]
            if len(proposed) > 1 and screen.legal(route['net'], face, proposed):
                changes.append(dict(face=face, before=path[i], after=p))
                path[i] = list(p)
        path[:] = [p for i, p in enumerate(path) if i == 0 or math.dist(p, path[i-1]) > 1e-7]
    result = copy.deepcopy(route)
    result['runs'] = runs
    return result, changes


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--control', default='digital-control30-costed-restoration-01')
    parser.add_argument('--label', default='digital-combined-costed-routes-01')
    args = parser.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in s) for s in (args.control, args.label))
    cp = ROOT/'staging/digital-serial1-closed-inputs-30/capture.json'
    recipes = [ROOT/'staging'/n/'construction.json' for n in ('digital-serial1-costed-restoration-03', args.control)]
    cap = json.loads(cp.read_text())
    records = [json.loads(p.read_text()) for p in recipes]
    for record in [cap, *records]:
        assert all(sha(Path(p)) == h for p, h in record['source_sha256'].items())
    assert all(r['candidate_emitted'] for r in records)
    routes = [copy.deepcopy(r['proposal']) for r in records]
    assert [r['net'] for r in routes] == [SERIAL, CONTROL]
    removed = set().union(*(r['removed_uuids'] for r in records))
    trim = None
    control = routes[1]
    pad = next(o for o in cap['objects'] if o.get('ref') == 'U2003' and o.get('pin') == '3')
    assert pad['net'] == CONTROL and pad['position_mm'] == [88.85, 39.715]
    if control['runs'][-1][0] == 'B.Cu' and math.dist(control['runs'][-1][1][-1], (87.5, 39.7)) < 1e-7:
        trim = dict(before=control['runs'][-1][1][-1], after=pad['position_mm'])
        control['runs'][-1][1][-1] = pad['position_mm']
        removed.update(o['uuid'] for o in cap['objects'] if o['net'] == CONTROL and o['kind'] in ('PCB_TRACK', 'PCB_VIA'))
    work = copy.deepcopy(cap)
    work['objects'] = [o for o in cap['objects'] if o['uuid'] not in removed]
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .001
    surface.SIGNAL_LAYERS = FACES
    screen = CloseMarginViaScreen(work, signal_layers=FACES)
    normalization, normalized = [], []
    for r in routes:
        vias = [o['position_mm'] for o in work['objects'] if o['kind'] == 'PCB_VIA' and o['net'] == r['net']]
        r, changes = center_vertices(screen, r, vias)
        normalization += [dict(net=r['net'], **c) for c in changes]
        normalized.append(r)
    checked, rejected = [], []
    for r in normalized:
        bad_runs = [i for i, (f, path) in enumerate(r['runs']) if not screen.legal(r['net'], f, path)]
        bad_vias = [p for p in r['new_vias_mm'] if not screen.via_legal(r['net'], p)]
        if bad_runs or bad_vias:
            rejected.append(dict(net=r['net'], failed_run_indices=bad_runs, failed_vias=bad_vias))
            break
        checked.append(add(screen, r['net'], dict(runs=r['runs'], vias=r['new_vias_mm'])))
    pcb = next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'))
    before = read_sexpr(pcb.read_text())
    paths = [cp, *recipes, pcb, Path(__file__)] + [ROOT/n for n in ('audit_candidate.py', 'digital_serial1_joint_repair.py', 'digital_via_spacing_close_margin.py', 'digital_via_spacing_v2.py', 'digital_xlat_escape_repair.py', 'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_softstart_joint_screen.py', 'nf_softstart_cell_routes.py')] + [ROOT.parent/'electronics/common/sexpr.py']
    out = ROOT/'staging'/args.label
    out.mkdir(exist_ok=False)
    result = dict(source_sha256={str(p): sha(p) for p in paths}, candidate_emitted=len(checked) == 2,
        removed_uuids=sorted(removed), routes=checked, rejected=rejected, control_receiving_tail_trim=trim,
        centered_vertices=normalization, native_rules_relaxed=False, fabrication_released=False)
    if len(checked) == 2:
        board = copy.deepcopy(before)
        retired = [n for tag in ('segment', 'via') for n in children(board, tag) if first(n, 'uuid')[1] in removed]
        assert len(retired) == len(removed)
        assert all(first(n, 'net')[1] in (SERIAL, CONTROL) for n in retired)
        for n in retired:
            board.remove(n)
        for r in checked:
            for face, path in r['runs']:
                for p, q in zip(path, path[1:]):
                    if math.dist(p, q) < 1e-7:
                        continue
                    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:COMBINED-COSTED:{sha(cp)}:{args.label}:{r["net"]}:{face}:{p}:{q}'))
                    board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2], [a('layer'), face], [a('net'), r['net']], [a('uuid'), uid]])
            for p in r['new_vias_mm']:
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:COMBINED-COSTED-VIA:{sha(cp)}:{args.label}:{r["net"]}:{p}'))
                board.append([a('via'), [a('at'), *p], [a('size'), .6], [a('drill'), .3], [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), r['net']], [a('uuid'), uid]])
        dest = out/pcb.name
        dest.write_text(sexpr(board)+'\n')
        result.update(candidate_PCB_sha256=sha(dest), removed_objects=retired, geometry_delta=geometry_delta(before, board), native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Combined candidate:', result['candidate_emitted'], 'rejections', rejected, 'centered', len(normalization), flush=True)


if __name__ == '__main__':
    run()
