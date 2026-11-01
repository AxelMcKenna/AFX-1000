import sys,json,hashlib,shutil,uuid
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
from hardware.electronics.rail_disconnect.revision28.repair import Router
ROOT=Path('/private/tmp/afx-u11-independent');d=json.loads((ROOT/'screen.json').read_text());SOURCE=Path(d['source']);dest=ROOT/'candidate0';dest.mkdir(exist_ok=True)
for p in SOURCE.iterdir():
 if p.is_file() and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym'] or p.name in ['components.json','fp-lib-table','sym-lib-table']):shutil.copy2(p,dest/p.name)
 elif p.is_dir() and p.suffix=='.pretty':shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
blob=(SOURCE/'rail_disconnect.kicad_pcb').read_bytes();assert hashlib.sha256(blob).hexdigest()==d['source_pcb_sha256'];t=read_sexpr(blob.decode());old_vias=[sexpr(n) for n in children(t,'via')];c=d['candidates'][0];ids={x['uuid'] for x in c['removed_objects']}
removed=[]
for n in list(t):
 if isinstance(n,list) and n and n[0]=='segment' and children(n,'uuid') and str(first(n,'uuid')[1]) in ids:t.remove(n);removed.append(sexpr(n))
assert len(removed)==len(ids)
r=Router(t);r.path(d['pad']['net'],0,c['F_path'],.2);r.via(d['pad']['net'],c['via'])
for i,n in enumerate(t):
 if isinstance(n,list) and n and n[0] in ['segment','via'] and not children(n,'uuid'):n.append([a('uuid'),a(str(uuid.uuid5(uuid.NAMESPACE_URL,'afx-u11-escape:'+d['source_pcb_sha256']+str(i)+sexpr(n))))])
assert [sexpr(n) for n in children(t,'via')][:-1]==old_vias
(dest/'rail_disconnect.kicad_pcb').write_text(sexpr(t)+'\n')
(ROOT/'candidate0-receipt.json').write_text(json.dumps(dict(source_pcb_sha256=d['source_pcb_sha256'],candidate_pcb_before_native_sha256=hashlib.sha256((dest/'rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),source_provenance=d['source'],removed_control_segments=removed,new_F_path=c['F_path'],new_via=c['via'],all_original_vias_exact_preserved=True,all_FP_and_zones_unchanged_before_refill=True,full_repair_closed=False,physical_qualified=False),indent=2)+'\n')
print('emitted',len(removed),'removed',len(old_vias),'oldvias')
