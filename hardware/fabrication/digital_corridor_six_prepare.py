"""Add one signal and one ground layer to the coordinated four-layer trial."""
import copy
import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import geometry_delta, sha

ROOT = Path(__file__).resolve().parent


def run():
    source = ROOT/'staging/digital-coordinated-native-01/digital_core.kicad_pcb'
    board = read_sexpr(source.read_text())
    original = copy.deepcopy(board)
    layers = first(board, 'layers')
    back = next(n for n in layers[1:] if n[1] == 'B.Cu')
    i = layers.index(back)
    layers[i:i] = [[a(8), 'In3.Cu', a('signal')], [a(10), 'In4.Cu', a('power')]]
    zone = copy.deepcopy(next(z for z in children(board, 'zone') if first(z, 'layer')[1] == 'In1.Cu'))
    zone = [n for n in zone if not isinstance(n, list) or n[0] not in ('filled_polygon', 'filled_areas_thickness')]
    first(zone, 'layer')[1] = 'In4.Cu'
    first(zone, 'uuid')[1] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'AFX:DC:coordinated6:'+sha(source)))
    board.append(zone)
    delta = geometry_delta(original, board)
    for tag in ('footprint', 'segment', 'via'):
        assert not any(delta[tag][key] for key in ('added', 'removed', 'changed'))
    assert len(delta['zone']['added']) == 1
    assert not delta['zone']['removed'] and not delta['zone']['changed']
    out = ROOT/'staging/digital-coordinated-six-01'
    out.mkdir(exist_ok=False)
    pcb = out/source.name
    pcb.write_text(sexpr(board)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in (source, Path(__file__))}, candidate_PCB_sha256=sha(pcb),
        geometry_delta=delta, added_signal_layer='In3.Cu', added_ground_layer='In4.Cu',
        original_footprints_and_copper_exact=True, physical_stack_accepted=False,
        native_checks_pending=True, fabrication_released=False), indent=2)+'\n')


if __name__ == '__main__':
    run()
