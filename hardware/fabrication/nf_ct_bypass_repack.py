"""Separate local bypass placement trial to open CT/reset escape room.

Move two existing rear capacitors 0.8 mm left and extend only their four
attached rear traces. Values, nets, via positions and widths remain unchanged.
"""
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,native_evidence_errors
ROOT=Path(__file__).resolve().parent


def run():
    source=ROOT/'staging/nf-ct-local-native-01';pcb=source/'negative_startup_physical.kicad_pcb';project=pcb.with_suffix('.kicad_pro')
    assert not native_evidence_errors(project,json.loads((source/'review.json').read_text()))
    cp=ROOT/'staging/nf-ct-local-inputs-166/capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    board=read_sexpr(pcb.read_text());moves={};placements=[]
    for fp in children(board,'footprint'):
        ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
        if ref not in {'C36','C38'}:continue
        assert first(fp,'layer')[1]=='B.Cu'
        at=first(fp,'at');before=list(map(float,at[1:3]));at[1]=round(before[0]-.8,6)
        placements.append(dict(ref=ref,before_mm=before,after_mm=[float(at[1]),float(at[2])]))
        for pad in c['objects']:
            if pad.get('ref')!=ref:continue
            old=pad['position_mm'];new=[round(old[0]-.8,6),old[1]]
            matches=[o for o in c['objects'] if o['kind']=='PCB_TRACK' and 'B.Cu' in o['layers'] and any(math.dist(old,pt)<1e-6 for pt in [o['position_mm'],o['end_mm']])]
            assert len(matches)==1
            moves[matches[0]['uuid']]=dict(old=old,new=new,net=pad['net'])
    changed=[]
    for track in children(board,'segment'):
        uid=first(track,'uuid')[1]
        if uid not in moves:continue
        move=moves[uid];assert first(track,'net')[-1]==move['net'] and first(track,'layer')[1]=='B.Cu'
        original=sexpr(track)
        for key in ['start','end']:
            pt=first(track,key)
            if math.dist(list(map(float,pt[1:3])),move['old'])<1e-6:pt[1:3]=move['new']
        assert sexpr(track)!=original;changed.append(uid)
    assert len(placements)==2 and len(changed)==4
    output=ROOT/'staging/nf-ct-bypass-repack-01';output.mkdir(exist_ok=False)
    (output/pcb.name).write_text(sexpr(board)+'\n')
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,project,cp,Path(__file__)]},placements=placements,changed_rear_trace_uuids=changed,
        actual_bypass_loop_and_installed_receiving_qualified=False,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Moved C36/C38 left 0.8 mm; extended their four rear traces at original widths')


if __name__=='__main__':run()
