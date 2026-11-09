"""Coordinate LED escapes after the signal-corridor rework."""
import argparse
import itertools
import json
import math
import uuid
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_array
from shapely.geometry import LineString, Point

import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.route_nf_surface as surface
from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen as ExistingViaScreen

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'staging/digital-led-fanout-02'
CAPTURE = ROOT/'staging/digital-signal-corridor-inputs/capture.json'


def run():
    global CAPTURE, OUT
    parser=argparse.ArgumentParser();parser.add_argument('--capture',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    for value in [args.capture,args.label]:assert value and all(c.isalnum() or c in '-_' for c in value)
    CAPTURE=ROOT/'staging'/args.capture/'capture.json';OUT=ROOT/'staging'/args.label
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(Path(p)) == h for p, h in capture['source_sha256'].items())
    source = next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board = read_sexpr(source.read_text())
    initial, count = sexpr(board), len(board)
    surface.WIDTH = layers.WIDTH = .2
    surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
    screen = ExistingViaScreen(capture, signal_layers=surface.SIGNAL_LAYERS)
    objects={o['uuid']:o for o in capture['objects']}
    open_nets={objects[ids[0]]['net'] for ids in capture['groups'].values()}
    pads = [o for o in capture['objects'] if o['kind'] == 'PAD' and o['net'] in open_nets
            and o['net'].startswith('/LED/LED_') and o['ref'].startswith('U300')]
    assert 0 < len(pads) <= 96
    groups = {}
    for pad in pads:
        groups.setdefault((pad['ref'], int(pad['pin']) > 16), []).append(pad)
    records, selected, missing = [], [], []
    for bank, bank_pads in sorted(groups.items()):
        candidates = []
        domains = []
        for pad in sorted(bank_pads, key=lambda p: int(p['pin'])):
            x, y = pad['position_mm']
            sign = 1 if bank[1] else -1
            options = []
            for offset, dy in itertools.product(
                    [1.25, 1.75, 2.25, 2.75, 3.25, 3.75, 4.25, 5.25, 6.25],
                    [0, -.3, .3, -.65, .65, -1.3, 1.3, -1.95, 1.95]):
                target = (x+sign*offset, y+dy)
                path = [(x, y), (x+sign*1.1, y), target]
                if not screen.legal(pad['net'], 'F.Cu', path) or not screen.via_legal(pad['net'], target):
                    continue
                line = LineString(path)
                options.append(dict(ref=pad['ref'], pin=pad['pin'], net=pad['net'],
                                    points_mm=path, via_mm=target, length_mm=line.length,
                                    line=line, point=Point(target), offset=offset, dy=dy))
            # Include both straight tiers and bent escapes in the bounded domain.
            options.sort(key=lambda r: (abs(r['dy']) > .31, r['length_mm'], r['offset'], r['dy']))
            # Retain all legal candidates; longer escapes can unblock adjacent pins.
            domains.append(dict(ref=pad['ref'], pin=pad['pin'], net=pad['net'],
                                candidate_indices=list(range(len(candidates), len(candidates)+len(options)))))
            candidates += options
        if not candidates:
            missing += domains
            records.append(dict(bank=bank,candidate_count=0,escaped_pins=0,domains=domains))
            continue
        constraints = [r['candidate_indices'] for r in domains if r['candidate_indices']]
        for i, left in enumerate(candidates):
            for j in range(i+1, len(candidates)):
                right = candidates[j]
                if left['net'] == right['net']:
                    continue
                if (left['point'].distance(right['point']) <= .86
                        or left['line'].distance(right['line']) <= .41
                        or left['point'].distance(right['line']) <= .61
                        or right['point'].distance(left['line']) <= .61):
                    constraints.append([i, j])
        rr, cc = [], []
        for row, indices in enumerate(constraints):
            rr.extend([row]*len(indices))
            cc.extend(indices)
        matrix = coo_array((np.ones(len(rr)), (np.array(rr, dtype=np.int32), np.array(cc, dtype=np.int32))),
                           shape=(len(constraints), len(candidates))).tocsc()
        result = milp(c=np.array([-1000+r['length_mm'] for r in candidates]),
                      integrality=np.ones(len(candidates)), bounds=Bounds(0, 1),
                      constraints=LinearConstraint(matrix, -np.inf, 1),
                      options=dict(time_limit=8, mip_rel_gap=.0001))
        assert result.x is not None, (bank, result.message)
        chosen = [r for r, value in zip(candidates, result.x) if value > .5]
        assert len({r['pin'] for r in chosen}) == len(chosen)
        for row in chosen:
            net, path, target = row['net'], row['points_mm'], row['via_mm']
            assert screen.legal(net, 'F.Cu', path) and screen.via_legal(net, target)
            screen.added.append((net, 'F.Cu', row['line']))
            screen.new_vias.append((net, target))
            for p, q in zip(path, path[1:]):
                uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DC:fanout01:{sha(CAPTURE)}:{net}:{p}:{q}'))
                board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2],
                              [a('layer'), 'F.Cu'], [a('net'), net], [a('uuid'), uid]])
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DC:fanoutvia01:{sha(CAPTURE)}:{net}:{target}'))
            board.append([a('via'), [a('at'), *target], [a('size'), .6], [a('drill'), .3],
                          [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), net], [a('uuid'), uid]])
            selected.append({k: v for k, v in row.items() if k not in {'line', 'point'}})
        chosen_pins = {r['pin'] for r in chosen}
        missing += [r for r in domains if r['pin'] not in chosen_pins]
        records.append(dict(bank=bank, candidate_count=len(candidates), constraint_count=len(constraints),
                            domains=domains, escaped_pins=len(chosen), solver_status=int(result.status),
                            solver_message=result.message, mip_gap=float(result.mip_gap)))
        print(bank, 'escaped', len(chosen), 'of remaining', result.message, flush=True)
    assert sexpr(board[:count]) == initial
    OUT.mkdir(exist_ok=False)
    pcb = OUT/source.name
    pcb.write_text(sexpr(board)+'\n')
    paths = [CAPTURE, source, Path(__file__), ROOT/'digital_via_spacing_v2.py', ROOT/'nf_softstart_joint_screen.py',
             ROOT/'nf_softstart_cell_routes.py', ROOT/'nf_minimum_logic.py', ROOT/'route_nf_surface.py']
    (OUT/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in paths}, candidate_PCB_sha256=sha(pcb),
        width_mm=.2, via_size_drill_mm=[.6, .3], selected_escapes=selected,
        unescaped_pins=missing, banks=records, input_geometry_exact=True,
        native_checks_pending=True, complete_signal_routes=False, fabrication_released=False), indent=2)+'\n')
    print('Coordinated escapes:', len(selected), 'new escapes; deferred', len(missing))


if __name__ == '__main__':
    run()
