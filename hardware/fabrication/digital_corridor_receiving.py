"""Recheck trial component envelopes against the retained conditional AP04 context."""
import json
from pathlib import Path

from hardware.electronics.common.sexpr import read_sexpr
from hardware.fabrication.assembly_layout import component_boxes, intersects
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def run():
    ap = ROOT/'staging/assembly-layout-04/allocation.json'
    allocation = json.loads(ap.read_text())
    assert all(sha(REPO/p) == h for p, h in allocation['source_sha256'].items())
    out = ROOT/'staging/digital-coordinated-native-01'
    pcb = out/'digital_core.kicad_pcb'
    boxes = component_boxes(read_sexpr(pcb.read_text()), [184,44,7], True)
    context = allocation['retained_context_boxes']
    collisions = [[b[0], o[0]] for b in boxes for o in context if intersects(b[1:7], o[1:7])]
    floor = [b[0] for b in boxes if b[3] < 2.8]
    assert not collisions and not floor
    assert len(boxes) == 143 and sum(not b[0].startswith('H') for b in boxes) == 138
    inputs = [ap, pcb, Path(__file__), ROOT/'assembly_layout.py']
    with (out/'conditional-assembly-review.json').open('x') as f:
        json.dump(dict(source_sha256={str(p): sha(p) for p in inputs},
                       component_boxes=boxes, conditional_context_collisions=collisions,
                       conditional_floor_collisions=floor, electrical_component_count=138, mounting_holes=5,
                       full_current_unit_receiving_verified=False,
                       actual_part_heights_mates_harnesses_and_supports_accepted=False,
                       fabrication_released=False), f, indent=2)
        f.write('\n')
    print('138 trial components and five mounts clear retained conditional context and floor')


if __name__ == '__main__':
    run()
