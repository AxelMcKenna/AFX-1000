from pathlib import Path
import sys,json,shutil,uuid,hashlib,math
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.focused import legal_line
R=Path('/private/tmp/afx-e28-p12-layerhop');d=json.load(open(R/'screen.json'));S=Path(d['source']);dest=R/'candidate-paired';dest.mkdir(exist_ok=True)
for p in S.iterdir():
 if p.is_file() and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym'] or p.name in ['components.json','fp-lib-table','sym-lib-table']):shutil.copy2(p,dest/p.name)
 elif p.is_dir() and p.suffix=='.pretty':shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
t=read_sexpr((R/'candidate1-oldformat.kicad_pcb').read_text());rows=json.load(open(R/'routes-attempt.json'));routes=[]
for row in rows:
 if not row['route']:continue
 net=row['net'];layer=row['layer'];points=row['route']['path'];names={str(n[1]):str(n[2]).lstrip('/') for n in children(t,'net')}
 # Remove only the just-authored missing-UUID centreline pieces; keep all
 # original vias/tracks exactly. Replay a same-width shortcut with20um reserve.
 for n in list(children(t,'segment')):
  if not children(n,'uuid') and names[str(first(n,'net')[1])]==net and str(first(n,'layer')[1])==('F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu')[layer]:t.remove(n)
 rr=Router(t);smooth=[points[0]];i=0
 while i<len(points)-1:
  j=next((j for j in range(len(points)-1,i,-1) if legal_line(rr,net,layer,points[i],points[j],.24)),None)
  if j is None:raise RuntimeError((net,i,'shortcutnotclear'))
  smooth.append(points[j]);i=j
 rr.path(net,layer,smooth,.2)
 routes.append(dict(net=net,layer=layer,points=smooth,original_proposed_length_mm=sum(math.dist(a0,b0) for a0,b0 in zip(points,points[1:])),final_length_mm=sum(math.dist(a0,b0) for a0,b0 in zip(smooth,smooth[1:])),clearance_screen_extra_mm=.02))
for i,n in enumerate(t):
 if isinstance(n,list) and n and n[0] in ['segment','via'] and not children(n,'uuid'):n.append([a('uuid'),a(str(uuid.uuid5(uuid.NAMESPACE_URL,'afx-E28-P12-layerhop:'+d['source_pcb_sha256']+str(i)+sexpr(n))))])
(dest/'rail_disconnect.kicad_pcb').write_text(sexpr(t)+'\n')
report=dict(source_pcb_sha256=d['source_pcb_sha256'],withdrawn_control_fragments=d['blockers'],new_receiving_via_local_mm=[13.35,10.8],Bstem=[[14,10.6],[13.35,10.8]],new_routed_paths=routes,
 all_original_vias_and_parts_preserved=True,V5buffered_debt_not_claimed_restored=True,
 actual_native_P12_MASTER_P19_pad_connectivity_pending=True,physical_qualified=False)
(R/'authored-delta.json').write_text(json.dumps(report,indent=2)+'\n')
print([(x['net'],len(x['points']),x['final_length_mm']) for x in routes],flush=True)
