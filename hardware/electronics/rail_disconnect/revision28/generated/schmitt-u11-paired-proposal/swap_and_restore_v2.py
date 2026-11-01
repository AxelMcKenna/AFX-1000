import sys,json,math,itertools,copy
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.focused import legal_line
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect
R=Path('/private/tmp/afx-u11-restoration');t=read_sexpr((R/'partial-restored-oldformat.kicad_pcb').read_text())
# This independent proposal ONLY swaps the2inputs of the same AND gate;
# owner must also update JSON/nativeSCH before integrated parity validation.
fp=next(f for f in children(t,'footprint') if any(p[1]=='Reference' and p[2]=='U11' for p in children(f,'property')))
a=next(p for p in children(fp,'pad') if p[1]=='4');b=next(p for p in children(fp,'pad') if p[1]=='5')
na=copy.deepcopy(first(a,'net'));nb=copy.deepcopy(first(b,'net'));a[a.index(first(a,'net'))]=nb;b[b.index(first(b,'net'))]=na
names={str(n[1]):str(n[2]).lstrip('/') for n in children(t,'net')}
removedN12=[]
for n in list(children(t,'segment')):
 if names[str(first(n,'net')[1])]=='N12_OV_OK_SCHMITT' and str(first(n,'layer')[1])=='F.Cu':t.remove(n);removedN12.append(sexpr(n))
# Retarget only the NEW proposed N12receiving barrel, keeping every originalvia.
for v in list(children(t,'via')):
 if names[str(first(v,'net')[1])]=='N12_OV_OK_SCHMITT' and math.dist(tuple(float(x)-100 for x in first(v,'at')[1:3]),(7.3,13.975))<1e-6:t.remove(v)
extra_stub=[]
for n in list(children(t,'segment')):
 if names[str(first(n,'net')[1])]=='P12_OV_OK_SCHMITT' and str(first(n,'layer')[1])=='F.Cu':
  start=tuple(float(x)-100 for x in first(n,'start')[1:3]);end=tuple(float(x)-100 for x in first(n,'end')[1:3])
  if max(math.dist(start,(8.6375,14)),math.dist(end,(8.6375,14)))<.05:t.remove(n);extra_stub.append(sexpr(n))
r=Router(t);r.via('N12_OV_OK_SCHMITT',(7.6,14));rows=[]
for net,points in [('N12_OV_OK_SCHMITT',[(8.6375,14),(7.6,14)]),('P12_OV_OK_SCHMITT',[(8.6375,14.65),(6.75,14.6)])]:
 good=all(legal_line(r,net,0,p,q,.2) for p,q in zip(points,points[1:]))
 rows.append(dict(net=net,layer='F.Cu',points=points,exact_clearance_good=good))
 print('swapped F',net,good,flush=True)
 if good:r.path(net,0,points,.2)
# Rejoin the N19 rawB component on the left of newbarrel toU36input.
p=next(p for p in r.by_ref['U36'] if p['pin']=='3')
got,why=connect(r,p,[dict(xy=(6.375,13.8),kind='RETAINED_B_TRACE')],radius=7,step=.025,budget=400000)
rows.append(dict(net='N19_OV_OK',route=got,reason=why));print('N19B',got,why,flush=True)
# Truth comparison for all8 independent raw comparator conditions, preserving
# the existingAND1commutation and AND2same-input-net identity.
truth=[]
for bits in itertools.product([False,True],repeat=8):
 before=(bits[0] and bits[1],bits[2] and bits[3],bits[4] and bits[5],bits[6] and bits[7])
 after=(bits[0] and bits[1],bits[3] and bits[2],bits[4] and bits[5],bits[6] and bits[7])
 assert before==after
 truth.append(dict(independent_OV_conditions=list(bits),gate_outputs=list(before)))
report=dict(status='PRIVATE_SAME_AND2_COMMUTATION_GEOMETRY_PROPOSAL',
 changed_pin_nets={'U11.4':{'old':na[-1],'new':nb[-1]},'U11.5':{'old':nb[-1],'new':na[-1]}},
 same_gate_output='U11.6',truth_cases=256,all_truth_cases_equal=True,truth_cases_data=truth,
 removed_old_or_candidate_N12_F_segments=removedN12,removed_P12_upper_old_stub=extra_stub,new_N12_proposed_barrel=[7.6,14],new_routes=rows,
 original_geometry_and_vias_preserved=True,proposed_new_extra_P12_via=None,
 source_producer_hysteresis_nets_unchanged=True,owner_must_update_SCH_JSON_and_native_parity=True,
 N12_U37_onward_untested=True,physical_qualified=False)
(R/'same-AND2-swap-v2-proposal.json').write_text(json.dumps(report,indent=2)+'\n')
(R/'same-AND2-swap-v2-proposal.kicad_pcb').write_text(sexpr(t)+'\n')
