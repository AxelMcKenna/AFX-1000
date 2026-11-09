"""Restore the seven displaced returns and join three nearby LED pulldowns."""
import json
import uuid
from pathlib import Path
from shapely.geometry import LineString

from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_power_finish import Screen

ROOT = Path(__file__).resolve().parent
CAPTURE = ROOT/'staging/digital-escape-repack-inputs-262/capture.json'
OUT = ROOT/'staging/digital-corridor-returns-01'


def run():
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(Path(p)) == h for p, h in capture['source_sha256'].items())
    source = next(Path(p) for p in capture['source_sha256'] if p.endswith('.kicad_pcb'))
    board = read_sexpr(source.read_text())
    initial, count = sexpr(board), len(board)
    screen = Screen(capture)
    pads = {(o['ref'],o['pin']):o for o in capture['objects'] if o['kind']=='PAD'}
    vias = {tuple(o['position_mm']):o for o in capture['objects'] if o['kind']=='PCB_VIA'}
    records = []

    def add(net, path, width, owner, target):
        assert screen.legal(net, 'B.Cu', path, width), (owner, path)
        for p, q in zip(path, path[1:]):
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f'AFX:DC:corridor-return01:{sha(CAPTURE)}:{net}:{p}:{q}'))
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],
                          [a('layer'),'B.Cu'],[a('net'),net],[a('uuid'),ident]])
        screen.added.append((net,'B.Cu',LineString(path),width))
        records.append(dict(net=net, layer='B.Cu', points_mm=path, width_mm=width,
                            length_mm=LineString(path).length, owner=owner,target=target))

    for ref, target in [('R1004',(55.75,31.85)),('R3003',(80.5,20)),
                        ('R1005',(40.5,20)),('R3019',(35.5,31.85)),
                        ('R3020',(32.75,31.85)),('R3021',(32.75,31.85))]:
        pad = pads[ref,'2']
        assert pad['net'] == vias[target]['net'] == 'AGND'
        add('AGND',[pad['position_mm'],target],.3,[ref,'2'],dict(via_uuid=vias[target]['uuid']))
    assert pads['R1003','2']['net'] == pads['R1005','2']['net'] == 'AGND'
    add('AGND',[pads['R1003','2']['position_mm'],pads['R1005','2']['position_mm']],.3,
        ['R1003','2'],dict(pad=['R1005','2']))
    for ref, series in [('R3019','R1012'),('R3020','R1011'),('R3021','R1010')]:
        p, q = pads[ref,'1'], pads[series,'2']
        assert p['net'] == q['net']
        add(p['net'],[p['position_mm'],q['position_mm']],.2,[ref,'1'],dict(pad=[series,'2']))
    assert sexpr(board[:count]) == initial
    OUT.mkdir(exist_ok=False)
    dest = OUT/source.name
    dest.write_text(sexpr(board)+'\n')
    inputs = [CAPTURE,source,Path(__file__),ROOT/'digital_power_finish.py']
    (OUT/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),
        routes=records,no_vias_added_or_removed=True,native_checks_pending=True,
        return_noise_current_and_timing_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Restored seven ground returns and connected three local LED pulldowns')


if __name__ == '__main__':
    run()
