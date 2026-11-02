"""Rebase the verified eight-layer CT alternative onto the newer SS/TMR board."""
import copy
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha


def run():
    root=Path(__file__).resolve().parent
    projects=[root/'staging'/n/'negative_startup_physical.kicad_pro' for n in ['nf-ct-local-native-01','nf-eight-cell-native-02','nf-softstart-cell-native-02']]
    for p in projects:assert not native_evidence_errors(p,json.loads((p.parent/'review.json').read_text()))
    old,alternative,current=[read_sexpr(p.with_suffix('.kicad_pcb').read_text()) for p in projects]
    delta=geometry_delta(old,alternative)
    for tag in ['footprint','segment','via','zone']:
        before={first(n,'uuid')[1]:n for n in children(old,tag)}
        after={first(n,'uuid')[1]:n for n in children(alternative,tag)}
        actual={first(n,'uuid')[1]:n for n in children(current,tag)}
        for key in delta[tag]['changed']+delta[tag]['removed']:
            # Native refills may change only zone fill polygons.
            def authored_node(n):return [v for v in n if not (isinstance(v,list) and v[0]=='filled_polygon')]
            assert (authored_node(actual[key])==authored_node(before[key]) if tag=='zone' else actual[key]==before[key]),('Overlapping newer edit',tag,key)
            index=current.index(actual[key])
            if key in delta[tag]['removed']:current.pop(index)
            else:current[index]=copy.deepcopy(after[key])
        for key in delta[tag]['added']:
            assert key not in actual
            current.append(copy.deepcopy(after[key]))
    assert first(current,'layers')==first(old,'layers')
    current[current.index(first(current,'layers'))]=copy.deepcopy(first(alternative,'layers'))
    output=root/'staging/nf-eight-rebased-01';output.mkdir(exist_ok=False)
    pcb=output/'negative_startup_physical.kicad_pcb';pcb.write_text(sexpr(current)+'\n')
    inputs=[Path(__file__),root/'audit_candidate.py',*projects,*[p.with_suffix('.kicad_pcb') for p in projects]]
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},applied_delta=delta,
        all_newer_SS_TMR_copper_preserved=True,overlapping_authored_edits=False,material_stack_accepted=False,
        native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Rebased eight-layer CT alternative; newer SS/TMR and fault routing retained')


if __name__=='__main__':run()
