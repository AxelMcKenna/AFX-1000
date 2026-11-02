"""Prepare two supervisor cells for coordinated CT/reset/supply routing.

Original circuit, widths and process rules are preserved. Explicitly identified
local segments are removed only in this separate, unaccepted rework candidate.
"""
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,native_evidence_errors
ROOT=Path(__file__).resolve().parent
REMOVE={
 '40dec890-685c-4e00-bd00-5bba743c5942','d6acf0d3-4d2d-4ee3-acec-aa6a6d57ed99',
 '5846c246-f0d3-4c4a-b30f-b5f9da0a26f7','c33ee2d0-64ad-4ff9-a672-c4408ed8b18e',
 '87d1ecab-0f63-4976-9ad3-a3fb4ea2df9e','4d84f83b-704e-49ce-a161-776f2f9627e7',
 '61c998cc-0264-4001-80ee-fc4ae1c2be24','27978a33-0bb9-4e09-a83b-59eeafce834b',
 'aa902964-6917-4798-a8ed-e9bb7d7c7cf6','2f9d5e97-dd13-4df0-b529-33514d1b9f15',
 '9a2fee96-1b87-4f0b-921a-cabca8034030'}


def run():
    folder=ROOT/'staging/nf-ct-bypass-native-02';project=folder/'negative_startup_physical.kicad_pro'
    assert not native_evidence_errors(project,json.loads((folder/'review.json').read_text()))
    pcb=project.with_suffix('.kicad_pcb');board=read_sexpr(pcb.read_text());removed=[];changed=[]
    via_id='d2790e69-30b9-4c0b-86cb-fd3a942df47c';old=[19.775,27.];new=[19.725,27.15]
    for s in list(children(board,'segment')):
        uid=first(s,'uuid')[1]
        if uid in REMOVE:
            assert first(s,'net')[-1] in {'/N12_BIAS_RESET_N','/N12_PERMIT_D','/N12_INTVCC','/N12_BIAS_SENSE'}
            removed.append(s);board.remove(s);continue
        for key in ['start','end']:
            pt=first(s,key)
            if math.dist(list(map(float,pt[1:3])),old)<1e-6:
                assert first(s,'net')[-1]=='/N12_INTVCC'
                changed.append(dict(uuid=uid,endpoint=key,before=list(pt[1:3]),after=new));pt[1:3]=new
    via=next(v for v in children(board,'via') if first(v,'uuid')[1]==via_id)
    assert list(map(float,first(via,'at')[1:3]))==old;first(via,'at')[1:3]=new
    assert len(removed)==11 and len(changed)==3
    output=ROOT/'staging/nf-ct-cell-prepare-01';output.mkdir(exist_ok=False)
    (output/pcb.name).write_text(sexpr(board)+'\n')
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,project,Path(__file__)]},removed_segments=removed,via_move=dict(uuid=via_id,before=old,after=new),changed_trace_endpoints=changed,
        routed=False,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Prepared 11 local segment repairs and one small bypass-via move')


if __name__=='__main__':run()
