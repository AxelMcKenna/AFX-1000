"""Keep real seats and future tapped-thread overlap distinct from empty checks."""
import json,math
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent

def run():
    data,c,_,_=w.load_manifest(H/'candidate.json')
    identities=[]
    for name in ['cap_handle_body_r2','cap_handle_r2','cap_handle_screw_r2','cap_handle_withdrawal_r2']:
        identity,_=w.job('component',c[name],c)
        result,_=w.execute('component',c[name],c,expected=identity)
        assert result['passed'] and not result['runtime_failure'],name
        identities.append(identity)
    rows=[]
    for name,left,right,z in [('handle_body_seat','cap_handle_r2','cap_handle_body_r2',55.6),
                              ('screw_handle_seat','cap_handle_screw_r2','cap_handle_r2',56.5),
                              ('withdrawal_body_seat','cap_handle_withdrawal_r2','cap_handle_body_r2',55.6),
                              ('future_tapped_thread','cap_handle_screw_r2','cap_handle_body_r2',None)]:
        check=dict(id=name,left=[left],right=[right],expect='empty')
        identity,folder=w.job('check',check,c);r,reused=w.execute('check',check,c,expected=identity)
        assert not r['runtime_failure'],name
        out=H/name;out.mkdir(exist_ok=True)
        for item in ['result.json','geometry.scad','geometry.stl','native.log']:
            src=folder/item
            if src.exists():
                dest=out/item
                if dest.exists():assert dest.read_bytes()==src.read_bytes()
                else:dest.write_bytes(src.read_bytes())
        m=r['mesh']
        if r['passed']:
            assert name=='withdrawal_body_seat' and m is None,name
            accepted=True  # Native-empty motion sweep; nominal seated contact retained separately.
        elif z is not None:
            accepted=m['min_mm'][2]==m['max_mm'][2] and math.isclose(m['min_mm'][2],z,abs_tol=1e-5)
        else:
            accepted=m['closed_oriented_boundary'] and math.isclose(m['min_mm'][2],50.5,abs_tol=1e-5) and math.isclose(m['max_mm'][2],55.6,abs_tol=1e-5)
            accepted &= all(m['min_mm'][i]>=v-1e-5 and m['max_mm'][i]<=v+2+1e-5 for i,v in enumerate([315,81]))
        rows.append(dict(check=name,expected_seat_z=z,classification_matches=accepted,mesh=m,identity=identity,
                         native_empty_pass=r['passed'],thread_strength_proven=False))
        identities.append(identity);print(name,accepted,flush=True)
    for identity in identities:w.assert_current(identity)
    w.assert_current({'sources':data['_loaded_sources']})
    report=dict(results=rows,source_sha256={**data['_loaded_sources'],w.relative(Path(__file__)):w.sha(Path(__file__))},
                future_tapped_thread_overlap_not_clearance_pass=True,physical_qualified=False)
    (H/'contact-review.json').write_text(json.dumps(report,indent=2)+'\n')
    assert all(r['classification_matches'] for r in rows)
if __name__=='__main__':run()
