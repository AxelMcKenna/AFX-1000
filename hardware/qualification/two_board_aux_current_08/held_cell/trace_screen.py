"""Trace-only sensitivity at receiving current/foil assumptions, not rail qualification."""
import json,math,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import sha
H=Path(__file__).resolve().parent

def run():
 board=H/'native-local-02/power_protection.kicad_pcb';planpath=H/'local-routes.json';apath=H.parent/'held_rail/analysis.json';p=json.loads(planpath.read_text());a=json.loads(apath.read_text());t=read_sexpr(board.read_text());segments={first(s,'uuid')[1]:s for s in children(t,'segment')};sheet=1.724e-5*(1+.00393*(125-20))/.035;current=a['receiving_allocations']['total_reservoir_drain_A'];rows=[]
 for i,r in enumerate(p['routes']):
  length=0
  for j,(start,end) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
   uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:HELD-CELL-LOCAL-01:track:'+str(i)+':'+str(j)));s=segments[uid];aa=list(map(float,first(s,'start')[1:]));bb=list(map(float,first(s,'end')[1:]));assert math.dist(aa,start)<2e-6 and math.dist(bb,end)<2e-6 and float(first(s,'width')[1])==r['width_mm'];length+=math.dist(aa,bb)
  resistance=sheet*length/r['width_mm'];rows.append({'source':r['source'],'target':r['target'],'native_centerline_length_mm':length,'width_mm':r['width_mm'],'trace_resistance_ohm_under_assumptions':resistance,'drop_V_if_full_receiving_current_flows':resistance*current})
 keys={x['source']+'->'+x['target']:x for x in rows};inputkeys=['P_R902.2->P_C902.1','P_C902.1->P_C905.1','P_C905.1->P_C903.1','P_C903.1->P_U901.1'];out={'source_sha256':{'board':sha(board),'plan':sha(planpath),'held_analysis':sha(apath),'prior_copper_assumption_source':sha(H.parent/'placement/paths.py'),'script':sha(Path(__file__))},'assumptions':{'copper_20C_resistivity_ohm_mm':1.724e-5,'temperature_coefficient_per_C':.00393,'temperature_C':125,'finished_thickness_mm':.035,'thickness_qualified':False,'receiving_current_A':current},'native_coordinate_quantization_allowance_mm':2e-6,'rows':rows,'RC_feed_to_LDO_input_trace_drop_V_under_assumptions':sum(keys[k]['drop_V_if_full_receiving_current_flows'] for k in inputkeys),'LDO_output_to_output_cap_trace_drop_V_under_assumptions':keys['P_U901.5->P_C904.1']['drop_V_if_full_receiving_current_flows'],'LDO_ground_escape_trace_drop_V_under_assumptions':keys['P_U901.2->via:P_U901']['drop_V_if_full_receiving_current_flows'],'total_ESR_and_local_drop_receiving_allocation_V':a['receiving_allocations']['instantaneous_ESR_and_local_drop_V'],'not_included':['pad copper','via barrels and contacts','ground-plane resistance and spreading','capacitor ESR','long external supply/distribution routes','actual current/temperature/foil tolerance','transient inductance and stability'],'qualified':False};(H/'trace-screen.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if 'trace_drop' in k})
if __name__=='__main__':run()
