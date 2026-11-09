"""Finish recursive verification with the established repository-relative source paths.

The first review writer emitted review.json before encountering an older
repository-relative binding. Preserve that review and its sealed writer.
"""
import json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
OUT=ROOT/'staging/digital-serial1-repair-review-01'
def run():
    assert not (OUT/'source-audit.json').exists()
    assert '## SERIAL_1: coordinated escape and restoration investigation' not in (ROOT/'WORKLOG.md').read_text()
    review=json.loads((OUT/'review.json').read_text())
    assert review['search_receipts']==18 and review['verified_opens_unchanged']==31 and not review['board_emitted']
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
                            p=Path(name)
                            if not p.is_absolute():
                                p=REPO/p if name.startswith(('hardware/','tests/')) else path.parent/p
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
    audit=dict(source_sha256={str(OUT/'review.json'):sha(OUT/'review.json'),str(Path(__file__)):sha(Path(__file__))},verified_source_bindings=bindings,source_bound_json_records=len(seen),missing_or_mismatched_sources=[],fabrication_released=False)
    with (OUT/'source-audit.json').open('x') as f:json.dump(audit,f,indent=2);f.write('\n')
    logbook=ROOT/'WORKLOG.md'
    with logbook.open('a') as f:
        f.write(f'''\n## SERIAL_1: coordinated escape and restoration investigation\n\nThe previous turn's 32-to-31-open checkpoint remains authoritative. This turn\nadds eighteen source-bound search receipts and a versioned zero-length-via-leg\nrouting fix. No new board was emitted or adopted. The source-side cut is\nMCU_PERMIT copper; the receiving-side cut includes CLOCK_5V and LED_48. Two\nCONTROL_30 front tracks conditionally open global serial access. A 0.05 mm\nlocal via grid finds 102 compatible receiving-end triples and independently\nreplays eighteen distinct arrangements, correcting the sparse sample's zero\nresult. The original legal CLOCK/LED48 via positions were absent from that\nsparse sample.\n\nSubsequent searches identify LED_37 via 4c8ecf3b-d93e-5c05-82da-95ddc9eeb8d1\nand LED_50 In3 track f1ea2e26-acf3-46e4-a518-bdb380e99c7e as additional\nrestoration obstructions. Trials explicitly require restoration of both nets.\nRouting MCU_PERMIT/CLOCK/LED48 together blocks SERIAL_1 in tested geometry;\nrouting SERIAL_1 earlier blocks LED48. Full retained-component targets include\nsampled track interiors. Failures are bounded, not global infeasibility proofs.\nSerial-only proposals around 338 mm remain unqualified and unadopted.\n\nThe continuous-route helper now skips zero-length legs at reused vias before\ncalling the polygon router. Six tests cover strict source/destination via\nbehavior and the four prior route cases; seven new compatibility tests cover\ntrack and through-via spacing. The focused 35-test suite passes. No native CAD\nrun is claimed this turn because no complete PCB candidate was constructed.\n\nThe detailed review records the invalid supply-pad-area probe and the exact\nprotected supply names used by the final cut-set reduction. The verified\n31-open board and all 213 unit-source hashes remain unchanged. Final source\nverification checks {bindings:,} bindings across {len(seen)} JSON records.\nAll started searches are terminal. Full-unit routing, approved ESS inputs,\nphysical stack/process, installed assembly and qualification remain unfinished.\nNo supplier message, order, commit or release occurred; the goal remains active.\n\nReview: [SERIAL_1 investigation](staging/digital-serial1-repair-review-01/README.md).\n''')
    print(json.dumps(dict(source_bindings=bindings,json_records=len(seen),focused_tests=35,opens=31)))

if __name__=='__main__':run()
