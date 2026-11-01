from pathlib import Path
import sys,json,math,shutil,uuid
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
R=Path('/private/tmp/afx-p03-strict-current');source=R/'centered1';dest=R/'centered2';dest.mkdir(exist_ok=True)
for p in source.iterdir():
 if p.is_dir():shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
 else:shutil.copy2(p,dest/p.name)
t=read_sexpr((source/'power_p03.kicad_pcb').read_text());nodes={str(first(n,'uuid')[1]):n for n in t if isinstance(n,list) and n and n[0] in ['segment','via'] and children(n,'uuid')};d=json.load(open(R/'centered1-drc.json'));changes=[]
for v in d['violations']:
 if v['type']!='track_not_centered_on_via':continue
 tr=next(nodes[i['uuid']] for i in v['items'] if nodes[i['uuid']][0]=='segment');via=next(nodes[i['uuid']] for i in v['items'] if nodes[i['uuid']][0]=='via');c=tuple(map(float,first(via,'at')[1:3]));before=sexpr(tr);key=min(['start','end'],key=lambda k:math.dist(tuple(map(float,first(tr,k)[1:3])),c));first(tr,key)[1:3]=read_sexpr(f'(at {c[0]} {c[1]})')[1:3];changes.append(dict(kind='second_endpoint_center',old=before,new=sexpr(tr)))
for uid,points in [
 ('3deed10d-07c3-4308-8ae2-a1d4a4104c05',[(232.8,128.25),(233.15,128.0),(233.6,128.1)]),
 ('66dda54d-dbf8-4d9a-ad7a-b24e7fc6c56b',[(207.55,109.2),(208.1,109.2),(208.5,108.95)])]:
 tr=nodes[uid];before=sexpr(tr);width=first(tr,'width')[1];layer=first(tr,'layer')[1];net=first(tr,'net')[1]
 first(tr,'start')[1:3]=read_sexpr(f'(at {points[0][0]} {points[0][1]})')[1:3];first(tr,'end')[1:3]=read_sexpr(f'(at {points[1][0]} {points[1][1]})')[1:3]
 new=read_sexpr(f'(segment (start {points[1][0]} {points[1][1]}) (end {points[2][0]} {points[2][1]}) (width {width}) (layer "{layer}") (net "{net}") (uuid {uuid.uuid5(uuid.NAMESPACE_URL,"p03-centering-dogleg:"+uid)}))');t.append(new)
 changes.append(dict(kind='same_width_local_dogleg',old=before,new=[sexpr(tr),sexpr(new)]))
for uid in ['1a3237d7-f2d7-48fa-be3e-d749cce0c75f','2956f8b2-a5a3-4458-b06b-9193eb9ec07c']:
 tr=nodes[uid];before=sexpr(tr);assert float(first(tr,'width')[1])==.8;first(tr,'width')[1]=a(.6)
 changes.append(dict(kind='EXPLICIT_proposed_P19_via_entry_neck_0p8_to0p6',old=before,new=sexpr(tr),force_current_acceptance=False))
(dest/'power_p03.kicad_pcb').write_text(sexpr(t)+'\n')
lengths=[math.dist(tuple(map(float,first(nodes[u],'start')[1:3])),tuple(map(float,first(nodes[u],'end')[1:3]))) for u in ['1a3237d7-f2d7-48fa-be3e-d749cce0c75f','2956f8b2-a5a3-4458-b06b-9193eb9ec07c']]
rho=1.724e-8*(1+.00393*80);rc=[rho*(x/1000)/(.6e-3*70e-6) for x in lengths]
report=dict(changes=changes,original_vias_and_FPs_unchanged=True,all_rule_values_unchanged=True,
 explicit_P19_two_short_necks=dict(length_mm=lengths,new_width_mm=.6,inner_Cu_minimum_required_m=70e-6,temperature_scenario_C=100,rho_copper_scenario_ohm_m=rho,individual_complete_neck_resistance_scenario_ohm=rc,both_series_times1p2_scenario_ohm=1.2*sum(rc),at0p2A_extra_drop_scenario_v=.2*1.2*sum(rc),not_added_to_authoritative_source_load_a=True,material_geometry_temperature_and_coupled_network_bound_accepted=False),
 physical_qualified=False,critical_literal_loop_and_buck_proofs_inherited=False)
(R/'centering2-delta.json').write_text(json.dumps(report,indent=2)+'\n');print(report['explicit_P19_two_short_necks'])
