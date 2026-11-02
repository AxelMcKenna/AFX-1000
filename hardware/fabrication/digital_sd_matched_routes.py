"""Route the SD carrier bus with one via per signal and bounded length spread."""
import json
import math
import uuid
from pathlib import Path

from shapely.geometry import LineString

import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.route_nf_surface as surface
from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.nf_softstart_joint_screen import ExistingViaScreen

ROOT = Path(__file__).resolve().parent
CAPTURE = ROOT/'staging/digital-signal-corridor-inputs/capture.json'
OUT = ROOT/'staging/digital-sd-matched-routes-01'


def run():
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(Path(p)) == h for p, h in capture['source_sha256'].items())
    source = next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board = read_sexpr(source.read_text())
    initial, count = sexpr(board), len(board)
    surface.WIDTH = layers.WIDTH = .2
    screen = ExistingViaScreen(capture, signal_layers=('F.Cu', 'B.Cu'))
    pads = {(o['ref'], o['pin']): o for o in capture['objects'] if o['kind'] == 'PAD'}
    records = []

    def add(net, face, path):
        path = [tuple(p) for i, p in enumerate(path) if i == 0 or tuple(p) != tuple(path[i-1])]
        assert len(path) >= 2 and screen.legal(net, face, path), (net, face, path)
        for p, q in zip(path, path[1:]):
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DC:SDmatched01:{sha(CAPTURE)}:{net}:{face}:{p}:{q}'))
            board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .2],
                          [a('layer'), face], [a('net'), net], [a('uuid'), ident]])
        screen.added.append((net, face, LineString(path)))
        records.append(dict(net=net, layer=face, points_mm=path, length_mm=LineString(path).length))

    for number in [1010, 1011, 1012, 1013, 1015, 1016, 1017, 1018, 1019, 1020]:
        resistor = pads[f'R{number}', '1']
        seed = next(o for (r, p), o in pads.items() if r == 'U1001' and o['net'] == resistor['net'])
        assert math.isclose(seed['position_mm'][0], resistor['position_mm'][0], abs_tol=1e-7)
        add(resistor['net'], 'B.Cu', [seed['position_mm'], resistor['position_mm']])
    signals = ['D0', 'D1', 'D2', 'D3', 'CMD', 'CLK']
    vias = []
    for index, name in enumerate(signals):
        net = '/PROCESSOR/SDMMC_'+name
        resistor = pads[f'R{1015+index}', '2']
        header = next(o for (r, p), o in pads.items() if r == 'J1012' and o['net'] == net)
        assert resistor['net'] == net
        x, _ = resistor['position_mm']
        lane = 35.9-.65*index
        via = (x, lane)
        assert screen.via_legal(net, via), (net, via)
        add(net, 'B.Cu', [resistor['position_mm'], via])
        target_x, target_y = header['position_mm']
        turn = (target_x-(target_y-lane), lane)
        path = [via]
        if name == 'D0':
            path += [(x, lane+3.2), (x+1, lane+3.2), (x+1, lane),
                     (x+2, lane), (x+2, lane+3.2), (x+3, lane+3.2), (x+3, lane)]
        elif name == 'D1':
            path += [(x, lane+3.5), (x+1, lane+3.5), (x+1, lane)]
        if name == 'CMD':
            path += [(68.3,33.3),(72.4,37.4),(79.0,37.4),(79.0,40.5),header['position_mm']]
        elif name == 'CLK':
            path += [(68.35,32.65),(71.4,35.7),(80.78,35.7),header['position_mm']]
        elif name == 'D0':
            path += [(turn[0]+1.2, lane), (target_x, target_y-1.2), header['position_mm']]
        else:
            path += [turn, header['position_mm']]
        add(net, 'F.Cu', path)
        ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DC:SDmatchedvia01:{sha(CAPTURE)}:{net}:{via}'))
        board.append([a('via'), [a('at'), *via], [a('size'), .6], [a('drill'), .3],
                      [a('layers'), 'F.Cu', 'B.Cu'], [a('net'), net], [a('uuid'), ident]])
        screen.new_vias.append((net, via))
        vias.append(dict(net=net, xy_mm=via, uuid=ident))
    totals = [dict(signal=name, carrier_planar_mm=sum(r['length_mm'] for r in records
                    if r['net'] in ['/PROCESSOR/SDMMC_'+name, '/PROCESSOR/SDMMC_'+name+'_SRC']),
                   via_count=1) for name in signals]
    spread = max(r['carrier_planar_mm'] for r in totals)-min(r['carrier_planar_mm'] for r in totals)
    assert spread < 7 and max(r['carrier_planar_mm'] for r in totals) < 80
    assert sexpr(board[:count]) == initial
    OUT.mkdir(exist_ok=False)
    dest = OUT/source.name
    dest.write_text(sexpr(board)+'\n')
    inputs = [CAPTURE, source, Path(__file__), ROOT/'nf_softstart_joint_screen.py',
              ROOT/'nf_softstart_cell_routes.py', ROOT/'nf_minimum_logic.py', ROOT/'route_nf_surface.py']
    (OUT/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs}, candidate_PCB_sha256=sha(dest),
        routes=records, added_vias=vias, carrier_path_totals=totals, planar_spread_mm=spread,
        all_source_geometry_retained=True, width_mm=.2, native_checks_pending=True,
        Seed_socket_card_harness_loading_and_impedance_qualified=False,
        fabrication_released=False), indent=2)+'\n')
    print('SD carrier spread', round(spread, 3), 'mm; one via each; native checks pending')


if __name__ == '__main__':
    run()
