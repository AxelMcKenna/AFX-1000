"""Serialize the declared translation from native S-expression tokens.

JSON preserves the footprint values but not the parser's keyword token class.
Rebuild the translated footprint from its native source, prove value equality
to the declared pose, and leave every routed segment and via unchanged.
"""
import copy
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta

ROOT = Path(__file__).resolve().parent


def repair(before, candidate, pose):
    def resistor(tree):
        return next(f for f in children(tree, 'footprint')
                    if any(p[1:3] == ['Reference', 'R3015'] for p in children(f, 'property')))
    assert pose['position_mm'] == [75.25, 21.] and pose['angle'] == 0 and pose['side'] == 'B'
    source = resistor(before)
    assert list(map(float, first(source, 'at')[1:3])) == [75., 21.]
    assert first(source, 'layer')[1] == 'B.Cu'
    moved = copy.deepcopy(source)
    first(moved, 'at')[1:3] = [75.25, 21.]
    assert moved == pose['footprint'], 'Only the declared translation is allowed'
    assert resistor(candidate) == read_sexpr(sexpr(pose['footprint']))
    moved = read_sexpr(sexpr(moved))
    corrected = copy.deepcopy(candidate)
    index = corrected.index(resistor(corrected))
    corrected[index] = moved
    assert corrected == candidate, 'Token repair may not change any parsed value'
    return corrected


def run():
    stage = ROOT/'staging/digital-serial1-combined-restoration-06'
    rp = stage/'construction.json'
    raw = stage/'digital_core.kicad_pcb'
    parent = ROOT/'staging/digital-serial1-source-preparation-native-01/digital_core.kicad_pcb'
    recipe = json.loads(rp.read_text())
    assert recipe['candidate_emitted'] and sha(raw) == recipe['candidate_PCB_sha256']
    assert all(sha(Path(p)) == h for p, h in recipe['source_sha256'].items())
    before, candidate = [read_sexpr(p.read_text()) for p in (parent, raw)]
    corrected = repair(before, candidate, recipe['component_move'])
    assert geometry_delta(before, corrected) == recipe['geometry_delta']
    out = ROOT/'staging/digital-serial1-combined-restoration-07'
    out.mkdir(exist_ok=False)
    dest = out/raw.name
    dest.write_text(sexpr(corrected)+'\n')
    assert read_sexpr(dest.read_text()) == corrected
    result = copy.deepcopy(recipe)
    paths = [rp, raw, parent, Path(__file__), ROOT/'audit_candidate.py', ROOT.parent/'electronics/common/sexpr.py', ROOT.parents[1]/'tests/tooling/test_serial1_native_footprint_repair.py']
    result.update(source_sha256={str(p): sha(p) for p in paths}, candidate_PCB_sha256=sha(dest),
                  footprint_keyword_tokens_restored_from_native_source=True,
                  parsed_geometry_values_unchanged=True, native_checks_pending=True)
    (out/'construction.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Native footprint tokens restored; all parsed geometry values unchanged')


if __name__ == '__main__':
    run()
