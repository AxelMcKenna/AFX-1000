"""Bind terminal restoration searches and verify their immutable source chain."""
import ast,json,re
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
OUT=ROOT/'staging/digital-serial1-restoration-review-01'

def run():
    previous=ROOT/'staging/digital-serial1-repair-review-01/review.json'
    old={Path(p).resolve() for p in json.loads(previous.read_text())['source_sha256']}
    roots=[p for p in sorted((ROOT/'staging').glob('digital-serial1-*/*.json'))
           if p.name in ('diagnosis.json','construction.json','templates.json') and p.resolve() not in old]
    assert len(roots)==17
    searches=[];templates=[];template_files=[]
    for p in roots:
        r=json.loads(p.read_text())
        if p.name=='templates.json':
            assert len(r['templates'])==8
            for t in r['templates']:
                target=p.parent/t['file'];assert sha(target)==t['sha256'];template_files.append(target)
            templates.append(p)
        else:
            assert r['candidate_emitted'] is False and not r.get('placement_and_routes') and not r.get('selected')
            assert not list(p.parent.glob('*.kicad_pcb'))
            searches.append(p)
    assert len(searches)==15 and len(templates)==2
    readme=OUT/'README.md';log=OUT/'focused-tests.log'
    assert 'Ran 46 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    for link in re.findall(r'\]\(([^)]+)\)',readme.read_text()):
        assert (readme.parent/link).resolve().exists() or link in ('review.json','source-audit.json'),link
    tests=['test_serial_escape_compatibility.py','test_digital_existing_crossing_route.py','test_digital_close_margin.py','test_digital_polygon_path.py','test_digital_region_reachability.py','test_digital_planned_region_screen.py','test_digital_continuous_net_route.py','test_digital_region_points.py','test_digital_resistor_native_pose_screen_v2.py']
    test_paths=[REPO/'tests/tooling'/n for n in tests]
    nf_tests=[REPO/'tests/tooling'/n for n in ('test_nf_logic_swap.py','test_nf_stage_repack_boundary.py')]
    nf_log=OUT/'nf-current-tests.log'
    assert 'Ran 10 tests' in nf_log.read_text() and nf_log.read_text().rstrip().endswith('OK')
    nf_helpers=[ROOT/n for n in ('audit_nf_logic_swap.py','audit_nf_logic_swap_final.py','source_audit_tools.py')]
    for p in [*ROOT.glob('digital_serial1*.py'),*ROOT.glob('digital_resistor*.py'),Path(__file__),*test_paths,*nf_tests,*nf_helpers]:ast.parse(p.read_text())
    unit_path=ROOT/'current-readiness.json';unit=json.loads(unit_path.read_text())
    assert unit['role_count']==15 and len(unit['source_sha256'])==213 and not unit['fabrication_released']
    for p,h in unit['source_sha256'].items():assert sha(Path(p) if Path(p).is_absolute() else REPO/p)==h
    assert unit['shared_digital_core']['uncapped_open_connections']==143
    assert unit['shared_audio_core']['layout_candidate']['uncapped_open_connections']==208
    board_review=ROOT/'staging/digital-bypass-ground-signal-native-02/review.json'
    native=json.loads(board_review.read_text());assert native['uncapped_open_connections']==31
    paths=[*roots,*template_files,previous,ROOT/'staging/digital-serial1-repair-review-01/source-audit.json',unit_path,board_review,readme,log,nf_log,Path(__file__),*test_paths,*nf_tests,*nf_helpers]
    review=dict(source_sha256={str(p):sha(p) for p in paths},search_receipts=len(searches),native_template_receipts=len(templates),focused_tests_passed=46,additional_current_nf_tests_passed=10,legacy_nf_test_binding_mismatches=2,
                selected_digital_opens=143,comparison_digital_opens=31,audio_opens=208,unit_source_bindings_checked=213,
                all_started_searches_terminal=True,board_candidate_emitted=False,source_board_changed=False,
                full_unit_complete=False,fabrication_released=False)
    seen=set();digests={};bindings=0;issues=[]
    def visit(path):
        path=path.resolve()
        if path in seen:return
        seen.add(path)
        walk(json.loads(path.read_text()),path)
    def walk(value,base):
        nonlocal bindings
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='source_sha256' and isinstance(item,dict):
                    for name,expected in item.items():
                        p=Path(name)
                        if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else base.parent)/p
                        p=p.resolve();assert p.is_file(),p
                        if p not in digests:digests[p]=sha(p)
                        if digests[p]!=expected:issues.append(dict(record=str(base),source=str(p),expected=expected,actual=digests[p]))
                        bindings+=1
                        if p.suffix=='.json':visit(p)
                else:walk(item,base)
        elif isinstance(value,list):
            for item in value:walk(item,base)
    # Verify the entire chain before creating the final immutable receipts.
    walk(review,OUT/'review.json')
    assert len(issues)==2 and {i['source'] for i in issues}=={str(p) for p in nf_tests},issues
    assert all(Path(i['record'])==ROOT/'staging/nf-logic-swap-clean-native-01/focused-tests.json' for i in issues),issues
    with (OUT/'review.json').open('x') as f:json.dump(review,f,indent=2);f.write('\n')
    audit=dict(source_sha256={str(OUT/'review.json'):sha(OUT/'review.json'),str(Path(__file__)):sha(Path(__file__))},
               checked_source_bindings=bindings,matching_source_bindings=bindings-len(issues),source_bound_json_records=len(seen),missing_sources=[],historical_test_binding_mismatches=issues,complete_recursive_match=False,fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:json.dump(audit,f,indent=2);f.write('\n')
    with (ROOT/'WORKLOG.md').open('a') as f:
        f.write(f'''\n## SERIAL_1: restoration conflicts and native resistor-placement search\n\nFifteen new terminal search/restoration receipts and two native Linux rotation\ntemplate receipts preserve this investigation. No complete PCB candidate was\nemitted or adopted. The digital comparison remains at 31 opens; selected\nfour-layer DC04 remains at 143, audio at 208 and NF at 138.\n\nThree DATA_5V_SRC back-layer tracks conditionally block the reserved serial\nroute. Removing them permits a 338.507 mm serial proposal but disconnects DATA.\nReconnecting DATA first blocks serial again; no directly reachable local DATA\nvia passes the 0.1 mm escape grid. LED37's separate access conflict follows the\nproposed MCU_PERMIT routes. Complete retained-component probes confirm both.\n\nNative resistor rotations on both faces support placement checks. None of\n175 original or 102 northern back-side R3015 legal poses reaches the DATA\nsource. Its front-side grid supplies no pad-clear pose. A 9.206 mm MCU trunk\nproposal retains the original LED37 via, but none of 364 back-side R1003 legal\nposes reaches MCU_PERMIT, and its front grid has no mechanical placement.\nThese are bounded results, not global infeasibility proofs. The next repair\nmust reconsider paired local escapes rather than fix the same reserved routes.\n\nThe focused suite passes 46 tests, including eight new placement tests.\nRecursive verification checks {bindings:,} source bindings across {len(seen)}\nJSON records; all 213 unit-source bindings remain unchanged. Two older NF test\nbindings are stale; the current versions pass 10 tests in a new supplemental\nlog. The original 129-test receipt is preserved and is not claimed as rerun. Native template\nwork boards are not PCB candidates, and no native PCB acceptance is claimed.\nAll searches are terminal; routing, ESS inputs, physical stack/process, installed\nreceiving and first-article qualification remain unfinished. No release, order,\nmessage or commit occurred. The full-unit goal remains active.\n\nReview: [restoration and resistor placement](staging/digital-serial1-restoration-review-01/README.md).\n''')
    print(json.dumps(dict(search_receipts=15,template_receipts=2,tests=46,source_bindings=bindings,json_records=len(seen),comparison_opens=31)))

if __name__=='__main__':run()
