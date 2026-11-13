"""Bind complete mounting evidence before proposing the selected manifest."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE = Path(__file__).resolve().parent

def run():
    results = json.loads((HERE/'full-results.json').read_text())
    assert len(results['results']) == 57 and all(r['passed'] for r in results['results'])
    w.assert_current({'sources': results['snapshot_sha256']})
    candidate = json.loads((HERE/'hardware-split-candidate.json').read_text())
    checks = {q['id']:q for q in candidate['checks']}
    partition = json.loads((HERE/'split-coverage.json').read_text())
    w.assert_current({'sources': partition['source_sha256']})
    for group in partition['coverage']:
        original = group['original']; actual = [checks[q] for q in group['replacement_checks']]
        assert all(q['left'] == original['left'] and q['expect'] == original['expect'] for q in actual)
        assert sum((q['right'] for q in actual),[]) == original['right']
    seats = json.loads((HERE/'seat-review.json').read_text())
    w.assert_current({'sources': seats['snapshot_sha256']})
    w.assert_current({'sources': seats['reviewer_sha256']})
    assert len(seats['results']) == 3
    assert all(r['exact_planar_seat'] and not r['native_empty_pass'] for r in seats['results'])
    registry = json.loads((HERE/'hardware-registry.json').read_text())
    registry['source_sha256'].update({w.relative(p):w.sha(p) for p in [
        Path(__file__), HERE/'hardware-registry.json', HERE/'hardware-split-candidate.json',
        HERE/'full-results.json', HERE/'hardware-split-results.json', HERE/'split-coverage.json',
        HERE/'seat-review.json', HERE/'check_seats.py', HERE/'shell-result.json', HERE/'shell.stl']})
    for row in seats['results']:
        for name in ['result.json','geometry.stl','native.log']:
            p = HERE/row['check']/name
            registry['source_sha256'][w.relative(p)] = w.sha(p)
        q = row['identity']['definition']
        registry['intentional_contacts'].append(dict(components=q['left']+q['right'],
            reason='Exact raw seating plane at Z'+str(row['expected_seat_z'])+'; nonempty witness retained, physical fit not certified',
            evidence=w.relative(HERE/row['check']/'result.json'), blanket_pair_exclusion=False))
    (HERE/'selected-registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    candidate['registries']=[w.relative(HERE/'selected-registry.json')]
    candidate['unresolved']=[x for x in candidate['unresolved'] if not x.startswith('Unselected r26 hardware candidate:')]
    candidate['unresolved'].append('R26 sourced nominal touch fasteners, two nut-pocket extensions and upper receiving envelope are modeled. Printed/PCB tolerances, fastener conformity, recessed nut insertion, torque, creep and retention remain unqualified; raw seats are not empty passes.')
    (HERE/'selected-candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    _,parts,ks,_=w.load_manifest(HERE/'selected-candidate.json')
    assert len(parts)==71 and len(ks)==57
    print('71roles/57checks; complete operand partition and three exact seat witnesses bound')

if __name__ == '__main__':run()
