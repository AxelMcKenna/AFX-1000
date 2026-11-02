"""Remove one newly added via that native DRC finds connected only on F.Cu."""
import json
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent
UID='42e892a2-fab5-5846-91e5-5b401612a196'

def run():
    folder=ROOT/'staging/nf-u37-multilayer-native-01';source=folder/'negative_startup_physical.kicad_pcb';drc=folder/'drc.json'
    findings=json.loads(drc.read_text())['violations']
    assert len(findings)==1 and findings[0]['type']=='via_dangling' and findings[0]['items'][0]['uuid']==UID
    board=read_sexpr(source.read_text());node=next(v for v in children(board,'via') if first(v,'uuid')[1]==UID)
    assert first(node,'net')[-1]=='/N19_SAFE' and [float(v) for v in first(node,'at')[1:3]]==[30.8,21.6]
    previous=ROOT/'staging/nf-u41-multilayer-native-01/negative_startup_physical.kicad_pcb'
    assert UID not in {first(v,'uuid')[1] for v in children(read_sexpr(previous.read_text()),'via')}
    point=Point(30.8,21.6);attached=[]
    for s in children(board,'segment'):
        if first(s,'net')[-1]!='/N19_SAFE':continue
        line=LineString([[float(v) for v in first(s,k)[1:3]] for k in ['start','end']])
        if line.distance(point)<=.3+float(first(s,'width')[1])/2:
            attached.append(dict(uuid=first(s,'uuid')[1],layer=first(s,'layer')[1]))
    assert attached and {s['layer'] for s in attached}=={'F.Cu'}
    board.remove(node);out=ROOT/'staging/nf-u37-redundant-via-01';out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,drc,previous,Path(__file__)]},candidate_PCB_sha256=sha(pcb),removed_new_via=node,attached_tracks=attached,all_tracks_preserved=True,native_connectivity_recheck_required=True,fabrication_released=False),indent=2)+'\n')

if __name__=='__main__':run()
