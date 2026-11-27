"""Bounded PD_R detour around the V5 via's native reference-plane clearance."""
import json,hashlib,uuid
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import Screen,shape
from hardware.electronics.common.sexpr import read_sexpr,sexpr,children,first,a
R=Path(__file__).resolve().parent;r=json.loads((R/'candidate-r94/routing.json').read_text());c=json.loads((R/'capture-r95/capture.json').read_text());b=json.loads((R.parent/'signal_input/capture-r7/capture.json').read_text());screen=Screen(c);net='/A_ADC/PD_R';oldpath=[[82.5,78.5875],[81.5,78.5875],[80.5,79.5875]];path=[[82.5,78.5875],[81.5,78.5875],[81.0,79.0],[80.5,79.5875]]
row=next(x for x in r['routes']if x['net']==net and x['layer']=='F.Cu');assert row['path_mm']==oldpath;assert screen.legal(net,'F.Cu',path)
field=unary_union([shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']=='In1.Cu']).buffer(2e-6);holes=unary_union([shape(ps).buffer(.215)for o in c['objects']if o['net']==net and o['kind']=='PCB_VIA'for ps in o['layers'].values()]);oldcopper=unary_union([shape(o['layers']['F.Cu'])for o in b['objects']if o['net']==net and o['layers'].get('F.Cu')]);gap=LineString(path).buffer(.1).difference(holes).difference(oldcopper).difference(field).area;assert gap<1e-6
row['path_mm']=path;t=read_sexpr((R/'candidate-r94/signal_main.kicad_pcb').read_text());removed=[s for s in children(t,'segment')if first(s,'net')[1]==net and first(s,'layer')[1]=='F.Cu'and list(map(float,first(s,'start')[1:]))==oldpath[1]and list(map(float,first(s,'end')[1:]))==oldpath[2]];assert len(removed)==1;t.remove(removed[0])
for k,(p,q)in enumerate(zip(path[1:],path[2:])):t.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),'F.Cu'],[a('net'),net],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-adc-r96-pd-detour-{k}'))]])
r['PD_R_reference_repair']={'before_path_mm':oldpath,'after_path_mm':path,'removed_candidate_only_segment':sexpr(removed[0]),'native_r95_field_probe_uncovered_mm2':gap,'adjacent_aggressor_net':'A__V5_REG','aggressor_via_at':[81.455,79.575],'no_tolerance_or_exclusion_change':True}
paths=[Path(__file__),R/'candidate-r94/routing.json',R/'candidate-r94/signal_main.kicad_pcb',R/'capture-r95/capture.json',R/'reference-review-r95.json',R.parent/'signal_input/capture-r7/capture.json'];r['PD_R_repair_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths};out=R/'candidate-r96';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print(r['PD_R_reference_repair'])
