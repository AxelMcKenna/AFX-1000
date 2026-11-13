"""Screen full conductive mounting hardware without selecting it."""
import json,copy,re
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent

def run():
    data,parts,_,_=w.load_manifest(H/'previous-manifest.json')
    parts=copy.deepcopy(parts)
    budget=json.loads((H/'budget.json').read_text())
    w.assert_current({'sources':budget['source_sha256']})
    keep=json.loads((H/'contact-keepouts.json').read_text())
    mounts=json.loads(re.search(r'^mounts = (.*);',(w.ROOT/'hardware/cad/two_board_print_01/captured.scad').read_text(),re.M).group(1))
    for f in keep['features']:
        m=next(m for m in mounts if m[0]==f['properties']['mount'])
        assert m[1:3]==f['properties']['center_mm']
        assert m[3]==({'signal':6.75,'power':7.9}[f['properties']['board']])
    original=sorted(parts)
    parts['base_board_heads']=dict(parts['base_board_heads'],source=w.relative(H/'parts.scad'),module='main_fasteners_nominal_r1',description='Conditional full22mainmounts; excludes sensor-owned D_H2/D_H5')
    parts['main_fastener_receiving_r1']=dict(id='main_fastener_receiving_r1',source=w.relative(H/'parts.scad'),module='main_fastener_receiving_r1',role='receiving',scene=False,description='Conservative screw/washer/nut bounds; own PCB and nut seats verified separately')
    bindings=dict(data['_loaded_sources'])
    for p in [Path(__file__),H/'parts.scad',H/'budget.json',H/'contact-keepouts.json',H/'source-review.json']:
        w.merge_sources(bindings,{w.relative(p):w.sha(p)})
    registry=dict(schema_version=1,components=list(parts.values()),source_sha256=bindings,intentional_contacts=sum((x['intentional_contacts'] for x in data['contracts']),[]))
    (H/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    excluded=['base_board_heads','base_main_pcbs','cooling_shell']
    external=[x for x in original if x not in excluded]
    assert len(external)==74 and len(set(external))==74
    checks=[dict(id=f'main_fastener_external_{i//8+1}',left=['main_fastener_receiving_r1'],right=external[i:i+8],expect='empty') for i in range(0,len(external),8)]
    candidate={k:v for k,v in data.items() if not k.startswith('_') and k!='contracts'}
    candidate.update(registries=[w.relative(H/'registry.json')],checks=checks)
    (H/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    (H/'scope.json').write_text(json.dumps(dict(external_roles=external,excluded=excluded,reasons={'base_board_heads':'Replaced candidate nominal hardware; not an external obstacle','base_main_pcbs':'Own washer/board seats: separate nominal contact evidence','cooling_shell':'Own captured nut/post seats: separate nominal contact evidence'},hardware_selected=False,copper_contact_screen_passed=False),indent=2)+'\n')
    print('Prepared10checksagainst74externalroles; ownseatsandcopperremainseparategates')
if __name__=='__main__':run()
