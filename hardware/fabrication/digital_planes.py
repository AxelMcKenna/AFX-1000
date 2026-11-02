"""Add reserved DC02 ground/5 V planes without altering existing geometry."""
import json
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a, read_sexpr, sexpr, children
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent

def run():
    source = ROOT/'staging/digital-local-cell-native-01/digital_core.kicad_pcb'
    capture = ROOT/'staging/digital-local-cell-inputs-427/capture.json'
    data = json.loads(capture.read_text())
    assert all(sha(Path(p)) == h for p,h in data['source_sha256'].items())
    board = read_sexpr(source.read_text())
    assert not children(board,'zone')
    original, count = sexpr(board), len(board)
    outline = data['outline'][0]['outer']
    for net,layer in [('AGND','In1.Cu'),('5V_DIG','In2.Cu')]:
        ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:DC:plane:{sha(source)}:{layer}'))
        board.append([a('zone'),[a('net'),net],[a('layer'),layer],[a('uuid'),ident],
            [a('hatch'),a('edge'),.5],[a('connect_pads'),[a('clearance'),.2]],
            [a('min_thickness'),.25],[a('filled_areas_thickness'),a('no')],
            [a('fill'),a('yes'),[a('thermal_gap'),.25],[a('thermal_bridge_width'),.5],
             [a('island_removal_mode'),0]],
            [a('polygon'),[a('pts'),*[[a('xy'),*p] for p in outline]]]])
    assert sexpr(board[:count]) == original
    out = ROOT/'staging/digital-planes-01'
    out.mkdir(exist_ok=False)
    dest = out/source.name
    dest.write_text(sexpr(board)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p):sha(p) for p in [source,capture,Path(__file__)]},
        candidate_PCB_sha256=sha(dest),original_authored_geometry_exact=True,
        planes={'In1.Cu':'AGND','In2.Cu':'5V_DIG'},thermal_spoke_width_mm=.5,
        stack_and_current_capacity_qualified=False,signal_reference_review_complete=False,
        native_checks_pending=True,fabrication_released=False),indent=2)+'\n')

if __name__ == '__main__':run()
