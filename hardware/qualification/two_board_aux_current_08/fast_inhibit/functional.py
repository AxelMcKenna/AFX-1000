"""Re-screen changed AUX-dependent functions; no circuit edits."""
import copy,hashlib,itertools,json,math,re,xml.etree.ElementTree as ET
from pathlib import Path
from .candidate import calculate,HERE,BASE
from hardware.fabrication.analyze_two_board_aux_resistor_networks import solve
from hardware.electronics.rail_disconnect.revision28.auxiliary import screen

PROPOSED={'P_R108':17600.,'E_R83':10700.,'E_R84':5760.,'E_R88':16200.,'E_R89':13300.,'P_R118':18000.,'P_R119':11700.,'P_R117':392000.}

def run():
 c=calculate();lo,hi=c['regulator']['conditional_interval_V'];nom=c['regulator']['nominal_V'];old=2.59476307
 tree=ET.parse(BASE/'sources/TBP71-netlist.xml');components={x.attrib['ref']:x.findtext('value') for x in tree.findall('./components/comp')}
 nets={n.attrib['name'].lstrip('/'):[x.attrib for x in n.findall('node')] for n in tree.findall('./nets/net')};pins={}
 for net,nodes in nets.items():
  for node in nodes:pins.setdefault(node['ref'],[]).append({'pin':node['pin'],'net':net.removeprefix('E_rail_disconnect/').removeprefix('PWR_')})
 parts=[{'ref':ref.removeprefix('E_'),'part':value,'pins':pins[ref]} for ref,value in components.items() if ref.startswith('E_')]
 bad=screen(parts=parts,receiver_interval=(lo,hi))
 for part in parts:
  ref='E_'+part['ref']
  if ref in PROPOSED:part['part']=str(PROPOSED[ref])+' 0.01% 5ppm'
 good=screen(parts=parts,receiver_interval=(lo,hi))
 # Existing auxiliary.screen also returns old logic assumptions. Retain ONLY
 # its actual analog corner result and explicit operating-point limitation.
 window=lambda r:{'margins':r['reference_window'],'receiver_interval_V':r['receiver_interval_requirement_v'],'comparator_error_at_actual_operating_point_accepted':False}
 groups=copy.deepcopy(json.loads((BASE/'sources/resistor-networks.json').read_text())['networks']);curr=[]
 for group in groups:
  for resistor in group['resistors']:
   if resistor['ref'] in PROPOSED:resistor['nominal_ohm']=PROPOSED[resistor['ref']]
  maxima=[];pmax={r['ref']:0. for r in group['resistors']}
  for state in group['states']:
   references=[1.2375,1.2625] if 'PWR_PROTECT_REF' in group['boundary_nodes'] else [1.25]
   for va,vr,factors in itertools.product([lo,hi],references,itertools.product([.97,1.03],repeat=len(group['resistors']))):
    s=solve(group,factors,va,vr,state['ideal_sinks_low'],state['switch_ON'])
    maxima.append(s['AUX_source_A'])
    for r,f in zip(group['resistors'],factors):pmax[r['ref']]=max(pmax[r['ref']],s['resistor_current_A'][r['ref']]**2*r['nominal_ohm']*f)
  curr.append({'id':group['id'],'roots':group['roots'],'conditional_max_A':max(maxima),'resistor_power_max_W':pmax})
 # Exact nominal 3-resistor summing-node formula; comparator offset/hysteresis,
 # output loading, rise/fall and reference-filter dynamics remain excluded.
 def fast(aux,rt,rb,rf):
  vref=aux*rb/(rt+rb);rise=vref*(1+30900/3090+30900/rf)
  return {'reference_V':vref,'VIN_IC_rising_V':rise,'VIN_IC_falling_V':rise-aux*30900/rf,'external_hysteresis_V':aux*30900/rf,'reference_filter_tau_s':rt*rb/(rt+rb)*1e-9}
 caps=[]
 for x in c['AUX_caps_to_requalify']:
  ratings=re.findall(r'(\d+(?:\.\d+)?)V',x['value']);assert len(ratings)==1,x
  caps.append(dict(**x,rated_V=float(ratings[0]),voltage_rating_screen_pass=float(ratings[0])>hi,effective_capacitance_qualified=False))
 thermal=[]
 for vin,load,ambient in itertools.product([13.2,14.4],[.065,.09,.1],[55,70,85]):
  power=(vin-lo)*load+vin*.0001
  thermal.append({'VIN_V':vin,'load_A':load,'ambient_C':ambient,'ground_current_allocation_A':.0001,'dissipation_W':power,'maximum_installed_theta_JA_for125_C_per_W':(125-ambient)/power,'JEDEC66p2_sensitivity_TJ_C':ambient+66.2*power,'actual_board_temperature_proven':False})
 return {'proposed_values_ohm_not_applied':PROPOSED,'unchanged_reference_window':window(bad),'corrected_reference_window':window(good),
  'fast_OV':{'baseline':fast(old,10000,10000,309000),'uncorrected':fast(nom,10000,10000,309000),'corrected':fast(nom,18000,11700,392000),'all_are_nominal_only':True,'C109_unchanged_F':1e-9,'C109_candidate_F':680e-12,'candidate_filter_tau_s':18000*11700/(18000+11700)*680e-12},
  'direct_resistor_networks':curr,'direct_resistor_conditional_sum_A':math.fsum(x['conditional_max_A'] for x in curr),'resistor_screen_conditions':'3% total resistor envelope not accepted;ideal sink/switch states;zero pin leakage;source/reference endpoints;not necessarily simultaneously functional',
  'capacitors':caps,'thermal_sensitivities':thermal,'startup_charge_sensitivity':{'E_U19_C60_F':10e-9,'E_U19_C60_initial_tolerance_only_charge_s':[10e-9*.95*1.17/1.35e-6,10e-9*1.05*1.29/.9e-6],'N_U56_C99_F':100e-9,'N_U56_C99_6percent_allocation_charge_s':[100e-9*.94*1.17/1.35e-6,100e-9*1.06*1.29/.9e-6],'assumes_zero_CT_board_leakage':True,'base_propagation_and_startup_max_not_given':True},'current_ceiling_proven':False,'all_cross_domain_paths_qualified':False,'startup_qualified':False,'board_changed':False,
  'independent_clamp_chain':{'N_U56_supply':'PWR_NF_RAW5','N_U56_sense':'AUX through N_R92/N_R93/N_R94','reset_output':'CLAMP_SUPPLY_ENABLE','load_switch':'N_U57 TPS22919DCKR','load_switch_output':'CLAMP_LED_SUPPLY','led_resistors':['N_R4','N_R11'],'clamps':['N_U6','N_U12'],'indication':'N_U58 ABS_AUX_FAULT','N_U56_CT_F':100e-9,'max_assertion_delay_s':None,'qualification':'Existing independent supply does not create a missing maximum TPS3890 delay or bound actual photorelay closure'},
  'source_sha256':{str(p.resolve().relative_to(BASE.parents[2])):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),BASE/'sources/TBP71-netlist.xml',BASE/'sources/resistor-networks.json',Path('hardware/fabrication/analyze_two_board_aux_resistor_networks.py'),Path('hardware/electronics/rail_disconnect/revision28/auxiliary.py')]}}
if __name__=='__main__':
 r=run();(HERE/'functional.json').write_text(json.dumps(r,indent=2)+'\n')
 print({k:r[k] for k in ['unchanged_reference_window','corrected_reference_window','fast_OV','direct_resistor_conditional_sum_A']})
