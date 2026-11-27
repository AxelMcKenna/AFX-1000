"""Remove the redundant threshold transition and detour a bias monitor reference gap."""
import json,uuid,hashlib,copy
from pathlib import Path
from hardware.fabrication.route_nf_surface import Screen
from hardware.cad.two_board_sensor_05.signal_dac.bounded_path import bounded_path
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
R=Path(__file__).resolve().parent;r=json.loads((R/'candidate-r84/routing.json').read_text());c=json.loads((R/'capture-r87/capture.json').read_text());screen=Screen(c);net='/A_ADC/THRESH_LOWER';q=[63.9125,89.9]
found=bounded_path(lambda p:screen.legal(net,'B.Cu',p),[58.9125,87.5],[62.875,89.67],(55,84,66,95),max_nodes=100000);assert found['path']is not None
assert r['routes'][4]['path_mm'][-1]==q and r['routes'][5]['path_mm'][-1]==q
r['routes'][4]['path_mm']=found['path'];r['routes'][4]['role']='join';del r['routes'][5]
bias=r['routes'][-1];assert bias['net']=='/A_ADC/BIAS_SHIFT_R'and bias['layer']=='B.Cu';bias['path_mm']=[[66.675,93.21],[66.2,93.5],[65.4,93.4],[58.825,92.0]];assert screen.legal(bias['net'],'B.Cu',bias['path_mm'])
r['vias']=[v for v in r['vias']if v['at']!=q];r['used_return_sites']=[v for v in r['used_return_sites']if v['signal_at']!=q];assert len(r['vias'])==8
r['reference_gap_repair']={'removed_redundant_signal_via_at':q,'threshold_reuses_return_verified_via_at':[62.875,89.67],'bounded_search':found,'bias_departure_detour':bias['path_mm'],'no_tolerance_or_exclusion_change':True,'expected_joins_preserved':10}
t=read_sexpr((R/'native-r83/signal_main.kicad_pcb').read_text())
for k,row in enumerate(r['routes']):
 for j,(p,v)in enumerate(zip(row['path_mm'],row['path_mm'][1:])):t.append([a('segment'),[a('start'),*p],[a('end'),*v],[a('width'),.2],[a('layer'),row['layer']],[a('net'),row['net']],[a('uuid'),str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-adc-r88-{k}-{j}'))]])
for k,v in enumerate(r['vias']):
 v['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-adc-r88-via-{k}'));t.append([a('via'),[a('at'),*v['at']],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),v['net']],[a('uuid'),v['uuid']]])
paths=[Path(__file__),R/'bounded_path.py',R/'candidate-r84/routing.json',R/'native-r83/signal_main.kicad_pcb',R/'capture-r87/capture.json',R/'reference-review-r87.json'];r['reference_gap_repair_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
out=R/'candidate-r88';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print(r['reference_gap_repair'])
