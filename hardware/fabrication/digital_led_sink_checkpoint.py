"""Combine two additive LED routing phases with exact intermediate geometry checks.

This records a construction chain, not electrical or fabrication acceptance.
The combined board still requires strict native and independent physical review.
"""
import copy
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha

ROOT = Path(__file__).resolve().parent


def additive_delta(before, after, recipe):
    delta = geometry_delta(before, after)
    assert delta['other_root_geometry_exact']
    for tag in ('footprint', 'zone'):
        assert delta[tag] == dict(added=[], removed=[], changed=[])
    for tag, key in (('segment', 'added_segments'), ('via', 'added_vias')):
        assert not delta[tag]['removed'] and not delta[tag]['changed']
        assert len(delta[tag]['added']) == recipe[key]
    nets = {r['net'] for r in recipe['routes']}
    assert all(n.startswith('/LED/LED_') for n in nets)
    for tag in ('segment', 'via'):
        added = set(delta[tag]['added'])
        for node in children(after, tag):
            if first(node, 'uuid')[1] not in added:
                continue
            assert first(node, 'net')[1] in nets
            if tag == 'segment':
                assert float(first(node, 'width')[1]) == .2
                assert first(node, 'layer')[1] in ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
            else:
                assert float(first(node, 'size')[1]) == .6
                assert float(first(node, 'drill')[1]) == .3
    return delta


def run():
    parent = ROOT/'staging/digital-xlat-bridge-native-01/digital_core.kicad_pcb'
    first_dir = ROOT/'staging/digital-post-xlat-bridges-routes-01'
    intermediate = ROOT/'staging/digital-led49-bridge-native-01'
    second_dir = ROOT/'staging/digital-led-sink-complete-routes-01'
    capture = ROOT/'staging/digital-led49-bridge-inputs-36/capture.json'
    paths = [Path(__file__), parent, capture, intermediate/'digital_core.kicad_pcb', intermediate/'review.json']
    recipes = []
    sources = {}
    for directory in (first_dir, second_dir):
        recipe_path = directory/'construction.json'
        recipe = json.loads(recipe_path.read_text())
        for path, digest in recipe['source_sha256'].items():
            assert sha(Path(path)) == digest, path
            assert path not in sources or sources[path] == digest
            sources[path] = digest
        pcb = directory/'digital_core.kicad_pcb'
        assert sha(pcb) == recipe['candidate_PCB_sha256']
        paths += [recipe_path, pcb]
        recipes.append(recipe)
    cap = json.loads(capture.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    assert str(intermediate/'digital_core.kicad_pcb') in cap['source_sha256']
    sources.update(cap['source_sha256'])
    review = json.loads((intermediate/'review.json').read_text())
    assert not native_evidence_errors(intermediate/'digital_core.kicad_pro', review)
    counts = review['status']['counts']
    assert counts['violations'] == counts['schematic_parity'] == counts['erc'] == 0
    assert counts['unconnected_items'] == 36
    boards = [read_sexpr(p.read_text()) for p in
              (parent, first_dir/'digital_core.kicad_pcb', intermediate/'digital_core.kicad_pcb', second_dir/'digital_core.kicad_pcb')]
    additive_delta(boards[0], boards[1], recipes[0])
    native_delta = geometry_delta(boards[1], boards[2])
    assert native_delta['other_root_geometry_exact']
    for tag in ('footprint', 'zone', 'segment', 'via'):
        assert native_delta[tag] == dict(added=[], removed=[], changed=[])
    additive_delta(boards[2], boards[3], recipes[1])
    assert [r['net'] for r in recipes[0]['routes']] == ['/LED/LED_49']
    assert recipes[1]['routes'], 'No second-phase joins to combine'
    assert not ({r['net'] for r in recipes[0]['routes']} & {r['net'] for r in recipes[1]['routes']})
    combined = dict(routes=copy.deepcopy(recipes[0]['routes']+recipes[1]['routes']),
                    added_segments=sum(r['added_segments'] for r in recipes),
                    added_vias=sum(r['added_vias'] for r in recipes))
    combined['geometry_delta'] = additive_delta(boards[0], boards[3], combined)
    output = ROOT/'staging/digital-led-sink-checkpoint-01'
    output.mkdir(exist_ok=False)
    pcb = output/'digital_core.kicad_pcb'
    pcb.write_bytes((second_dir/pcb.name).read_bytes())
    sources.update({str(p): sha(p) for p in paths})
    combined.update(source_sha256=sources, candidate_PCB_sha256=sha(pcb),
                    source_geometry_exact=True, signal_layers=['F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu'],
                    width_mm=.2, attempts=recipes[0]['attempts']+recipes[1]['attempts'],
                    phase_length_targets_mm=[r['maximum_emitted_route_length_mm'] for r in recipes],
                    length_targets_are_not_electrical_acceptance=True,
                    native_checks_pending=True, physical_qualified=False, fabrication_released=False)
    (output/'construction.json').write_text(json.dumps(combined, indent=2)+'\n')
    print('Combined', len(combined['routes']), 'LED joins with exact intermediate geometry')


if __name__ == '__main__':
    run()
