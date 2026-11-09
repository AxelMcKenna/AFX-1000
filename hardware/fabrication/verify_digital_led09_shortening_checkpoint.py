"""Seal the LED09 shortening checkpoint, including the rejected sliver trial."""
import ast
import json
import re
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT/'staging/digital-led09-shortened-native-02'


def run():
    log = OUT/'focused-tests.log'
    assert 'Ran 11 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    review = json.loads((OUT/'shortening-review.json').read_text())
    assert review['before_opens']==review['after_opens']==29
    assert review['all_previous_pad_connections_preserved'] and review['LED09_shortened'] and review['no_pad_groups_changed']
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
    parent = ROOT/'staging/digital-led09-closed-native-01/source-audit.json'
    known = json.loads(parent.read_text())['historical_test_binding_mismatches']
    names = ['test_digital_led09_shortening','test_digital_route_shortcuts']
    tests = [REPO/'tests/tooling'/(n+'.py') for n in names]
    for p in tests + [Path(__file__)]:
        ast.parse(p.read_text(), filename=str(p))
    paths = [OUT/n for n in ('review.json', 'stage-connectivity-review.json', 'shortening-review.json',
             'corridor-audit.json', 'visual-review.json', 'README.md', 'focused-tests.log')]
    paths += [parent, unit, Path(__file__), *tests]
    for label in ('digital-led09-screened-shortcuts-01','digital-led09-screened-shortcuts-02'):
        p=ROOT/'staging'/label/'construction.json'
        record=json.loads(p.read_text())
        assert record['candidate_emitted'] and not record['native_rules_relaxed'] and not record['fabrication_released']
        paths.append(p)
    rejected=ROOT/'staging/digital-led09-shortened-native-01'
    r=json.loads((rejected/'review.json').read_text())
    assert r['status']['counts']==dict(violations=1,unconnected_items=29,schematic_parity=0,erc=0)
    assert r['status']['all_native_rule_checks_enabled']
    assert sha(rejected/'digital_core.kicad_pcb')==r['checked_PCB_sha256']
    for name,h in r['raw_report_sha256'].items():
        assert sha(rejected/name)==h
        paths.append(rejected/name)
    findings=json.loads((rejected/'drc.json').read_text())['violations']
    assert len(findings)==1 and findings[0]['type']=='copper_sliver' and findings[0]['severity']=='warning'
    paths += [rejected/'review.json',rejected/'digital_core.kicad_pcb']
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
        focused_tests_passed=11, inherited_parent_focused_tests_passed=7, selected_digital_opens=143, comparison_digital_opens=29,
        prior_pad_connections_preserved=True, all_pad_groups_exact=True, LED09_shortened=True,
        LED09_route_length_optimization_required=True,
        electrical_performance_qualified=False, full_unit_complete=False, fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(bindings=bindings, matching=bindings-len(issues), json_records=len(seen), tests=11, opens=29)))


if __name__=='__main__':
    run()
