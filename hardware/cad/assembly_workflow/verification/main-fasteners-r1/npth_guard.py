"""Prove skipped NPTH pad geometry is entirely removed by its drill."""
import json,math,hashlib,importlib
from pathlib import Path
from hardware.fabrication import assembly_layout as al
from hardware.electronics.common import sexpr as sx
H=Path(__file__).resolve().parent
R=H.parents[4]
def validate(pad):
    assert pad[2]=='np_thru_hole'
    assert pad[3]=='circle','Unsupported NPTH copper envelope'
    size=list(map(float,sx.first(pad,'size')[1:3]))
    drill=sx.first(pad,'drill')
    assert drill and str(drill[1])!='oval','Unsupported non-round drill'
    diameter=float(drill[1]);offset=next(iter(sx.children(drill,'offset')),None)
    displacement=math.hypot(*map(float,offset[1:3])) if offset else 0.
    assert max(size)/2+displacement<=diameter/2,'NPTH pad has possible copper outside drill'
    return True

def audit(pcb):
    tree,_=al.outline(pcb);count=0
    for footprint in sx.children(tree,'footprint'):
        for pad in sx.children(footprint,'pad'):
            if pad[2]=='np_thru_hole':validate(pad);count+=1
    return count

def run():
    selected=json.loads((H/'previous-manifest.json').read_text())
    rows={k:{'pads_proved_drill_only':audit(R/p),'pcb_sha256':hashlib.sha256((R/p).read_bytes()).hexdigest()} for k,p in selected['boards'].items()}
    sources=[Path(__file__),H/'test_npth_guard.py',H/'previous-manifest.json']
    report={'boards':rows,'all_skipped_NPTH_have_no_annular_copper':True,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (H/'npth-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows))
if __name__=='__main__':run()
