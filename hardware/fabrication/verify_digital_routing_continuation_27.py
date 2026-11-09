"""Bind unsuccessful routing searches to the unchanged 27-open native board."""
import ast
import json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha, native_evidence_errors

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CASES = (
    ('digital-led13-led02-whole-01','construction.json'),
    ('digital-led01-led02-whole-01','construction.json'),
    ('digital-led01-led02-whole-02','construction.json'),
    ('digital-led01-source-packing-01','diagnosis.json'),
    ('digital-led30-whole-trunks-01','construction.json'),
    ('digital-led30-whole-trunks-02','construction.json'),
    ('digital-led30-minimal-latch-01','construction.json'),
    ('digital-led30-minimal-latch-02','construction.json'),
    ('digital-led30-minimal-latch-03','construction.json'),
    ('digital-led30-inner-global-probe-01','diagnosis.json'),
    ('digital-led30-native-leaf-repair-01','construction.json'),
    ('digital-led30-native-leaf-repair-02','construction.json'),
)


def run():
    parent = ROOT/'staging/digital-led16-closed-native-01'
    out = ROOT/'staging/digital-routing-continuation-27-01'
    out.mkdir(exist_ok=True)
    review = json.loads((parent/'review.json').read_text())
    assert not native_evidence_errors(parent/'digital_core.kicad_pro',review)
    assert review['status']['counts'] == dict(violations=0,unconnected_items=27,schematic_parity=0,erc=0)
    prior = json.loads((parent/'source-audit.json').read_text())
    known = prior['historical_test_binding_mismatches']
    unit = ROOT/'current-readiness.json'
    readiness = json.loads(unit.read_text())
    assert not readiness['fabrication_released'] and not readiness['complete_fabrication_package']
    assert readiness['shared_digital_core']['uncapped_open_connections'] == 143
    assert len(readiness['source_sha256']) == 213
    for name, expected in readiness['source_sha256'].items():
        p = Path(name)
        assert sha(p if p.is_absolute() else REPO/p) == expected
    paths = [parent/'source-audit.json',parent/'review.json',unit,Path(__file__),ROOT/'audit_candidate.py']
    probe = ROOT/'staging/digital-led30-connectivity-probe-native-01'
    probe_review = json.loads((probe/'review.json').read_text())
    assert not native_evidence_errors(probe/'digital_core.kicad_pro',probe_review)
    assert probe_review['status']['counts'] == dict(violations=2,unconnected_items=27,schematic_parity=0,erc=0)
    drc = json.loads((probe/'drc.json').read_text())
    assert len(drc['violations']) == 2 and all(v['type'] == 'track_dangling' for v in drc['violations'])
    assert any('LATCH_5V' in str(v) for v in drc['unconnected_items'])
    provisional = ROOT/'staging/digital-led30-minimal-latch-04/construction.json'
    record = json.loads(provisional.read_text())
    assert record['candidate_emitted'] and record['connectivity_hypothesis_only']
    assert not record['all_displaced_pad_connections_verified'] and not record['fabrication_released']
    paths += [probe/'review.json',probe/'drc.json',probe/'README.md',provisional,out/'README.md']
    cases = []
    for name, filename in CASES:
        folder = ROOT/'staging'/name
        p = folder/filename
        record = json.loads(p.read_text())
        assert record['candidate_emitted'] is False and record['native_rules_relaxed'] is False
        assert record['fabrication_released'] is False
        assert not list(folder.glob('*.kicad_pcb'))
        paths.append(p)
        cases.append(dict(record=str(p),candidate_emitted=False))
    roots = {str(p):sha(p) for p in paths}
    seen, digests, issues = set(), {}, []
    bindings = 0

    def visit(path):
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)
        walk(json.loads(path.read_text()),path)

    def walk(value, record):
        nonlocal bindings
        if isinstance(value,dict):
            for key,item in value.items():
                if key == 'source_sha256' and isinstance(item,dict):
                    for name,expected in item.items():
                        p = Path(name)
                        if not p.is_absolute():
                            p = (REPO if name.startswith(('hardware/','tests/')) else record.parent)/p
                        p = p.resolve(); assert p.is_file(),p
                        if p not in digests:
                            digests[p] = sha(p)
                        if digests[p] != expected:
                            issues.append(dict(record=str(record),source=str(p),expected=expected,actual=digests[p]))
                        bindings += 1
                        if p.suffix == '.json':
                            visit(p)
                else:
                    walk(item,record)
        elif isinstance(value,list):
            for item in value:
                walk(item,record)

    walk(dict(source_sha256=roots),out/'review.json')
    assert sorted(issues,key=lambda r:r['source']) == sorted(known,key=lambda r:r['source']),issues
    for p in digests:
        if p.suffix == '.py' and p.parent == ROOT:
            ast.parse(p.read_text(),filename=str(p))
    result = dict(source_sha256=roots,searches=cases,checked_source_bindings=bindings,
        matching_source_bindings=bindings-len(issues),source_bound_json_records=len(seen),
        historical_test_binding_mismatches=issues,current_unit_source_bindings_matched=213,
        current_native_board_and_evidence_unchanged=True,comparison_opens=27,selected_digital_opens=143,
        provisional_native_candidate_rejected=True,new_accepted_checkpoint=False,
        rejected_native_counts=probe_review['status']['counts'],inherited_focused_tests_passed=11,
        global_infeasibility_proven=False,complete_fabrication_package=False,fabrication_released=False)
    with (out/'review.json').open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(bindings=bindings,matching=bindings-len(issues),searches=len(cases),opens=27)))


if __name__ == '__main__':
    run()
