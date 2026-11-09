"""Record terminal receiving-area searches without changing accepted board state."""
import ast
import json
import re
from pathlib import Path

from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT/'staging/digital-serial1-receiving-review-01'


def run():
    names = [
        ('digital-serial1-data-placement-first-02', 'diagnosis.json'),
        ('digital-serial1-combined-restoration-02', 'construction.json'),
        ('digital-serial1-shifted-target-escape-01', 'diagnosis.json'),
        ('digital-serial1-shifted-target-pack-01', 'diagnosis.json'),
        ('digital-serial1-combined-restoration-03', 'construction.json'),
        ('digital-serial1-receiving-topology-01', 'diagnosis.json'),
        ('digital-serial1-combined-restoration-04', 'construction.json'),
        ('digital-serial1-combined-restoration-05', 'construction.json'),
    ]
    paths = [ROOT/'staging'/folder/file for folder, file in names]
    records = [json.loads(p.read_text()) for p in paths]
    assert all(not r.get('candidate_emitted', False) for r in records)
    packing = records[3]
    assert len(packing['packing']['choices']) == 292 and packing['packing']['complete_enumeration']
    assert len(packing['screen_replayed_choices']) == 32 and packing['all_screen_replayed_choices_passed']
    observations = records[5]['observations']
    assert len(observations) == 12
    assert all(not o['region_report']['connected'] for o in observations if o['omitted_route_index'] is None)
    assert all(o['region_report']['connected'] for o in observations if o['omitted_net'] in ('/LED/SERIAL_1', '/LED/LED_48'))
    assert all(not o['region_report']['connected'] for o in observations if o['omitted_net'] == '/LED/CLOCK_5V')
    counts = {names[i][0]: len(records[i]['attempts']) for i in (1, 4, 6, 7)}
    log = OUT/'focused-tests.log'
    assert 'Ran 42 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    tests = ['test_serial1_source_preparation.py', 'test_digital_joint_escape_packing.py',
             'test_serial_escape_compatibility.py', 'test_digital_existing_crossing_route.py',
             'test_digital_region_reachability.py', 'test_digital_planned_region_screen.py',
             'test_digital_region_points.py', 'test_digital_screen_branch.py']
    test_paths = [REPO/'tests/tooling'/n for n in tests]
    for p in test_paths + [Path(__file__)]:
        ast.parse(p.read_text(), filename=str(p))
    parent = ROOT/'staging/digital-serial1-source-preparation-native-01/source-audit.json'
    known = json.loads(parent.read_text())['historical_test_binding_mismatches']
    unit = ROOT/'current-readiness.json'
    readiness = json.loads(unit.read_text())
    assert len(readiness['source_sha256']) == 213
    assert readiness['shared_digital_core']['uncapped_open_connections'] == 143
    assert not readiness['fabrication_released']
    for name, expected in readiness['source_sha256'].items():
        p = Path(name)
        assert sha(p if p.is_absolute() else REPO/p) == expected
    table = '\n'.join(f'| [{folder}](../{folder}/{file}) | {counts.get(folder, "—")} |' for folder, file in names)
    readme = OUT/'README.md'
    with readme.open('x') as f:
        f.write(f'''# SERIAL_1 receiving-area review

The receiving-area trials did not produce a complete candidate. The latest
native-checked comparison remains the [source-preparation checkpoint](../digital-serial1-source-preparation-native-01/README.md):
31 opens, zero native geometry/parity/ERC findings, and all previous pad groups
preserved. It prepares the source escape but does not close SERIAL_1. The
selected four-layer DC04 remains unchanged at 143 opens.

## Evidence and limits

Moving R3015 by 0.25 mm to (75.25, 21) permits both DATA branches in the local
screen. Fresh receiving escapes were sampled at 0.025 mm spacing. The discrete
packing search found 292 spatially distinct local arrangements; 32 were
independently replayed, spanning ten SERIAL_1 exit bins. Local compatibility
does not establish complete net restoration.

The combined searches retain all five obligations: SERIAL_1, CLOCK, LED48,
LED50, and CONTROL30. The table counts attempted packs; a last attempt may be
cut short by the route budget. It does not count every pack as fully explored.

| Terminal search or diagnostic | Attempted packs |
| --- | ---: |
{table}

Independent topology replay of the first two resampled packs found an actual
loss of free-space connectivity after routing SERIAL_1 or LED48. Removing the
opposing global route restored access; removing only the global CLOCK route
did not. The local CLOCK escape remained in that diagnostic. This is evidence
about those specific proposals, not proof that the board is unroutable.

The alternate-departure search restricted the LED48 starting-via graph edge
to test other layer paths. This removes a planner option only; it does not
remove actual copper or relax rules. A separate bounded search targeted the
17 local packs with CLOCK's via farther left (x < 72.9 mm), which the earlier 32-pack
sample had missed. Neither search emitted a complete candidate.

The first resampled SERIAL_1 proposal was approximately 338 mm long. Its
electrical suitability was not established, and no such route was adopted.
No conclusion about global infeasibility follows from these bounded searches.

## Verification and unit status

[All 42 focused tests pass](focused-tests.log), including four tests for
independent trial reservations. Captured copper and its spatial indexes are
shared read-only; proposed tracks, vias and cache dictionaries are separate
between trials. [Recursive source verification](source-audit.json) records
the exact source bindings and discloses the two unchanged historical NF test
hash mismatches. All 213 current unit-source bindings match.

The source-preparation checkpoint lengthens MCU_PERMIT by about 24.7 mm and
adds one via; that trade-off remains electrically unqualified. Audio still
has 208 opens and the approved ESS footprint hold; NF has 138 opens and two
isolated-ground ERC warnings. Stack/process, receiving, installed-unit and
first-article electrical, thermal and EMC qualification remain unfinished.

The next layout work must preserve a complete LED48 path while opening a
separate SERIAL_1 receiving corridor, then restore every cut net and pass
native and independent copper checks. Repeating only the previously sampled
exit positions is insufficient. No board was released or ordered, and no
commit or external message was made. The full-unit goal remains active.
''')
    for link in re.findall(r'\]\(([^)]+)\)', readme.read_text()):
        assert (readme.parent/link).resolve().exists() or link == 'source-audit.json', link
    roots = {str(p): sha(p) for p in paths + [parent, unit, log, readme, Path(__file__), *test_paths]}
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
        historical_test_binding_mismatches=issues, missing_sources=[], complete_recursive_match=False,
        historical_mismatches_unchanged_from_previous_review=True, current_unit_source_bindings_matched=213,
        focused_tests_passed=42, attempted_packs=counts, selected_digital_opens=143,
        comparison_digital_opens=31, candidate_emitted=False, global_infeasibility_proven=False,
        full_unit_complete=False, fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    heading = '## SERIAL_1: receiving-area topology and alternate departures'
    assert heading not in (ROOT/'WORKLOG.md').read_text()
    with (ROOT/'WORKLOG.md').open('a') as f:
        f.write(f'\n{heading}\n\nEight terminal searches/diagnostics follow the native source-preparation checkpoint.\nFresh 0.025 mm receiving escapes yield 292 spatial local packs; 32 were replayed\nindependently. Two-pack topology replay isolates mutual SERIAL_1/LED48\nobstruction. Alternate layer departures and 17 farther-left CLOCK packs did\nnot yield a complete restoration. No new PCB was emitted or adopted.\n\nAll 42 focused tests pass. Recursive verification checks {bindings:,} bindings\nacross {len(seen)} JSON records, with only the same two historical NF test\nmismatches. All 213 current unit-source bindings match. Comparison/selected\ndigital opens stay 31/143. The full unit remains unfinished; no release, order,\ncommit or external message occurred.\n\nDetails: [receiving-area review](staging/digital-serial1-receiving-review-01/README.md).\n')
    print(json.dumps(dict(bindings=bindings, matching=bindings-len(issues), json_records=len(seen), tests=42, attempted_packs=counts)))


if __name__ == '__main__':
    run()
