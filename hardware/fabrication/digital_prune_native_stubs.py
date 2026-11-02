"""Remove only explicitly reported, newly added dangling copper in a variant."""
import argparse
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, native_evidence_errors

ROOT = Path(__file__).resolve().parent


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--tracks-only', action='store_true')
    args = parser.parse_args()
    for value in [args.source, args.label]:
        assert value and all(c.isalnum() or c in '-_' for c in value)
    source = ROOT/'staging'/args.source
    pcb = source/'digital_core.kicad_pcb'
    review = json.loads((source/'review.json').read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
    drc = json.loads((source/'drc.json').read_text())
    assert all(v['severity'] == 'warning' and v['type'] in
               {'via_dangling', 'track_dangling'} for v in drc['violations'])
    base = ROOT/'staging/digital-distribution-native-02/digital_core.kicad_pcb'
    original = read_sexpr(base.read_text())
    protected = {first(n, 'uuid')[1] for tag in ['segment', 'via']
                 for n in children(original, tag)}
    ids = {i['uuid'] for v in drc['violations']
           if not args.tracks_only or v['type'] == 'track_dangling'
           for i in v['items']}
    assert ids and not ids & protected
    board = read_sexpr(pcb.read_text())
    removed = [n for tag in ['segment', 'via'] for n in children(board, tag)
               if first(n, 'uuid')[1] in ids]
    assert len(removed) == len(ids)
    for n in removed:
        board.remove(n)
    out = ROOT/'staging'/args.label
    out.mkdir(exist_ok=False)
    dest = out/pcb.name
    dest.write_text(sexpr(board)+'\n')
    inputs = [pcb, pcb.with_suffix('.kicad_pro'), source/'review.json',
              source/'drc.json', base, Path(__file__)]
    (out/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs},
        candidate_PCB_sha256=sha(dest), removed_native_reported_objects=removed,
        original_DC03_copper_preserved=True, native_checks_pending=True,
        fabrication_released=False), indent=2)+'\n')
    print('Removed', len(removed), 'native-reported dangling objects')


if __name__ == '__main__':
    run()
