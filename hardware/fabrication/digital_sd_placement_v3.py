"""Place SD series resistors beside the Seed pins in an isolated native variant."""
import json
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import sha, native_evidence_errors

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'staging/digital-led-fanout-native-01'
OUT = ROOT/'staging/digital-sd-placement-03'


def run():
    assert sys.platform == 'linux', 'Mac CAD remains disabled'
    import pcbnew
    pcb = SOURCE/'digital_core.kicad_pcb'
    review = json.loads((SOURCE/'review.json').read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
    assert all(v['type'] == 'via_dangling' and v['severity'] == 'warning'
               for v in json.loads((SOURCE/'drc.json').read_text())['violations'])
    board = pcbnew.LoadBoard(str(pcb))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    moves = []
    for number in [1010,1011,1012,1013,1015,1016,1017,1018,1019,1020]:
        ref = f'R{number}'
        f = fps[ref]
        source_pad = next(p for p in f.Pads() if p.GetNumber() == '1')
        seed = next(p for p in fps['U1001'].Pads() if p.GetNetname() == source_pad.GetNetname())
        x = seed.GetPosition().x/1e6
        before = dict(position_mm=[f.GetPosition().x/1e6, f.GetPosition().y/1e6],
                      orientation_deg=f.GetOrientationDegrees(), flipped=f.IsFlipped())
        if not f.IsFlipped():
            f.Flip(f.GetPosition(), False)
        f.SetOrientationDegrees(90)
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(38.5)))
        pads = {p.GetNumber(): p for p in f.Pads()}
        if pads['1'].GetPosition().y < pads['2'].GetPosition().y:
            f.SetOrientationDegrees(-90)
        pads = {p.GetNumber(): p for p in f.Pads()}
        seed = next(p for p in fps['U1001'].Pads() if p.GetNetname() == pads['1'].GetNetname())
        assert seed.GetPosition().x == pads['1'].GetPosition().x
        assert seed.GetPosition().y > pads['1'].GetPosition().y > pads['2'].GetPosition().y
        moves.append(dict(ref=ref, before=before, after_position_mm=[x, 38.5],
                          after_orientation_deg=f.GetOrientationDegrees(), after_side='B',
                          pads={k: dict(net=p.GetNetname(), xy_mm=[p.GetPosition().x/1e6, p.GetPosition().y/1e6]) for k,p in pads.items()}))
    # R1039 is unconnected in this source. Reuse the vacated, accepted R1018
    # 0805 site to clear the SD corridor; retain R1039's own identity and nets.
    f = fps['R1039']
    before = dict(position_mm=[f.GetPosition().x/1e6, f.GetPosition().y/1e6],
                  orientation_deg=f.GetOrientationDegrees(), flipped=f.IsFlipped())
    if not f.IsFlipped():
        f.Flip(f.GetPosition(), False)
    f.SetOrientationDegrees(0)
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(57), pcbnew.FromMM(49)))
    moves.append(dict(ref='R1039', before=before, after_position_mm=[57,49],
                      after_orientation_deg=0, after_side='B', reason='Reuse vacated R1018 site to clear SD corridor'))
    OUT.mkdir(exist_ok=False)
    dest = OUT/pcb.name
    assert pcbnew.SaveBoard(str(dest), board)
    inputs = [pcb, pcb.with_suffix('.kicad_pro'), SOURCE/'review.json', SOURCE/'drc.json', Path(__file__)]
    (OUT/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs}, candidate_PCB_sha256=sha(dest),
        component_moves=moves, native_checks_pending=True,
        physical_receiving_and_timing_qualified=False, fabrication_released=False), indent=2)+'\n')
    print('Moved ten SD/LED series resistors beside their source pins; R1039 clears the bus corridor')


if __name__ == '__main__':
    run()
