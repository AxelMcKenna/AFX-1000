"""Reapply the explicit CT cell preparation onto the newer SS/TMR revision."""
import copy
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha


def run():
    root=Path(__file__).resolve().parent
    folders=[root/'staging'/n for n in ['nf-ct-local-native-01','nf-ct-cell-prepared-native-01','nf-softstart-cell-native-02']]
    projects=[p/'negative_startup_physical.kicad_pro' for p in folders]
    for p in projects:assert not native_evidence_errors(p,json.loads((p.parent/'review.json').read_text()))
    old,prepared,current=[read_sexpr(p.with_suffix('.kicad_pcb').read_text()) for p in projects]
    delta=geometry_delta(old,prepared)
    assert delta['other_root_geometry_exact'] and not any(delta['zone'].values())
    assert len(delta['footprint']['changed'])==2 and len(delta['via']['changed'])==1
    assert len(delta['segment']['removed'])==11 and len(delta['segment']['changed'])==6
    for tag in ['footprint','segment','via']:
        assert not delta[tag]['added']
        before={first(n,'uuid')[1]:n for n in children(old,tag)}
        after={first(n,'uuid')[1]:n for n in children(prepared,tag)}
        actual={first(n,'uuid')[1]:n for n in children(current,tag)}
        for key in delta[tag]['changed']+delta[tag]['removed']:
            assert actual[key]==before[key],('Overlapping newer edit',key)
            index=current.index(actual[key])
            if key in delta[tag]['removed']:current.pop(index)
            else:current[index]=copy.deepcopy(after[key])
    output=root/'staging/nf-ct-rebased-prepare-01';output.mkdir(exist_ok=False)
    pcb=output/'negative_startup_physical.kicad_pcb';pcb.write_text(sexpr(current)+'\n')
    inputs=[Path(__file__),root/'audit_candidate.py',*projects,*[p.with_suffix('.kicad_pcb') for p in projects]]
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},applied_delta=delta,
        all_newer_SS_TMR_objects_preserved=True,overlapping_edits=False,native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Rebased only the verified CT cell preparation; all newer SS/TMR copper retained')


if __name__=='__main__':run()
