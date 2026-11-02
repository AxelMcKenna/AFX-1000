"""Clear signal corridors by relocating three pulldowns and retiring six ground spurs."""
import json
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, native_evidence_errors

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'staging/digital-sd-power-native-01'
OUT = ROOT/'staging/digital-escape-repack-01'


def run():
    assert sys.platform == 'linux', 'Mac CAD remains disabled'
    import pcbnew
    pcb = SOURCE/'digital_core.kicad_pcb'
    review = json.loads((SOURCE/'review.json').read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
    assert all(v['type'] == 'via_dangling' and v['severity'] == 'warning'
               for v in json.loads((SOURCE/'drc.json').read_text())['violations'])
    tree = read_sexpr(pcb.read_text())
    tracks = {str(first(t,'uuid')[1]): t for tag in ['segment','via'] for t in children(tree,tag)}
    base = ROOT/'staging/digital-distribution-native-02/digital_core.kicad_pcb'
    fanout = ROOT/'staging/digital-led-fanout-01/digital_core.kicad_pcb'
    def copper_ids(path):
        tree = read_sexpr(path.read_text())
        return {str(first(n, 'uuid')[1]) for tag in ['segment', 'via'] for n in children(tree, tag)}
    trial_ids = copper_ids(fanout)-copper_ids(base)
    assert len(trial_ids) == 234 and trial_ids <= tracks.keys()
    for uid in trial_ids:
        tree.remove(tracks[uid])
    escape_path = ROOT/'staging/digital-plane-escapes-01/construction.json'
    finish_path = ROOT/'staging/digital-power-finish-01/construction.json'
    owners = {'R1003', 'R1004', 'R3003', 'R3019', 'R3020', 'R3021'}
    branches = [r for r in json.loads(escape_path.read_text())['routes'] if r['owner']['ref'] in owners]
    assert len(branches) == 6
    branches += [r for r in json.loads(finish_path.read_text())['routes'] if r['owner']['ref'] == 'R1005']
    removed = []
    for row in branches:
        assert row['net'] == 'AGND'
        ids = []
        for p, q in zip(row['points_mm'], row['points_mm'][1:]):
            expected = {tuple(round(v*1e6) for v in p), tuple(round(v*1e6) for v in q)}
            matching = [t for t in children(tree,'segment')
                        if first(t,'net')[1] == 'AGND' and first(t,'layer')[1] == row['face']
                        and {tuple(round(float(v)*1e6) for v in first(t,tag)[1:3]) for tag in ['start','end']} == expected]
            assert len(matching) == 1, row
            t = matching[0]
            ids.append(str(first(t,'uuid')[1]))
            tree.remove(t)
        removed.append(dict(owner=row['owner'], removed_track_uuids=ids, old_branch=row))
    via_ids = {r['via_uuid'] for r in branches if 'via_uuid' in r}
    assert len(via_ids) == 6
    # Every direct track contact on these vias must be one of the retired spurs.
    for uid in via_ids:
        via = tracks[uid]
        xy = tuple(round(float(v)*1e6) for v in first(via,'at')[1:3])
        assert not any(xy in {tuple(round(float(v)*1e6) for v in first(t,tag)[1:3]) for tag in ['start','end']}
                       for t in children(tree,'segment')), uid
        tree.remove(via)
    OUT.mkdir(exist_ok=False)
    prepared = OUT/'prepared.kicad_pcb'
    prepared.write_text(sexpr(tree)+'\n')
    board = pcbnew.LoadBoard(str(prepared))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    moves = []
    for ref, series in [('R3019','R1012'),('R3020','R1011'),('R3021','R1010')]:
        f, resistor = fps[ref], fps[series]
        before = dict(position_mm=[f.GetPosition().x/1e6,f.GetPosition().y/1e6],
                      angle=f.GetOrientationDegrees(), flipped=f.IsFlipped())
        if not f.IsFlipped():
            f.Flip(f.GetPosition(), False)
        f.SetPosition(pcbnew.VECTOR2I(resistor.GetPosition().x, pcbnew.FromMM(35)))
        f.SetOrientationDegrees(90)
        pads = {p.GetNumber(): p for p in f.Pads()}
        if pads['1'].GetPosition().y < pads['2'].GetPosition().y:
            f.SetOrientationDegrees(-90)
        assert next(p for p in f.Pads() if p.GetNumber() == '1').GetNetname() == next(p for p in resistor.Pads() if p.GetNumber() == '2').GetNetname()
        moves.append(dict(ref=ref, before=before, after_position_mm=[f.GetPosition().x/1e6,35],
                          after_angle=f.GetOrientationDegrees(), after_side='B', paired_series=series))
    dest = OUT/pcb.name
    assert pcbnew.SaveBoard(str(dest), board)
    inputs = [pcb, pcb.with_suffix('.kicad_pro'), SOURCE/'review.json', base, fanout,
              escape_path, finish_path, prepared, Path(__file__)]
    (OUT/'construction.json').write_text(json.dumps(dict(
        source_sha256={str(p): sha(p) for p in inputs}, candidate_PCB_sha256=sha(dest),
        retired_trial_fanout_uuids=sorted(trial_ids), retired_ground_branches=removed,
        retired_ground_via_uuids=sorted(via_ids), component_moves=moves,
        seven_ground_pad_returns_must_be_restored=True,
        native_checks_pending=True, fabrication_released=False), indent=2)+'\n')
    print('Moved three pulldowns; retired six ground vias and old trial fanouts; seven returns await rerouting')


if __name__ == '__main__':
    run()
