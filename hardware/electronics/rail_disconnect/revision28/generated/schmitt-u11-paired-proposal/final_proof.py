import sys,json,hashlib,itertools,copy,collections
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.common.netlists import netlist
R=Path('/private/tmp/afx-u11-restoration');D=Path('/private/tmp/afx-u11-independent');s=json.load(open(D/'screen.json'));SOURCE=Path(s['source']);blob=(SOURCE/'rail_disconnect.kicad_pcb').read_bytes();assert hashlib.sha256(blob).hexdigest()==s['source_pcb_sha256']
old=read_sexpr(blob.decode());new=read_sexpr((R/'final-paired/rail_disconnect.kicad_pcb').read_text());oldNames={str(n[1]):str(n[2]) for n in children(old,'net')}
def uid(n):return str(first(n,'uuid')[1])
def byid(t,kind):return {uid(n):n for n in children(t,kind) if children(n,'uuid')}
bs=byid(old,'segment');cs=byid(new,'segment');bv=byid(old,'via');cv=byid(new,'via')
def desc(n,legacy=False):
 return dict(uuid=uid(n),net=oldNames[str(first(n,'net')[1])] if legacy else str(first(n,'net')[1]),source_object=sexpr(n))
removed=[desc(n,True) for k,n in bs.items() if k not in cs];added=[desc(n) for k,n in cs.items() if k not in bs];vias=[desc(n) for k,n in cv.items() if k not in bv]
assert len(removed)==40 and len(added)==17 and len(vias)==1 and len(bv)==1447
assert set(bv)<=set(cv)
baseline=read_sexpr((D/'baseline/rail_disconnect.kicad_pcb').read_text())
def physical(n,stripnet=False):
 if isinstance(n,list):return [physical(c,stripnet) for c in n if not(isinstance(c,list) and c and (c[0]=='uuid' or (stripnet and c[0]=='net')))]
 return n
def byref(t):return {next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(t,'footprint')}
bfp=byref(baseline);cfp=byref(new);assert set(bfp)==set(cfp) and len(bfp)==273
for ref in bfp:assert sexpr(physical(bfp[ref],ref=='U11'))==sexpr(physical(cfp[ref],ref=='U11')),ref
parts,pins=netlist(R/'final-netlist.xml');alltargets={name:[dict(ref=ref,pin=p) for ref,ps in pins.items() for p,n in ps.items() if n==name] for name in ['P12_OV_OK_SCHMITT','N19_OV_OK','N12_OV_OK_SCHMITT']}
drc=json.load(open(R/'final-drc.json'));open_target=[]
for n in drc['unconnected_items']:
 if any(any(name in i.get('description','') for name in alltargets) for i in n['items']):open_target.append(n)
assert len(open_target)==1 and all('N12_OV_OK_SCHMITT' in i['description'] for i in open_target[0]['items'])
# Functional comparison uses the actual native post-swap receiver input names.
oldc=json.load(open(SOURCE/'components.json'));newc=json.load(open(R/'final-paired/components.json'));uo=next(c for c in oldc if c['ref']=='U11');un=next(c for c in newc if c['ref']=='U11')
om={p['number']:p['net'] for p in uo['pins']};nm={p['number']:p['net'] for p in un['pins']}
assert nm['4']==om['5'] and nm['5']==om['4'];assert {k:v for k,v in nm.items() if k not in ['4','5']}=={k:v for k,v in om.items() if k not in ['4','5']}
old_other=[c for c in oldc if c['ref']!='U11'];new_other=[c for c in newc if c['ref']!='U11'];assert old_other==new_other
inputs=[om[p] for p in ['1','2','4','5','9','10','12','13']]
def outputs(m,v):return [v[m[a]] and v[m[b]] for a,b in [('1','2'),('4','5'),('9','10'),('12','13')]]
wrong=dict(nm);wrong['4'],wrong['9']=wrong['9'],wrong['4'];bad=0
for bits in itertools.product([False,True],repeat=8):
 v=dict(zip(inputs,bits));assert outputs(om,v)==outputs(nm,v)
 if outputs(om,v)!=outputs(wrong,v):bad+=1
assert bad>0
report=dict(status='PAIRED_SAME_AND_RESTORATION_PARTIAL_SOURCE_NOT_FULL_ROUTING',source_pcb_sha256=s['source_pcb_sha256'],
 final_native_refilled_sha256=hashlib.sha256((R/'final-paired/rail_disconnect.kicad_pcb').read_bytes()).hexdigest(),
 removed_source_segments=removed,added_final_segments=added,added_final_vias=vias,
 removed_counts_by_net=dict(collections.Counter(x['net'] for x in removed)),added_counts_by_net=dict(collections.Counter(x['net'] for x in added)),
 all1447oldvias_preserved=True,no_original_force_quiet_GND_objects_removed=True,
 exact_U11_component_pin_delta={k:dict(old=om[k],new=nm[k]) for k in ['4','5']},other268components_exact=True,
 all273physical_FP_geometries_properties_unchanged_except_two_net_bindings=True,
 actual_native_target_pad_inventory=alltargets,remaining_native_target_open=open_target,
 truth256_equal=True,wrong_cross_gate_mutation_detected_cases=bad,
 source_specific_native_hard=0,source_specific_native_warnings=151,source_specific_native_opens=41,source_specific_native_parity=0,
 native_ERC=0,native_pin_value_mismatch=0,inherited_ignored_checks=5,
 full_current_owner_source_merge_recheck_required=True,
 all_three_target_nets_closed=False,P12buffered_and_N19raw_native_closed=True,
 N12buffered_U37_onward_open=True,physical_qualified=False)
(R/'final-delta-proof.json').write_text(json.dumps(report,indent=2)+'\n')
print('removed',report['removed_counts_by_net'],'added',report['added_counts_by_net'],'wrongmutation',bad)
print('targetpads',alltargets)
# Preserve original claimed source, not only its fresh normalized baseline.
p=R/'source-parent41';p.mkdir(exist_ok=True)
for f in ['rail_disconnect.kicad_pcb','rail_disconnect.kicad_sch','components.json']:(p/f).write_bytes((SOURCE/f).read_bytes())
# Ensure previous68-file proposal evidence remains immutable.
h=json.load(open(D/'handoff.json'))
for p,hh in h['files_sha256'].items():assert hashlib.sha256((D/p).read_bytes()).hexdigest()==hh,p
