"""Actual held-rail contacts and conditional RC acceptance, not a load guarantee."""
import hashlib,json,math,xml.etree.ElementTree as ET
from pathlib import Path
from ..fast_inhibit.preregulator import calculate_preregulator
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'schematic_candidate'
def analyze():
 t=ET.parse(BASE/'native-03/candidate-netlist.xml');parts={c.attrib['ref']:c.findtext('value') for c in t.findall('./components/comp')}
 nets={n.attrib['name']:[(x.attrib['ref'],x.attrib['pin']) for x in n.findall('node')] for n in t.findall('./nets/net')}
 pn={p:n for n,ps in nets.items() for p in ps}
 fanout=[]
 for ref,pin in [('E_U29','3'),('E_U29','7'),('E_U31','3'),('E_U31','7')]:
  n=pn[(ref,pin)];fanout.append(dict(source=[ref,pin],net=n,contacts=[{'ref':r,'pin':p,'value':parts[r]} for r,p in nets[n]]))
 # Exact direct resistor-to-ground paths; four 100R/10k branches need their
 # own receiver leakage allowance, which is not supplied by the Si8751 table.
 vhi=3.3*1.015;vlo=3.3*.985;rows=[]
 for r in ['E_R100','E_R104','E_R108','E_R141']:
  assert pn[(r,'2')]=='PWR_AGND';ohm=47000 if parts[r]=='47k' else 10000;assert parts[r] in ['47k','10k']
  rows.append(dict(path=[r],R_nom_ohm=ohm,I_max_under_3percent_R_envelope_A=vhi/(ohm*.97)))
 for series,down,u in [('E_R4','E_R5','E_U1'),('E_R12','E_R13','E_U2'),('E_R20','E_R21','E_U3'),('E_R28','E_R29','E_U4')]:
  assert pn[(series,'2')]==pn[(down,'1')]==pn[(u,'3')] and pn[(down,'2')]=='PWR_AGND'
  rows.append(dict(path=[series,down],R_nom_ohm=10100,I_max_under_3percent_R_envelope_A=vhi/(10100*.97),receiver_input_current_included=False))
 prereg=calculate_preregulator();v5lo,v5hi=prereg['conditional_output_interval_V']
 # Total drain includes regulator ground current, capacitor leakage and load.
 i=.1;r=4.7;rtol=.03;rlo=r*(1-rtol);rhi=r*(1+rtol);c=200e-6
 uv5=5*.95;overdrive5=uv5*.993*.95
 start=overdrive5-i*rhi;esr_drop=.02;start-=esr_drop;floor=3.6
 # Conservative independent minR in discharge and maxR in initial drop.
 log=math.log((start+i*rlo)/(floor+i*rlo));hold=rlo*c*log
 assert start>floor and hold>31e-6
 return dict(selected={'LDO':'TPS7A2033PDBVR','input_feed_R':'CRCW25124R70FKEG','input_reservoir':'T520D227M010ATE025','minimum_load_R':'TNPW08053K01BEEA'},
  exact_output_fanout=fanout,static_resistor_branches=rows,static_resistor_sum_A=math.fsum(x['I_max_under_3percent_R_envelope_A'] for x in rows),
  table_conditioned_driver_current_A=.038,driver_TT='Four 10k 1% resistors; no parallel startup capacitors',
  current_bound_proven=False,missing_current_bounds=['Si8751 IN-low maximum absent; IN-transition/load dependence not bounded; 9.5mA condition IN=VDD/TT=10k/100pF differs from real input and gate load','AUP2G08 ICC valid at rail-valued inputs; deltaICC at discrete3.3V and VCC-0.6V; arbitrary transition current not bounded','E_J6.2 and E_J9.5 external MASTER_ENABLE loads unspecified','Si8751 IN input leakage/capacitance maximum absent','LDO ground and capacitor leakage bounds across actual input/temperature require receiving test'],
  LDO={'regulated_output_V':[vlo,vhi],'guarantee_conditions':'SBVS338H:3.6<=VIN<=6V,1..300mA,-40..125C,DBV3.3V part','minimum_bleeder_current_A':vlo/(3010*1.0035),'minimum_logic_supply_V':3.,'margin_before_distribution_V':vlo-3.,'LDO_pin_map':{'1':'held RC input','2':'AGND','3':'held RC input','4':'NC','5':'PWR_AUX_HELD3V3'}},
  receiving_allocations={'total_reservoir_drain_A':i,'effective_C_min_F':c,'total_feed_R_error':rtol,'instantaneous_ESR_and_local_drop_V':esr_drop,'C_nominal_F':440e-6,'C_initial_tolerance':.2,'C_after_initial_tolerance_only_F':352e-6,'C_temperature_bias_age_and_leakage_qualified':False},
  five_volt_supervisor={'MPN':'TPS3703A5500DSER','VDD':'held3.3V','SENSE':'prereg5V','reset':'wiredOR with existing AUX supervisor','UV_release_max_V':uv5*1.007+uv5*.008,'healthy_low_margin_V':v5lo-(uv5*1.007+uv5*.008),'OV_min_V':5*1.05*.993,'healthy_high_margin_V':5*1.05*.993-v5hi,'overdrive_floor_V':overdrive5},
  hard_5V_source_short={'initial_RC_node_min_at_worst_detection_V':start,'LDO_required_input_floor_V':floor,'minimum_regulated_hold_s_under_allocations':hold,'max_supervisor_assertion_s':30e-6,'logic_path_allocation_s':1e-6,'remaining_after_detection_s':hold-31e-6,'capacitance_required_for_100us_F':100e-6/(rlo*log),'model':'V(t)=(V0+I*R)*exp(-t/(R*C))-I*R;source=0,constant maximum drain;repeated faults/recharge not accepted'},
  resistor={'steady_power_at_drain_allocation_W':i*i*rhi,'worst_initial_short_or_charge_peak_W':v5hi*v5hi/rlo,'energy_of_max_nominal_C_tolerance_charge_J':.5*440e-6*1.2*v5hi*v5hi,'pulse_and_cycle_acceptance':False},
  thermal_sensitivity={'held_LDO_loss_at100mA_2mAground_W':(v5hi-.1*rlo-vlo)*.1+(v5hi-.1*rlo)*.002,'maximum_theta_JA_at85ambient_125junction':40/((v5hi-.1*rlo-vlo)*.1+(v5hi-.1*rlo)*.002),'datasheet_DBV_theta_JA_C_per_W':187.1,'mounted_board_qualified':False},
  output_capacitor_acceptance={'effective_total_min_F':.47e-6,'effective_total_max_for_reverse_current_screen_F':4e-6,'output_ESR_max_ohm':.1,'note':'Includes C904 and eight transferred/new bypass capacitors; total maximum is an allocation, not a nominal sum guarantee'},
  timing_qualified=False,gate_load_qualification='35us Si8751 turnoff uses100pF. Paired CSD18540Q5B+22R is not covered; measure actual gate-safe endpoint within remaining hold window.',
  limits=['Main AUX hard short can invalidate monitors before the30us reaction; this variant does not prove the original before-invalid criterion for instantaneous faults','Held-rail local short not covered','No manufacturer maximum startup time; sequence acceptance still required','MASTER_ENABLE fanout must meet gate delay loading; typ input capacitances are not maxima'],
  external_source_sha256={str(p.relative_to(HERE.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE.parents[3]/'hardware/electronics/rail_disconnect/spec.py',HERE.parents[3]/'hardware/electronics/rail_disconnect/revision28/positive.py']},
  source_sha256={str(p.relative_to(HERE.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),BASE/'native-03/candidate-netlist.xml',HERE/'primary/tps7a20.pdf',HERE/'primary/t520d227m010ate025.pdf',HERE/'primary/crcw.pdf',HERE.parent/'fast_inhibit/primary/tps3703.pdf',HERE.parent/'package_currents/primary/si8751.pdf',HERE.parent/'package_currents/primary/sn74aup2g08.pdf']})
if __name__=='__main__':
 r=analyze();(HERE/'analysis.json').write_text(json.dumps(r,indent=2)+'\n');print({k:r[k] for k in ['static_resistor_sum_A','hard_5V_source_short']})
