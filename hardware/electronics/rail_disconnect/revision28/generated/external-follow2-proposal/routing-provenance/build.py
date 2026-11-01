import json,sys,math,uuid
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.power_distribution.p03.route import coded,named
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.focused import legal_line
from hardware.electronics.rail_disconnect.revision28.receiver_surface_path import connect
R=Path(__file__).parent;t=coded(read_sexpr((R/'posed-native.kicad_pcb').read_text()));names={str(n[1]):str(n[2]).lstrip('/') for n in children(t,'net')};removed=[]
ids={'de531b86-3e43-50a5-b647-07d7ddcf3578','e648649c-d1d8-53f8-ac30-4a58ef1a647f','61a1b572-8749-5852-bb4e-de04d8170d49','657d2fa6-4545-5744-9ea3-80bae1a0a0ff','39fd5070-8a97-5379-bd06-e557bfaecc88'}
oldOUT=json.loads((R.parent/'c84-local-recut.json').read_text())['withdrawn'];ids|={v['uuid'] for v in oldOUT if v['net']=='E28_OUT_VALID_ACTIVE'}
for n in list(children(t,'segment')):
 uid=str(first(n,'uuid')[1]);net=names[str(first(n,'net')[1])];aa=tuple(round(float(x)-100,5) for x in first(n,'start')[1:3]);bb=tuple(round(float(x)-100,5) for x in first(n,'end')[1:3])
 special=(net=='ANA_PG1_SCHMITT' and str(first(n,'layer')[1])=='In4.Cu' and aa==(63.45,51.65) and bb==(67.65,51.65)) or (net=='E28_ANA_FOLLOW' and str(first(n,'layer')[1])=='In3.Cu' and aa==(59.2,52.85) and bb==(83.6,52.85))
 if uid in ids or special:removed.append(dict(uuid=uid,net=net,source_object=sexpr(n)));t.remove(n)
assert len(removed)==12,len(removed)
rt=Router(t);routes=[]
# Exact owner candidate barrels are abstract planning obstacles; no board object is authored for them.
for p in [(67.075,50.625),(51.6375,49.3),(50.5125,46.675),(52.9625,50.375),(51.6375,48)]:rt.geometry.append(dict(kind='via',net='OWNER_FUTURE_RECEIVER',layers=tuple(range(6)),radius=.3,xy=p))
plans=[('V2V5_AUX',3,[(61.95,52.225),(61.75,53.475)]),('E28_ANA_FOLLOW',3,[(59.2,52.85),(60.5,52.85),(60.5,51.4),(62.75,51.4),(63.5,52.85),(83.6,52.85)]),('ANA_PG1_SCHMITT',4,[(63.45,51.65),(63.45,52.6),(67.65,52.6),(67.65,51.65)]),('V2V5_AUX',0,[(60.3,51.25),(60.3,50.6),(63.3,50.9)]),('V2V5_AUX',0,[(62.3,50.1),(63.3,50.9)]),('AGND',0,[(63.3,52.5),(63.275,53.475)])]
for net,layer,points in plans:
 for aa,bb in zip(points,points[1:]):
  ok=legal_line(rt,net,layer,aa,bb,.2);print('literal',net,layer,aa,bb,ok,flush=True)
  if not ok:
   (R/'literal-failure.json').write_text(json.dumps(dict(net=net,layer=layer,start=aa,end=bb),indent=2)+'\n');raise RuntimeError('literal path collision')
 rt.path(net,layer,points,.2);routes.append(dict(net=net,layer=layer,points=points))
# First join OUT_VALID using real retained same-net barrels, retaining all actual source/target pins.
results=[]
for layer in [2,3,4,1,5,0]:
 got,why=connect(rt,dict(net='E28_OUT_VALID_ACTIVE',xy=[46.4875,48.575],layers=(layer,)),[dict(xy=[97.7,48],kind='ACTUAL_RETAINED_SAME_NET_BARREL')],radius=54,step=.1,budget=400000)
 results.append(dict(net='E28_OUT_VALID_ACTIVE',layer=layer,route=got,reason=why));print('OUT_VALID',layer,bool(got),why,flush=True)
 if got:break
for i,n in enumerate(t):
 if isinstance(n,list) and n and n[0] in ['segment','via'] and not children(n,'uuid'):n.append([a('uuid'),a(str(uuid.uuid5(uuid.NAMESPACE_URL,'afx-joint-C84:'+str(i)+sexpr(n))))])
(R/'stage1.kicad_pcb').write_text(sexpr(named(t))+'\n');(R/'stage1.json').write_text(json.dumps(dict(removed=removed,literal_routes=routes,OUT_VALID_attempts=results),indent=2)+'\n')
