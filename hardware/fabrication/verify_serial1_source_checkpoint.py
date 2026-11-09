"""Seal the native-checked source-preparation checkpoint and its evidence."""
import ast,json,re
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
OUT=ROOT/'staging/digital-serial1-source-preparation-native-01'

def run():
    tests=['test_serial1_source_preparation.py','test_digital_joint_escape_packing.py','test_serial_escape_compatibility.py','test_digital_existing_crossing_route.py','test_digital_region_reachability.py','test_digital_planned_region_screen.py','test_digital_region_points.py']
    test_paths=[REPO/'tests/tooling'/n for n in tests]
    readme=OUT/'README.md';log=OUT/'focused-tests.log'
    assert 'Ran 38 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    for link in re.findall(r'\]\(([^)]+)\)',readme.read_text()):
        assert (readme.parent/link).resolve().exists() or link=='source-audit.json',link
    p=OUT/'source-preparation-review.json';review=json.loads(p.read_text())
    assert review['all_pad_groups_preserved'] and review['before_opens']==review['after_opens']==31
    assert review['all_other_net_records_exact'] and not review['full_serial_route_complete']
    unit=ROOT/'current-readiness.json';u=json.loads(unit.read_text())
    assert len(u['source_sha256'])==213 and u['shared_digital_core']['uncapped_open_connections']==143 and not u['fabrication_released']
    for name,h in u['source_sha256'].items():
        q=Path(name);q=q if q.is_absolute() else REPO/q
        assert sha(q)==h
    parent=ROOT/'staging/digital-serial1-restoration-review-01/source-audit.json'
    known=json.loads(parent.read_text())['historical_test_binding_mismatches']
    paths=[OUT/n for n in ('review.json','stage-connectivity-review.json','source-preparation-review.json','corridor-audit.json','visual-review.json','README.md','focused-tests.log')]+[parent,unit,Path(__file__),*test_paths]
    for q in test_paths+[Path(__file__)]:ast.parse(q.read_text())
    roots={str(q):sha(q) for q in paths};seen=set();digests={};issues=[];bindings=0
    def visit(q):
        q=q.resolve()
        if q in seen:return
        seen.add(q);walk(json.loads(q.read_text()),q)
    def walk(v,record):
        nonlocal bindings
        if isinstance(v,dict):
            for key,item in v.items():
                if key=='source_sha256' and isinstance(item,dict):
                    for name,expected in item.items():
                        q=Path(name)
                        if not q.is_absolute():q=(REPO if name.startswith(('hardware/','tests/')) else record.parent)/q
                        q=q.resolve();assert q.is_file(),q
                        if q not in digests:digests[q]=sha(q)
                        if digests[q]!=expected:issues.append(dict(record=str(record),source=str(q),expected=expected,actual=digests[q]))
                        bindings+=1
                        if q.suffix=='.json':visit(q)
                else:walk(item,record)
        elif isinstance(v,list):
            for item in v:walk(item,record)
    walk(dict(source_sha256=roots),OUT/'source-audit.json')
    assert sorted(issues,key=lambda r:r['source'])==sorted(known,key=lambda r:r['source']),issues
    result=dict(source_sha256=roots,checked_source_bindings=bindings,matching_source_bindings=bindings-len(issues),
        source_bound_json_records=len(seen),missing_sources=[],historical_test_binding_mismatches=issues,complete_recursive_match=False,
        historical_mismatches_unchanged_from_previous_review=True,current_unit_source_bindings_matched=213,
        focused_tests_passed=38,native_preparation_checkpoint_complete=True,full_routing_complete=False,
        selected_digital_opens=143,comparison_digital_opens=31,full_unit_complete=False,fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    heading='## SERIAL_1: native source-preparation checkpoint'
    assert heading not in (ROOT/'WORKLOG.md').read_text()
    with (ROOT/'WORKLOG.md').open('a') as f:
        f.write(f'''\n{heading}\n\nA coordinated LED37 via relocation and MCU_PERMIT rework now passes native\nchecks on an actual PCB: zero geometry/parity/ERC findings and 31 opens, all\nchecks enabled. The independent audit proves every native pad group preserved;\nonly the two declared nets change. Six tracks and two vias are replaced by\neighteen tracks and three vias. Component poses, authored zones and all other\ncopper remain exact. The future SERIAL_1 source escape passes a fresh native-\ncapture screen, but is not installed as dangling copper.\n\nThe preparation retains 201 power/ground pads, 39 local, 33 thermal and 32\nfront-control connections. Four plane unions remain connected. The closest\nnew-track/foreign-copper gap is 0.201383 mm; the nonexempt drill/SMD minimum\nremains 0.154984 mm and SD spread 5.999239 mm. The 21 EP-via process holds\nremain. All eight layers and four source details were visually inspected.\nThirty-eight tests pass, including seven packing and six mutation-boundary\ntests. MCU_PERMIT grows from 53.190 to 77.919 mm and two to three vias; this\ntrade-off remains electrically unqualified. LED37 shortens slightly.\n\nRecursive verification checks {bindings:,} bindings across {len(seen)} JSON\nrecords. The two disclosed historical NF test mismatches are unchanged; all\n213 current unit-source bindings match. The first new capture used relative\nsource paths; the second, unchanged native-board capture uses absolute paths\nfor the physical auditor. Both captures are preserved.\n\nThis is a development preparation checkpoint, with no reduction in opens and\nno change to selected four-layer DC04. Receiving-end joint routing remains\nunder investigation. Audio/NF routing, approved ESS inputs, stack/process,\ninstalled assembly and first-article qualification remain incomplete. No\norder, release, commit or external message occurred. The full goal stays active.\n\nCheckpoint: [native source preparation](staging/digital-serial1-source-preparation-native-01/README.md).\n''')
    print(json.dumps(dict(checked_source_bindings=bindings,matching_source_bindings=bindings-len(issues),json_records=len(seen),tests=38,opens=31)))

if __name__=='__main__':run()
