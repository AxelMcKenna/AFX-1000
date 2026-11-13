"""Retain own nominal seats separately from strict external clearance checks."""
import json,math,struct,re
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent

def run():
    data,parts,_,_=w.load_manifest(H/'candidate.json')
    mounts=json.loads(re.search(r'^mounts = (.*);',(w.ROOT/'hardware/cad/two_board_print_01/captured.scad').read_text(),re.M).group(1))
    mounts=[m for m in mounts if m[0] not in ['D_H2','D_H5']]
    identities=[];rows=[]
    for name in ['base_board_heads','base_main_pcbs','cooling_shell']:
        ident,_=w.job('component',parts[name],parts);r,_=w.execute('component',parts[name],parts,expected=ident)
        assert r['passed'] and not r['runtime_failure'];identities.append(ident)
    for case,right in [('nominal_washer_board_seats','base_main_pcbs'),('nominal_nut_roof_seats','cooling_shell')]:
        check=dict(id='main_fastener_'+case,left=['base_board_heads'],right=[right],expect='empty')
        ident,folder=w.job('check',check,parts);r,_=w.execute('check',check,parts,expected=ident)
        assert not r['runtime_failure'];identities.append(ident)
        out=H/case;out.mkdir(exist_ok=True)
        for name in ['result.json','geometry.scad','geometry.stl','native.log']:
            src=folder/name
            if src.exists():
                dest=out/name
                if dest.exists():assert dest.read_bytes()==src.read_bytes()
                else:dest.write_bytes(src.read_bytes())
        seen=set();valid=True
        if not r['empty']:
            raw=(folder/'geometry.stl').read_bytes()
            for i in range(struct.unpack_from('<I',raw,80)[0]):
                values=struct.unpack_from('<12fH',raw,84+50*i);vertices=[values[j:j+3] for j in [3,6,9]]
                matches=[m[0] for m in mounts if all(abs(v[2]-(m[3]+1.6 if right=='base_main_pcbs' else 1.8))<5e-5 and math.dist(v[:2],m[1:3])< (2.25 if right=='base_main_pcbs' else 4/math.sqrt(3))+5e-5 for v in vertices)]
                if len(matches)!=1:valid=False
                else:seen.add(matches[0])
        rows.append(dict(case=case,native_empty=r['empty'],all_retained_vertices_on_expected_seat_planes=valid,mounts_with_retained_seat_mesh=sorted(seen),expected_mount_count=22,not_a_strict_empty_clearance_pass=not r['passed'],physical_contact_qualified=False,mesh=r['mesh'],result_sha256=w.sha(folder/'result.json')))
        assert valid,case
        print(case, 'EMPTY' if r['empty'] else f'expected seat planes only; {len(seen)} mounts',flush=True)
    for identity in identities:w.assert_current(identity)
    w.assert_current({'sources':data['_loaded_sources']})
    report=dict(results=rows,physical_qualified=False,source_sha256={**data['_loaded_sources'],w.relative(Path(__file__)):w.sha(Path(__file__))})
    (H/'contact-review.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':run()
