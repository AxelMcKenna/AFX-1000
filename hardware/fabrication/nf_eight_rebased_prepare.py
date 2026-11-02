"""Eight-layer routing-feasibility proposal, preserving the 1.2 mm outline.

No dielectric/material stack is accepted. Old In4 AUX copper moves to In6;
new In4/In5 are signal-routing space. All-layer mechanical keepouts expand.
"""
import copy
import json
import uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha,native_evidence_errors
ROOT=Path(__file__).resolve().parent


def replace_layer(node):
    if isinstance(node,list):return [replace_layer(v) for v in node]
    return 'In6.Cu' if node=='In4.Cu' else node


def run():
    source=ROOT/'staging/nf-ct-rebased-prepared-native-01';project=source/'negative_startup_physical.kicad_pro';pcb=project.with_suffix('.kicad_pcb')
    assert not native_evidence_errors(project,json.loads((source/'review.json').read_text()))
    original=read_sexpr(pcb.read_text());board=replace_layer(original)
    layers=first(board,'layers');old=next(n for n in layers if isinstance(n,list) and len(n)>1 and n[1]=='In6.Cu');old[0]=a(14)
    index=layers.index(old);layers[index:index]=[[a(10),'In4.Cu',a('signal')],[a(12),'In5.Cu',a('signal')]]
    new_areas=[]
    for z in children(original,'zone'):
        if not children(z,'keepout') or not children(z,'layer') or first(z,'layer')[1]!='In3.Cu':continue
        for layer in ['In4.Cu','In5.Cu']:
            n=copy.deepcopy(z);first(n,'layer')[1]=layer
            first(n,'uuid')[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:NF:8layer-KO:'+str(first(z,'uuid')[1])+':'+layer))
            board.append(n);new_areas.append(first(n,'uuid')[1])
    assert len(new_areas)==12
    output=ROOT/'staging/nf-eight-rebased-prepared-01';output.mkdir(exist_ok=False)
    (output/pcb.name).write_text(sexpr(board)+'\n')
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,project,Path(__file__)]},old_copper_layer_map={'In4.Cu':'In6.Cu'},new_signal_layers=['In4.Cu','In5.Cu'],new_keepout_uuids=new_areas,
        nominal_total_thickness_mm=1.2,material_copper_dielectric_stack_defined=False,manufacturer_stack_accepted=False,PDN_and_thermal_qualified=False,
        native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Prepared eight-layer feasibility proposal with 12 matching new keepouts')


if __name__=='__main__':run()
