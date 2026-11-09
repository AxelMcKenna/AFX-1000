"""Seal the independently verified two-net shortening checkpoint."""
import ast
import json
import re
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT/'staging/digital-costed-shortening-native-01'


def run():
    log = OUT/'focused-tests.log'
    assert 'Ran 69 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    review = json.loads((OUT/'shortening-review.json').read_text())
    assert review['before_opens'] == review['after_opens'] == 30
    assert review['all_previous_pad_connections_preserved'] and review['both_nets_shortened']
    assert review['no_pad_groups_changed'] and review['all_component_poses_and_authored_zones_exact']
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
    parent = ROOT/'staging/digital-serial1-closed-native-03/source-audit.json'
    known = json.loads(parent.read_text())['historical_test_binding_mismatches']
    names = ['test_serial1_source_preparation', 'test_digital_joint_escape_packing',
             'test_serial_escape_compatibility', 'test_digital_existing_crossing_route',
             'test_digital_region_reachability', 'test_digital_planned_region_screen',
             'test_digital_region_points', 'test_digital_screen_branch',
             'test_serial1_closure', 'test_serial1_native_footprint_repair', 'test_digital_costed_region_route', 'test_digital_costed_region_incumbents', 'test_digital_costed_region_seeds', 'test_digital_costed_shortening']
    tests = [REPO/'tests/tooling'/(n+'.py') for n in names]
    for p in tests + [Path(__file__)]:
        ast.parse(p.read_text(), filename=str(p))
    paths = [OUT/n for n in ('review.json', 'stage-connectivity-review.json', 'shortening-review.json',
             'corridor-audit.json', 'visual-review.json', 'README.md', 'focused-tests.log')]
    paths += [parent, unit, Path(__file__), *tests]
    searches=['digital-serial1-costed-restoration-01','digital-serial1-costed-restoration-02','digital-serial1-costed-restoration-03','digital-control30-costed-restoration-01','digital-control30-costed-restoration-02','digital-combined-costed-routes-01','digital-control30-local-restoration-01','digital-control30-local-restoration-02']
    paths += [ROOT/'staging'/n/'construction.json' for n in searches]
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
        focused_tests_passed=69, selected_digital_opens=143, comparison_digital_opens=30,
        prior_pad_connections_preserved=True, both_nets_shortened=True,
        serial1_and_control30_route_length_optimization_required=True,
        electrical_performance_qualified=False, full_unit_complete=False, fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    heading = '## SERIAL_1 and CONTROL30: costed shortening checkpoint'
    assert heading not in (ROOT/'WORKLOG.md').read_text()
    with (ROOT/'WORKLOG.md').open('a') as f:
        f.write(f"""\n{heading}\n\nThe eight-layer comparison remains at 30 opens with zero native layout,
parity or ERC findings and all checks enabled. SERIAL_1 falls from 340.912 to
129.919 mm with eight vias retained. CONTROL30 falls from 196.563 to 132.458 mm
and two vias to zero. Every prior pad group is preserved. Only these two nets
change; all other net records, footprints, authored zones and board geometry
remain exact. The board now has 3,276 tracks and 530 vias.

The finite costed search measures actual planar paths and retains complete
incumbents. Earlier native via seeds were screened as extra candidates. The
two proposals were replayed together, an intermediate vertex was centered on
its own via, and CONTROL30's receiving return tail was removed. Two attempted
compact original-branch restorations emitted no candidate. These searches do
not prove global optimum or global infeasibility.

Independent actual-copper verification checks 54 added tracks and six new vias;
minimum measured nearby foreign-track gap is 0.201397 mm. All four planes remain
connected; 201 power/ground pads, 39 local, 33 thermal and 32 front-control
connections remain intact. Drill/SMD minimum is 0.154984 mm, SD spread 5.999239 mm,
and 21 exposed-pad process holds remain. Eight layers and four detail regions
were visually inspected. All 69 focused tests pass.

Recursive verification checks {bindings:,} bindings across {len(seen)} JSON
records, with only the same two historical NF test mismatches. All 213 current
unit-source bindings match. Selected four-layer DC04 stays at 143 opens.

The comparison still needs SERIAL_0 and 29 LED outputs. CONTROL30 retains a
perimeter detour and is still longer than its 53.336 mm pre-SERIAL_1-closure
route. Electrical, timing, EMC, installed and manufacturing qualification remain
open, as do audio/NF routing and ESS inputs. No release, order, commit or external
message occurred. The full goal remains active.

Evidence: [shortening checkpoint](staging/digital-costed-shortening-native-01/README.md).
""")
    print(json.dumps(dict(bindings=bindings, matching=bindings-len(issues), json_records=len(seen), tests=69, opens=30)))


if __name__ == '__main__':
    run()
