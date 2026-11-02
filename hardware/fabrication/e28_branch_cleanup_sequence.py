"""Bounded E28 cleanup passes, each separated by full isolated native checks."""
import argparse,json,subprocess,sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
HELPER=Path('/private/tmp/afx-isolated-kicad.py')

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--label',required=True);ap.add_argument('--start-pass',type=int,required=True);ap.add_argument('--max-passes',type=int,default=6);args=ap.parse_args()
    assert all(v and all(ch.isalnum() or ch in '-_' for ch in v) for v in [args.source,args.label])
    assert 1<=args.max_passes<=6 and 1<=args.start_pass<=30
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False)
    record=dict(source_sha256={str(p):sha(p) for p in [Path(__file__),HELPER,ROOT/'e28_branch_cleanup_v2.py',ROOT/'capture_rework.py',ROOT/'native_review.py']},passes=[],complete=False,fabrication_released=False)
    def save():(out/'sequence.json').write_text(json.dumps(record,indent=2)+'\n')
    def invoke(module,arguments,native):
        command=[sys.executable,str(HELPER),module,*arguments] if native else [sys.executable,'-m',module,*arguments]
        subprocess.run(command,cwd=REPO,check=True,timeout=190 if native else 90)
    source=args.source
    try:
        for i in range(args.start_pass,args.start_pass+args.max_passes):
            folder=ROOT/'staging'/source;drc=json.loads((folder/'drc.json').read_text())
            assert not drc['unconnected_items'] and not drc['schematic_parity']
            assert all(v['type'] in ['track_dangling','via_dangling'] and v['severity']=='warning' for v in drc['violations'])
            if not drc['violations']:record['complete']=True;break
            cp=f'e28-branch-inputs-pass-{i:02d}';candidate=f'e28-branch-cleanup-{i:02d}';native=f'e28-branch-cleanup-native-{i:02d}'
            print('PASS',i,'source',source,'warnings',len(drc['violations']),flush=True)
            invoke('hardware.fabrication.capture_rework',['--source',str(folder),'--label',cp,'--expected-opens','0','--expected-footprints','275','--board-name','rail_disconnect','--allow-via-dangling','--allow-track-dangling'],True)
            invoke('hardware.fabrication.e28_branch_cleanup_v2',['--capture',cp,'--label',candidate],False)
            proof=ROOT/'staging'/candidate/'construction.json';data=json.loads(proof.read_text());assert data['removed_objects']
            invoke('hardware.fabrication.native_review',['--source-project',str(folder/'rail_disconnect.kicad_pro'),'--candidate',str(ROOT/'staging'/candidate/'rail_disconnect.kicad_pcb'),'--label',native],True)
            review=ROOT/'staging'/native/'review.json';result=json.loads(review.read_text());counts=result['status']['counts']
            assert counts['unconnected_items']==counts['schematic_parity']==counts['erc']==0
            report=json.loads(review.with_name('drc.json').read_text())
            assert all(v['type'] in ['track_dangling','via_dangling'] and v['severity']=='warning' for v in report['violations'])
            record['passes'].append(dict(source=source,capture=cp,candidate=candidate,native=native,removed=len(data['removed_objects']),remaining_warnings=counts['violations'],construction_sha256=sha(proof),review_sha256=sha(review)))
            source=native;record['latest_checked_source']=source;record['complete']=not counts['violations'];save()
            if record['complete']:break
    finally:save()
    print('Sequence finished;',source,'native-clean',record['complete'],flush=True)

if __name__=='__main__':run()
