"""Bind the completed SERIAL_1 search evidence without changing the PCB checkpoint."""
import ast
import json
import re
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
OUT=ROOT/'staging/digital-serial1-repair-review-01'

def run():
    roots=sorted((ROOT/'staging').glob('digital-serial1-*/diagnosis.json'))
    assert len(roots)==18, 'Every started search must have its terminal receipt'
    rows=[]
    for path in roots:
        record=json.loads(path.read_text())
        assert record['candidate_emitted'] is False
        assert record.get('complete_route_proposal') is None
        assert not list(path.parent.glob('*.kicad_pcb'))
        if 'attempts' in record:rows.append((path.parent.name,len(record['attempts'])))
    readme=OUT/'README.md';text=readme.read_text()
    text=text.replace('Final trial outcomes and source\nverification are recorded below after the running searches terminate.', 'Final trial outcomes and source verification are recorded below.')
    text+='\n## Completed trials\n\n| Search | Attempts | Complete repair |\n| --- | ---: | --- |\n'
    text+='\n'.join(f'| [{name}](../{name}/diagnosis.json) | {count} | No |' for name,count in rows)+'\n'
    text+='\nEvery search has terminated. None emitted a board. The latest trials can\nrestore MCU_PERMIT, CLOCK_5V and LED_48 together, but the tested continuations\nthen block SERIAL_1. Reversing the order leaves LED_48 disconnected. This\nremains a joint routing problem, with no accepted reduction from 31 opens.\n\n[Bound review](review.json) and [recursive source verification](source-audit.json)\npreserve the search history and the previous verified checkpoint.\n'
    readme.write_text(text)
    for target in re.findall(r'\]\(([^)]+)\)',text):assert (readme.parent/target).resolve().exists() or target in ('review.json','source-audit.json'),target
    tests=['test_serial_escape_compatibility.py','test_digital_existing_crossing_route.py','test_digital_close_margin.py','test_digital_polygon_path.py','test_digital_region_reachability.py','test_digital_planned_region_screen.py','test_digital_continuous_net_route.py']
    test_paths=[REPO/'tests/tooling'/name for name in tests]
    log=OUT/'focused-tests.log';assert 'Ran 35 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    for p in list(ROOT.glob('digital_serial1*.py'))+[ROOT/'digital_continuous_net_route_v2.py',Path(__file__),*test_paths]:ast.parse(p.read_text())
    unit_path=ROOT/'current-readiness.json';unit=json.loads(unit_path.read_text())
    assert unit['role_count']==15 and not unit['missing_source_files'] and not unit['fabrication_released']
    assert all(sha(Path(p))==h for p,h in unit['source_sha256'].items())
    parent=ROOT/'staging/digital-bypass-ground-signal-native-02/source-audit.json'
    paths=[*roots,parent,readme,log,Path(__file__),*test_paths]
    review=dict(source_sha256={str(p):sha(p) for p in paths},search_receipts=len(roots),attempts_by_search=dict(rows),focused_tests_passed=35,
                original_board_checkpoint='digital-bypass-ground-signal-native-02',verified_opens_unchanged=31,board_emitted=False,all_started_searches_terminal=True,
                unit_scope_check=dict(source_bindings_checked=len(unit['source_sha256']),roles=unit['role_count'],readiness_file_sha256=sha(unit_path)),
                full_unit_complete=False,fabrication_released=False)
    with (OUT/'review.json').open('x') as f:json.dump(review,f,indent=2);f.write('\n')
    seen=set();bindings=0;digests={}
    def visit(path):
        nonlocal bindings
        path=path.resolve()
        if path in seen:return
        seen.add(path)
        record=json.loads(path.read_text())
        def walk(value):
            nonlocal bindings
            if isinstance(value,dict):
                for key,item in value.items():
                    if key=='source_sha256':
                        for name,expected in item.items():
                            p=Path(name);p=p if p.is_absolute() else path.parent/p
                            p=p.resolve();assert p.is_file(),p
                            if p not in digests:digests[p]=sha(p)
                            assert digests[p]==expected,(path,p)
                            bindings+=1
                            if p.suffix=='.json':visit(p)
                    else:walk(item)
            elif isinstance(value,list):
                for item in value:walk(item)
        walk(record)
    visit(OUT/'review.json')
    assert bindings>=3508
    audit=dict(source_sha256={str(OUT/'review.json'):sha(OUT/'review.json')},verified_source_bindings=bindings,source_bound_json_records=len(seen),missing_or_mismatched_sources=[],fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:json.dump(audit,f,indent=2);f.write('\n')
    logbook=ROOT/'WORKLOG.md'
    with logbook.open('a') as f:
        f.write(f'''\n## SERIAL_1: coordinated escape and restoration investigation\n\nThe previous turn's 32-to-31-open checkpoint remains authoritative. This turn\nadds eighteen source-bound search receipts and a versioned zero-length-via-leg\nrouting fix. No new board was emitted or adopted. The source-side cut is\nMCU_PERMIT copper; the receiving-side cut includes CLOCK_5V and LED_48. Two\nCONTROL_30 front tracks conditionally open global serial access. A 0.05 mm\nlocal via grid finds 102 compatible receiving-end triples and independently\nreplays eighteen distinct arrangements, correcting the sparse sample's zero\nresult. The original legal CLOCK/LED48 via positions were absent from that\nsparse sample.\n\nSubsequent searches identify LED_37 via 4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1\nand LED_50 In3 track f1ea2e26-acf3-46e4-a518-bdb380e99c7e as additional\nrestoration obstructions. Trials explicitly require restoration of both nets.\nRouting MCU_PERMIT/CLOCK/LED48 together blocks SERIAL_1 in tested geometry;\nrouting SERIAL_1 earlier blocks LED48. Full retained-component targets include\nsampled track interiors. Failures are bounded, not global infeasibility proofs.\nSerial-only proposals around 338 mm remain unqualified and unadopted.\n\nThe continuous-route helper now skips zero-length legs at reused vias before\ncalling the polygon router. Six tests cover strict source/destination via\nbehavior and the four prior route cases; seven new compatibility tests cover\ntrack and through-via spacing. The focused 35-test suite passes. No native CAD\nrun is claimed this turn because no complete PCB candidate was constructed.\n\nThe detailed review records the invalid supply-pad-area probe and the exact\nprotected supply names used by the final cut-set reduction. The verified\n31-open board and all 213 unit-source hashes remain unchanged. Final source\nverification checks {bindings:,} bindings across {len(seen)} JSON records.\nAll started searches are terminal. Full-unit routing, approved ESS inputs,\nphysical stack/process, installed assembly and qualification remain unfinished.\nNo supplier message, order, commit or release occurred; the goal remains active.\n\nReview: [SERIAL_1 investigation](staging/digital-serial1-repair-review-01/README.md).\n''')
    print(json.dumps(dict(search_receipts=len(roots),attempts_by_search=dict(rows),source_bindings=bindings,json_records=len(seen),focused_tests=35,opens=31)))

if __name__=='__main__':run()
