"""Shift J1001 within its screened reserve and retain both bulk-cap connections."""
import argparse
import json
import sys
from pathlib import Path

from hardware.fabrication.audit_candidate import native_evidence_errors, sha

ROOT = Path(__file__).resolve().parent


def run():
    assert sys.platform == 'linux', 'Mac CAD remains disabled'
    import pcbnew
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    for value in (args.source, args.label):
        assert value and all(c.isalnum() or c in '-_' for c in value)
    source = ROOT/'staging'/args.source
    pcb = source/'digital_core.kicad_pcb'
    review = json.loads((source/'review.json').read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
    assert review['status']['counts']['schematic_parity'] == review['status']['counts']['erc'] == 0
    assert not json.loads((source/'drc.json').read_text())['violations']
    board = pcbnew.LoadBoard(str(pcb))
    f = next(f for f in board.GetFootprints() if f.GetReference() == 'J1001')
    assert [f.GetPosition().x, f.GetPosition().y] == [32000000,14000000]
    assert f.GetOrientationDegrees() == 0 and not f.IsFlipped()
    targets = {'0f17361b-836d-54a5-958a-0322dbb84109', '315da06e-7073-5520-939e-6c630b774fff'}
    edits = []
    for t in board.GetTracks():
        if t.m_Uuid.AsString() not in targets:
            continue
        assert t.GetClass() == 'PCB_TRACK' and t.GetNetname() == '5V_DIG'
        assert t.GetLayer() == pcbnew.B_Cu and t.GetWidth() == 200000
        assert [t.GetEnd().x, t.GetEnd().y] == [32000000,14000000]
        before = [t.GetEnd().x/1e6, t.GetEnd().y/1e6]
        t.SetEnd(pcbnew.VECTOR2I(31200000,14000000))
        edits.append(dict(uuid=t.m_Uuid.AsString(), end_before_mm=before, end_after_mm=[31.2,14]))
    assert len(edits) == 2
    f.SetPosition(pcbnew.VECTOR2I(31200000,14000000))
    out = ROOT/'staging'/args.label
    out.mkdir(exist_ok=False)
    dest = out/pcb.name
    assert pcbnew.SaveBoard(str(dest), board)
    inputs = [pcb, pcb.with_suffix('.kicad_pro'), source/'review.json', source/'drc.json', Path(__file__)]
    (out/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs}, candidate_PCB_sha256=sha(dest),
        component_moves=[dict(ref='J1001', before_mm=[32,14], after_mm=[31.2,14])],
        changed_bulk_tracks=edits, native_checks_pending=True,
        actual_harness_and_assembly_acceptance=False, fabrication_released=False), indent=2)+'\n')
    print('J1001 shifted left 0.8 mm; both bulk-cap trace ends follow the input pad')


if __name__ == '__main__':
    run()
