"""Repair one router clearance without relaxing the 0.2 mm native rule."""
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent


def run():
    source = ROOT/'staging/rail-monitor-reserved-routed-native-01/rail_monitor.kicad_pcb'
    drc = source.parent/'drc.json'
    report = json.loads(drc.read_text())
    assert len(report['violations']) == 1 and report['violations'][0]['type'] == 'clearance'
    assert not report['unconnected_items'] and not report['schematic_parity']
    tree = read_sexpr(source.read_text())
    ident = 'dcb6884f-5f17-438c-9969-6fa0b0539a3c'
    via = next(v for v in children(tree,'via') if first(v,'uuid')[1] == ident)
    assert first(via,'net')[-1] == '/LOWV_WINDOWS_OK'
    pos = first(via,'at')
    old = [float(v) for v in pos[1:3]]
    assert old == [70.7969,57.7704]
    pos[2] = 57.8004
    changed = []
    for track in children(tree,'segment'):
        if first(track,'net') != first(via,'net'):
            continue
        for tag in ('start','end'):
            endpoint = first(track,tag)
            if [float(v) for v in endpoint[1:3]] == old:
                endpoint[1:3] = pos[1:3]
                changed.append(str(first(track,'uuid')[1]))
    assert changed
    output = ROOT/'staging/rail-monitor-reserved-finish-01'
    output.mkdir(exist_ok=False)
    pcb = output/source.name
    pcb.write_text(sexpr(tree)+'\n')
    (output/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in (source,drc,Path(__file__))},
        candidate_PCB_sha256=sha(pcb),via_uuid=ident,old_position_mm=old,
        new_position_mm=pos[1:3],attached_track_UUIDs=changed,
        native_checks_pending=True,fabrication_released=False),indent=2)+'\n')


if __name__ == '__main__':
    run()
