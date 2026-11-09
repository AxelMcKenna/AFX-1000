"""Seal the 30-open native checkpoint with its explicit performance limitations."""
import ast
import json
import re
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT/'staging/digital-serial1-closed-native-03'


def run():
    log = OUT/'focused-tests.log'
    assert 'Ran 53 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    review = json.loads((OUT/'serial1-closure-review.json').read_text())
    assert review['before_opens'] == 31 and review['after_opens'] == 30
    assert review['all_previous_pad_connections_preserved'] and review['full_serial_route_complete']
    assert review['only_newly_closed_net'] == '/LED/SERIAL_1'
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
    parent = ROOT/'staging/digital-serial1-receiving-review-01/source-audit.json'
    known = json.loads(parent.read_text())['historical_test_binding_mismatches']
    names = ['test_serial1_source_preparation', 'test_digital_joint_escape_packing',
             'test_serial_escape_compatibility', 'test_digital_existing_crossing_route',
             'test_digital_region_reachability', 'test_digital_planned_region_screen',
             'test_digital_region_points', 'test_digital_screen_branch',
             'test_serial1_closure', 'test_serial1_native_footprint_repair']
    tests = [REPO/'tests/tooling'/(n+'.py') for n in names]
    for p in tests + [Path(__file__)]:
        ast.parse(p.read_text(), filename=str(p))
    paths = [OUT/n for n in ('review.json', 'stage-connectivity-review.json', 'serial1-closure-review.json',
             'corridor-audit.json', 'visual-review.json', 'README.md', 'focused-tests.log')]
    paths += [parent, unit, Path(__file__), *tests]
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
        focused_tests_passed=53, selected_digital_opens=143, comparison_digital_opens=30,
        prior_pad_connections_preserved=True, serial1_closed=True,
        serial1_and_control30_route_length_optimization_required=True,
        electrical_performance_qualified=False, full_unit_complete=False, fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    heading = '## SERIAL_1 closed: native-clean 30-open comparison'
    assert heading not in (ROOT/'WORKLOG.md').read_text()
    with (ROOT/'WORKLOG.md').open('a') as f:
        f.write(f'''\n{heading}\n\nSERIAL_1 now closes in native KiCad: 31 to 30 opens, zero layout/parity/ERC\nfindings with all checks enabled. Starting CLOCK on its existing back-layer\nvia and LED48 on In3 avoids the extra CLOCK via that blocked the receiving\ncorridor. R3015 translates 0.25 mm right; all five restoration obligations and\nboth DATA branches are connected. Native feedback led to removal of one\nredundant source via and an unused CONTROL30 branch. Footprint serialization\nwas corrected from native keyword tokens, without changing parsed geometry.\n\nIndependent auditing confirms every prior pad connection preserved, only\nSERIAL_1 newly closed, and all unrelated net records exact. The delta removes\n29 tracks/five vias and adds 94 tracks/eleven vias; the board has 3,313 tracks\nand 532 vias. All four planes remain connected; 201 power/ground pads, 39 local,\n33 thermal and 32 front-control connections are retained. Closest added-track\nforeign copper gap is 0.201543 mm; nonexempt drill/SMD minimum remains\n0.154984 mm. SD spread is 5.999239 mm and 21 EP process holds remain.\n\nThis is explicitly a connectivity checkpoint: SERIAL_1 is 340.912 mm with\neight vias; CONTROL30 grows from 53.336 to 196.563 mm, although its via count\nfalls from four to two. These long detours need optimization and electrical\nqualification. The selected four-layer DC04 remains unchanged at 143 opens.\n\nAll 53 focused tests pass, including seven closure boundary checks and four\nserialization checks. Eight layer plots and both four-layer detail sets were\nvisually inspected. Recursive verification checks {bindings:,} bindings across\n{len(seen)} JSON records, with only the two previously disclosed historical NF\ntest mismatches. All 213 current unit-source bindings match.\n\nRemaining digital routing: SERIAL_0 and 29 LED outputs. Audio/NF routing, ESS\ninputs, stack/process and installed/first-article qualification remain open.\nNo release, order, commit or external message occurred. The full goal remains\nactive. Next priority is shortening SERIAL_1 and CONTROL30 while preserving\nthe native-clean connectivity, followed by the remaining digital nets.\n\nEvidence: [30-open checkpoint](staging/digital-serial1-closed-native-03/README.md).\n''')
    print(json.dumps(dict(bindings=bindings, matching=bindings-len(issues), json_records=len(seen), tests=53, opens=30)))


if __name__ == '__main__':
    run()
