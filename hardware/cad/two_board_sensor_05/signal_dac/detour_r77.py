"""Move the new In5 departure away from the neighboring BIAS_N_L reference opening."""
import copy,hashlib,json,uuid
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first
import hardware.fabrication.route_nf_surface as S
R=Path(__file__).resolve().parent;r=json.loads((R/'candidate-r75/routing.json').read_text());t=read_sexpr((R/'candidate-r75/signal_main.kicad_pcb').read_text());route=r['routes'][3]
assert route['net']=='/A_DAC/RX_POS_R'and route['layer']=='In5.Cu'and route['role']=='layer-bridge'
before=copy.deepcopy(route['path_mm']);assert before[0]==[123.938867,70.945894]and before[1]==[118.4,72.9]
route['path_mm'].insert(1,[123.438867,71.345894])
S.SIGNAL_LAYERS=('F.Cu','B.Cu','In3.Cu','In5.Cu');screen=S.Screen(json.loads((R/'capture-r76/capture.json').read_text()));assert screen.legal(route['net'],route['layer'],route['path_mm'])
uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'TBH-dac-r75-3-0'));old=next(x for x in children(t,'segment')if first(x,'uuid')[1]==uid);t.remove(old)
for k,(p,q)in enumerate(zip(route['path_mm'][:3],route['path_mm'][1:3])):
 x=copy.deepcopy(old);first(x,'start')[1:]=p;first(x,'end')[1:]=q;first(x,'uuid')[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-dac-r77-departure-{k}'));t.append(x)
r['RX_POS_R_trace_length_mm']=sum(LineString(x['path_mm']).length for x in r['routes']if x['net']=='/A_DAC/RX_POS_R')
r['local_reference_detour']={'net':route['net'],'layer':route['layer'],'before_path_mm':before,'after_path_mm':route['path_mm'],'neighbor_via_uuid':'37068287-4c39-5c0c-ac8e-07d7d4fd21bc','failed_unexplained_area_mm2':1.0512581965341438e-6,'policy':'Change new copper geometry; preserve every reference threshold and original object.'}
r['detour_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'candidate-r75/routing.json',R/'candidate-r75/signal_main.kicad_pcb',R/'capture-r76/capture.json',R/'reference-review-r76.json']}
o=R/'candidate-r77';o.mkdir(exist_ok=False);(o/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(o/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('new exact path length',r['RX_POS_R_trace_length_mm'])
