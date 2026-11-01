import json,sys,copy,hashlib,shutil
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.power_distribution.p03.route import coded
R=Path(__file__).parent;D=R/'follow2-only';D.mkdir(exist_ok=True)
for p in (R/'source-parent').iterdir():
 if p.is_dir():shutil.copytree(p,D/p.name,dirs_exist_ok=True)
 elif p.is_file():shutil.copy2(p,D/p.name)
s=read_sexpr((R/'source-parent/rail_disconnect.kicad_pcb').read_text());t=coded(read_sexpr((R/'joint-restoration/multilayer.kicad_pcb').read_text()));oldids={str(first(n,'uuid')[1]) for kind in ['segment','via'] for n in children(s,kind)};srcnames={str(n[2]).lstrip('/'):str(n[1]) for n in children(s,'net')};newnames={str(n[1]):str(n[2]).lstrip('/') for n in children(t,'net')};added=[]
for n in t:
 if not isinstance(n,list) or not n or n[0] not in ['segment','via']:continue
 uid=str(first(n,'uuid')[1]);net=newnames[str(first(n,'net')[1])]
 if uid in oldids or net!='E28_ANA_FOLLOW2':continue
 obj=copy.deepcopy(n);first(obj,'net')[:]=[a('net'),a(srcnames[net])];s.append(obj);added.append(dict(uuid=uid,net=net,source_object=sexpr(obj)))
assert len(added)==81
(D/'rail_disconnect.kicad_pcb').write_text(sexpr(s)+'\n');(R/'follow2-only-authored-delta.json').write_text(json.dumps(dict(source_pcb_sha256=hashlib.sha256((R/'source-parent/rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),added=added,removed=[],all_original_geometry_unchanged=True,physical_qualified=False),indent=2)+'\n');print('extracted',len(added),'objects')
