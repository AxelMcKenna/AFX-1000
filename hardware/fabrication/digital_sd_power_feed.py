"""Move the SD power feed outside the reserved signal bundle."""
import json
import uuid
from pathlib import Path
from shapely.geometry import LineString

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_power_finish import Screen

ROOT = Path(__file__).resolve().parent
CAPTURE = ROOT/'staging/digital-sd-placement-inputs-v3/capture.json'
OUT = ROOT/'staging/digital-sd-power-feed-01'


def run():
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(Path(p)) == h for p, h in capture['source_sha256'].items())
    source = next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board = read_sexpr(source.read_text())
    removed_ids = {'5af17068-5c97-5f01-b630-d11ab7f513ae',
                   '35e40a59-3d33-57ee-ba30-1cf00ea84f65',
                   '680eb7c0-e169-5013-8cae-d159c0709149',
                   '17450eca-f541-59c5-ac33-d975f017b7b4'}
    removed = [n for n in children(board, 'segment') if first(n, 'uuid')[1] in removed_ids]
    assert len(removed) == 4
    assert all(first(n, 'net')[1] == 'V3V3_IO' and first(n, 'layer')[1] == 'F.Cu' for n in removed)
    for n in removed:
        board.remove(n)
    capture['objects'] = [o for o in capture['objects'] if o['uuid'] not in removed_ids]
    pads = {(o['ref'], o['pin']): o for o in capture['objects'] if o['kind'] == 'PAD'}
    seed, header = pads['U1001', '38'], pads['J1012', '2']
    assert seed['net'] == header['net'] == 'V3V3_IO'
    path = [seed['position_mm'], (15.08, 28.5), (8.5, 28.5),
            (8.5, 40.2), (65.54, 40.2), header['position_mm']]
    screen = Screen(capture)
    assert screen.legal('V3V3_IO', 'F.Cu', path, .8)
    for p, q in zip(path, path[1:]):
        ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DC:SDpower01:{sha(CAPTURE)}:{p}:{q}'))
        board.append([a('segment'), [a('start'), *p], [a('end'), *q], [a('width'), .8],
                      [a('layer'), 'F.Cu'], [a('net'), 'V3V3_IO'], [a('uuid'), ident]])
    OUT.mkdir(exist_ok=False)
    dest = OUT/source.name
    dest.write_text(sexpr(board)+'\n')
    inputs = [CAPTURE, source, Path(__file__), ROOT/'digital_power_finish.py']
    (OUT/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs}, candidate_PCB_sha256=sha(dest),
        removed_source_branch=removed, new_feed=dict(net='V3V3_IO', layer='F.Cu',
            points_mm=path, width_mm=.8, length_mm=LineString(path).length,
            source=['U1001','38'], destination=['J1012','2']),
        no_vias_added_or_removed=True, native_checks_pending=True,
        source_current_voltage_drop_transient_and_thermal_qualified=False,
        fabrication_released=False), indent=2)+'\n')
    print('SD power feed:', round(LineString(path).length, 3), 'mm at 0.8 mm width; native checks pending')


if __name__ == '__main__':
    run()
