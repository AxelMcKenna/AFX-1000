"""Retain explicitly selected complete joins from an immutable additive trial."""
import argparse,json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--label',required=True);ap.add_argument('--nets',required=True,nargs='+');args=ap.parse_args()
    for name in (args.source,args.label):assert name and all(c.isalnum() or c in '-_' for c in name)
    source=ROOT/'staging'/args.source;rp=source/'construction.json';r=json.loads(rp.read_text())
    assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    pcb=source/'digital_core.kicad_pcb';assert sha(pcb)==r['candidate_PCB_sha256']
    parents=[Path(p) for p in r['source_sha256'] if p.endswith('.kicad_pcb')];assert len(parents)==1
    base=read_sexpr(parents[0].read_text());board=read_sexpr(pcb.read_text());delta=geometry_delta(base,board)
    assert delta['other_root_geometry_exact']
    for tag in ('footprint','zone'):assert delta[tag]==dict(added=[],removed=[],changed=[])
    for tag in ('segment','via'):assert not delta[tag]['removed'] and not delta[tag]['changed']
    nets=set(args.nets);assert nets<={v['net'] for v in r['routes']}
    removed=[]
    for tag in ('segment','via'):
        for n in list(children(board,tag)):
            if first(n,'uuid')[1] in delta[tag]['added'] and first(n,'net')[1] not in nets:board.remove(n);removed.append(n)
    result_delta=geometry_delta(base,board);out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
    inputs=[Path(__file__),rp,pcb,parents[0]]
    result=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),routes=[v for v in r['routes'] if v['net'] in nets],added_segments=len(result_delta['segment']['added']),added_vias=len(result_delta['via']['added']),removed_trial_objects=removed,retained_nets=sorted(nets),source_geometry_exact=True,native_checks_pending=True,fabrication_released=False)
    with (out/'construction.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Retained',len(result['routes']),'joins;',len(removed),'unadopted trial objects removed')
if __name__=='__main__':run()
