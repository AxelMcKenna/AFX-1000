"""Export source-bound eight-layer E28 copper views without editing the board."""
import argparse,json,subprocess,sys
from pathlib import Path
from hardware.fabrication.audit_candidate import native_evidence_errors,sha

ROOT=Path(__file__).resolve().parent

def run():
    assert sys.platform=='linux'
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--label',required=True);args=ap.parse_args()
    assert all(v and all(ch.isalnum() or ch in '-_' for ch in v) for v in [args.source,args.label])
    folder=ROOT/'staging'/args.source;project=folder/'rail_disconnect.kicad_pro';review=folder/'review.json'
    assert not native_evidence_errors(project,json.loads(review.read_text()))
    pcb=project.with_suffix('.kicad_pcb');digest=sha(pcb);out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False)
    layers=[('front','F.Cu,F.Fab,Edge.Cuts')]+[(f'inner{i}',f'In{i}.Cu,Edge.Cuts') for i in range(1,7)]+[('back','B.Cu,B.Fab,Edge.Cuts')]
    for name,layer in layers:
        subprocess.run(['kicad-cli','pcb','export','pdf','--layers',layer,'--mode-single','--output',str(out/(name+'.pdf')),str(pcb)],check=True,timeout=30)
    assert sha(pcb)==digest
    (out/'export.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,project,review,Path(__file__)]},outputs_sha256={p.name:sha(p) for p in sorted(out.glob('*.pdf'))},fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':run()
