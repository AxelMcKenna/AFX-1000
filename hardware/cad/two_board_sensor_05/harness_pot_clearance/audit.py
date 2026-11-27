"""Bind sensor harness pin mapping, installed board datums and conditional loading budget."""
import json,hashlib,math
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[3]
main=R.parent/'signal_input/native-r7/signal_main.kicad_pcb';sensor=R.parent/'pcb/native-r3/sensor.kicad_pcb'
def footprints(p):
 return{next(v[2]for v in children(f,'property')if v[1]=='Reference'):f for f in children(read_sexpr(p.read_text()),'footprint')}
m=footprints(main);s=footprints(sensor);f=m['D_J1010'];pose=first(f,'at');angle=math.radians(float(pose[3]));rows=[]
for i,pad in enumerate(children(f,'pad'),1):
 at=first(pad,'at');x,y=map(float,at[1:3]);xyz=[float(pose[1])+x*math.cos(angle)+y*math.sin(angle),float(pose[2])-x*math.sin(angle)+y*math.cos(angle),8.35]
 w=s['W'+str(i)];local=list(map(float,first(w,'at')[1:3]));wp=children(w,'pad')[0]
 rows.append({'main_pin':i,'main_net':first(pad,'net')[1],'main_pad_world_mm':xyz,'sensor_ref':'W'+str(i),'sensor_net':first(wp,'net')[1],'sensor_pad_local_mm':local,'sensor_pad_back_world_mm':[299.7,72+local[0],21.6+local[1]],'sensor_wire_exit_world_mm':[298.2,72+local[0],21.6+local[1]],'sensor_drill_mm':float(first(wp,'drill')[1])})
assert [x['main_net']for x in rows]==['LINK_AGND','LINK_V3V3_IO','LINK_SCL','LINK_SDA']
assert [x['sensor_net']for x in rows]==['/AGND','/V3V3_IO','/SCL','/SDA']
for ref,xy in [('D_H2',[250,57]),('D_H5',[294,88])]:assert list(map(float,first(m[ref],'at')[1:3]))==xy
path=[[234,55,28],[246,62,28],[283,76,28],[293,82,25.1]]
paths=[Path(__file__),R/'route.scad',R/'run.py',main,sensor,REPO/'hardware/cad/two_board_print_01/captured.scad',REPO/'hardware/cad/two_board_print_01/README.md']
report={'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'pin_mapping':rows,'selected_cable':'3M3365/06','cable_order':['GND','SCL','GND','SDA','GND','3V3'],'cable_cut_mm':82,'cut_tolerance_mm':1,'main_fanout_mm':20,'sensor_fanout_mm':12,'nominal_intact_ribbon_mm':50,'routing_envelope_polyline_mm':path,'polyline_length_mm':sum(math.dist(a,b)for a,b in zip(path,path[1:])),'envelope_radius_mm':4.5,'header':'Harwin M20-9990445','mate':'Harwin M20-1060400','contacts':'Harwin M20-1180042','main_clamp_center_mm':[259,66.9189189,28],'sensor_clamp_center_mm':[289,79.6,26.26],'mounts':[{'ref':'D_H2','screw':'M2x25','support_height_mm':15},{'ref':'D_H5','screw':'M2x20','support_height_mm':10}],'nominal_cable_capacitance_pF_per_line':47.5*.083,'accepted_complete_harness_ceiling_pF_per_line':12,'capacitance_ceiling_is_receiving_requirement_not_manufacturer_guarantee':True,'full_bus_allocations_pF':{'main_board_and_devices':80,'missing_codec_and_future_routes':10,'sensor_board_and_device':15,'Trill':15,'this_sensor_harness':12,'all_remaining_harnesses':18},'total_budget_pF':150,'worst_pullup_ohm':2020,'rise_time_budget_ns':.8473*2020*150e-3,'all_remaining_harness_routes_closed':False,'board_capacitance_established':False,'assembled_waveforms_measured':False,'physical_fit_qualified':False}
(R/'contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'pins':rows,'budget_pF':150,'nominal_cable_pF':report['nominal_cable_capacitance_pF_per_line']},indent=2))
