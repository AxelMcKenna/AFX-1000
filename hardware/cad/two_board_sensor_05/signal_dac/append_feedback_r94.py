"""Add four adjacent unity-buffer feedback joins after screening all planned control copper."""
import json,hashlib,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.cad.two_board_sensor_05.signal_dac import adc_context_r90 as C
from hardware.electronics.common.sexpr import read_sexpr,sexpr,a
R=C.R;r=json.loads((R/'candidate-r92/routing.json').read_text());t=read_sexpr((R/'candidate-r92/signal_main.kicad_pcb').read_text())
for row in r['routes']:C.screen.added.append((row['net'],row['layer'],LineString(row['path_mm'])))
for v in r['vias']:
 for layer in C.S.SIGNAL_LAYERS:C.screen.added.append((v['net'],layer,Point(v['at']).buffer(.2)))
for q in r['planned_ground_returns']:
 for layer in C.S.SIGNAL_LAYERS:C.screen.added.append(('LINK_AGND',layer,Point(q).buffer(.2)))
added=[]
for k,(ref,pins,net)in enumerate([('A_U103',['1','2'],'/A_ADC/BUF_L'),('A_U103',['7','6'],'/A_ADC/BUF_R'),('A_U104',['1','2'],'/A_ADC/REF_HALF_L'),('A_U104',['8','9'],'/A_ADC/REF_HALF_R')]):
 ps=[next(o for o in C.c['objects']if o.get('ref')==ref and o.get('pin')==p)for p in pins];assert ps[0]['net']==ps[1]['net']==net and ps[0]['group']!=ps[1]['group'];path=[o['position_mm']for o in ps]
 assert C.screen.legal(net,'F.Cu',path),(ref,pins)
 uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'TBH-adc-r94-feedback-{k}'));t.append([a('segment'),[a('start'),*path[0]],[a('end'),*path[1]],[a('width'),.2],[a('layer'),'F.Cu'],[a('net'),net],[a('uuid'),uid]])
 row={'net':net,'layer':'F.Cu','width_mm':.2,'path_mm':path,'role':'local_buffer_feedback','join':100+k};r['routes'].append(row);added.append({'uuid':uid,'reference':ref,'pins':pins,**row});C.screen.added.append((net,'F.Cu',LineString(path)))
r['expected_opens']-=len(added);r['local_buffer_feedback_joins']=added;r['declared_new_selected_nets']=sorted({x['net']for x in r['routes']})
paths=[Path(__file__),R/'adc_context_r90.py',R/'candidate-r92/routing.json',R/'candidate-r92/signal_main.kicad_pcb',R/'capture-r89/capture.json'];r['local_feedback_source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
out=R/'candidate-r94';out.mkdir(exist_ok=False);(out/'signal_main.kicad_pcb').write_text(sexpr(t)+'\n');(out/'routing.json').write_text(json.dumps(r,indent=2)+'\n');print('Added four 1.27mm feedback joins; expected',r['expected_opens'])
