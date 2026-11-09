"""Seal the independently verified LED09 closure checkpoint and failed trials."""
import ast
import json
import re
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT/'staging/digital-led09-closed-native-01'


def run():
    log = OUT/'focused-tests.log'
    assert 'Ran 7 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    review = json.loads((OUT/'closure-review.json').read_text())
    assert review['before_opens']==30 and review['after_opens']==29
    assert review['all_previous_pad_connections_preserved'] and review['only_LED09_pad_groups_merged']
    assert review['all_component_poses_and_authored_zones_exact']
    assert not review['electrical_timing_thermal_EMC_and_installed_performance_qualified']
    readme = OUT/'README.md'
    for link in re.findall(r'\]\(([^)]+)\)', readme.read_text()):
        assert (readme.parent/link).resolve().exists() or link == 'source-audit.json', link
    unit = ROOT/'current-readiness.json'
    readiness = json.loads(unit.read_text())
    assert len(readiness['source_sha256']) == 213
    assert readiness['shared_digital_core']['uncapped_open_connections'] == 143 and not readiness['fabrication_released']
    for name, expected in readiness['source_sha256'].items():
        p = Path(name)
        assert sha(p if p.is_absolute() else REPO/p) == expected
    parent = ROOT/'staging/digital-costed-shortening-native-01/source-audit.json'
    known = json.loads(parent.read_text())['historical_test_binding_mismatches']
    names = ['test_digital_led09_closure']
    tests = [REPO/'tests/tooling'/(n+'.py') for n in names]
    for p in tests + [Path(__file__)]:
        ast.parse(p.read_text(), filename=str(p))
    paths = [OUT/n for n in ('review.json', 'stage-connectivity-review.json', 'closure-review.json',
             'corridor-audit.json', 'visual-review.json', 'README.md', 'focused-tests.log')]
    paths += [parent, unit, Path(__file__), *tests]
    searches = [
        ('digital-remaining-region-survey-30-01','diagnosis.json'),
        ('digital-led70-corridor-probe-01','diagnosis.json'),
        ('digital-led70-escape-packing-01','diagnosis.json'),
        ('digital-led70-escape-packing-02','diagnosis.json'),
        ('digital-led70-serial2-detour-01','construction.json'),
        ('digital-led70-coordinated-detour-01','construction.json'),
        ('digital-led70-coordinated-detour-02','construction.json'),
        ('digital-led30-inner-detour-01','construction.json'),
        ('digital-led30-inner-detour-02','construction.json'),
        ('digital-led09-outer-detour-01','construction.json'),
        ('digital-led09-outer-detour-02','construction.json'),
    ]
    for label, filename in searches:
        p=ROOT/'staging'/label/filename
        record=json.loads(p.read_text())
        assert record['candidate_emitted'] == (label=='digital-led09-outer-detour-02')
        assert not record['fabrication_released'] and not record['native_rules_relaxed']
        paths.append(p)
    roots = {str(p): sha(p) for p in paths}
    seen, digests, issues = set(), {}, []
    bindings = 0

    def visit(path):
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)
        walk(json.loads(path.read_text()), path)

    def walk(value, record):
        nonlocal bindings
        if isinstance(value, dict):
            for key, item in value.items():
                if key == 'source_sha256' and isinstance(item, dict):
                    for name, expected in item.items():
                        path = Path(name)
                        if not path.is_absolute():
                            path = (REPO if name.startswith(('hardware/', 'tests/')) else record.parent)/path
                        path = path.resolve()
                        assert path.is_file(), path
                        if path not in digests:
                            digests[path] = sha(path)
                        if digests[path] != expected:
                            issues.append(dict(record=str(record), source=str(path), expected=expected, actual=digests[path]))
                        bindings += 1
                        if path.suffix == '.json':
                            visit(path)
                else:
                    walk(item, record)
        elif isinstance(value, list):
            for item in value:
                walk(item, record)

    walk(dict(source_sha256=roots), OUT/'source-audit.json')
    assert sorted(issues, key=lambda r: r['source']) == sorted(known, key=lambda r: r['source']), issues
    result = dict(source_sha256=roots, checked_source_bindings=bindings,
        matching_source_bindings=bindings-len(issues), source_bound_json_records=len(seen),
        historical_test_binding_mismatches=issues, historical_mismatches_unchanged_from_previous_review=True,
        missing_sources=[], complete_recursive_match=False, current_unit_source_bindings_matched=213,
        focused_tests_passed=7, inherited_parent_focused_tests_passed=69, selected_digital_opens=143, comparison_digital_opens=29,
        prior_pad_connections_preserved=True, only_LED09_pad_groups_merged=True,
        LED09_route_length_optimization_required=True,
        electrical_performance_qualified=False, full_unit_complete=False, fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(bindings=bindings, matching=bindings-len(issues), json_records=len(seen), tests=7, opens=29)))


if __name__=='__main__':
    run()
