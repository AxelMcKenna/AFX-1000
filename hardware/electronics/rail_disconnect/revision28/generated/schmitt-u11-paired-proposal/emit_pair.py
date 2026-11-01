import sys,json,hashlib,shutil,uuid
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
R=Path('/private/tmp/afx-u11-restoration');d=json.load(open('/private/tmp/afx-u11-independent/screen.json'));source=Path(d['source']);dest=R/'candidate2-paired';dest.mkdir(exist_ok=True)
for p in source.iterdir():
 if p.is_file() and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym'] or p.name in ['components.json','fp-lib-table','sym-lib-table']):shutil.copy2(p,dest/p.name)
 elif p.is_dir() and p.suffix=='.pretty':shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
t=read_sexpr((R/'same-AND2-swap-v2-proposal.kicad_pcb').read_text())
for i,n in enumerate(t):
 if isinstance(n,list) and n and n[0] in ['via','segment'] and not children(n,'uuid'):n.append([a('uuid'),a(str(uuid.uuid5(uuid.NAMESPACE_URL,'afx-u11-restoration2:'+d['source_pcb_sha256']+str(i)+sexpr(n))))])
(dest/'rail_disconnect.kicad_pcb').write_text(sexpr(t)+'\n')
# Pair exacttwo schematic receiving labels with the same AND2 commutation.
sch=read_sexpr((source/'rail_disconnect.kicad_sch').read_text());changes=[]
for uid,old,new in [('bc592365-106c-58f1-a0e7-b9560b5b0271','P12_OV_OK_SCHMITT','N12_OV_OK_SCHMITT'),('450dd0ba-36b5-532d-9f06-727029480260','N12_OV_OK_SCHMITT','P12_OV_OK_SCHMITT')]:
 n=next(n for n in children(sch,'label') if str(first(n,'uuid')[1])==uid);assert n[1]==old
 before=sexpr(n);n[1]=new;changes.append(dict(uuid=uid,before=before,after=sexpr(n)))
(dest/'rail_disconnect.kicad_sch').write_text(sexpr(sch)+'\n')
parts=json.load(open(source/'components.json'));u=next(p for p in parts if p['ref']=='U11')
pa=next(p for p in u['pins'] if p['number']=='4');pb=next(p for p in u['pins'] if p['number']=='5');assert pa['net']=='P12_OV_OK_SCHMITT' and pb['net']=='N12_OV_OK_SCHMITT';pa['net'],pb['net']=pb['net'],pa['net']
(dest/'components.json').write_text(json.dumps(parts,indent=2)+'\n')
(R/'paired-schematic-delta.json').write_text(json.dumps(dict(source_pcb_sha256=d['source_pcb_sha256'],labels=changes,only_components_delta='U11sameAND2pin4/5nets',physical_qualified=False),indent=2)+'\n')
print('emitted paired')
