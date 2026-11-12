"""Candidate requirements, not a qualified board modification."""
import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent

def calculate(current_allocation_A=.1,distribution_allocation_V=.02,logic_delay_allocation_s=1e-6):
    assert current_allocation_A>0 and distribution_allocation_V>=0 and logic_delay_allocation_s>=0
    # Proposed P_R108=17.6k 0.1%25ppm; preserve49.9R and10k bottom.
    top=17600;trim=49.9;bottom=10000
    nominal=1.193*(1+(top+trim)/bottom)
    lowtop=top*(1-.001-25e-6*100)+trim*(1-.0001-5e-6*100)
    hitop=top*(1+.001+25e-6*100)+trim*(1+.0001+5e-6*100)
    reglo=1.193*.98*(1+lowtop/(bottom*1.002))-.1e-6*hitop
    reghi=1.193*1.02*(1+hitop/(bottom*.998))+.1e-6*hitop
    # TPS3703A5330: 3.3V nominal,5% window; accuracy relative totripoint.
    uv=3.3*.95;ov=3.3*1.05
    uvlo=uv*.993;uvhi=uv*1.007
    uv_release_hi=uvhi+uv*.008
    ovlo=ov*.993
    overdrive_floor=uvlo*.95
    remaining=overdrive_floor-2.4-distribution_allocation_V
    assert remaining>0
    td=30e-6+logic_delay_allocation_s
    c=current_allocation_A*td/remaining
    tree=ET.parse(BASE/'sources/TBP71-netlist.xml')
    caps=[];components={x.attrib['ref']:x.findtext('value') for x in tree.findall('./components/comp')}
    for n in tree.findall('./nets/net'):
        if n.attrib['name']=='PWR_V2V5_AUX':
            for node in n.findall('node'):
                ref=node.attrib['ref']
                if ref.split('_')[-1].startswith('C'):caps.append({'ref':ref,'value':components[ref]})
    return {'proposal':{'P_R108':'17.6k 0.1%25ppm','P_R130':'49.9R unchanged','P_R109':'10k unchanged','new_supervisor':'TPS3703A5330DSER','wiring':'SENSE1 and VDD2 to AUX;GND5 to AGND;CT3 open;MR6 open;RESET4 with10k AUX pullup to E_U31.6 instead of literal AUX;retain E_U19/E_U35 startup chain','local_bypass':'100nF; RESET loading must be<=10pF for timing table'},
      'regulator':{'nominal_V':nominal,'conditional_interval_V':[reglo,reghi],'input_for_accuracy_V':nominal+.5,'margin_below_3V6_V':3.6-reghi},
      'supervisor':{'UV_nominal_V':uv,'UV_min_V':uvlo,'UV_max_V':uvhi,'UV_release_max_V':uv_release_hi,'OV_min_V':ovlo,'minimum_5percent_overdrive_V':overdrive_floor,'max_delay_s':30e-6,'release_delay_range_s':[.007,.013],'startup_correct_state_max_s':None},
      'allocations_not_bounds':{'current_A':current_allocation_A,'source_to_worst_load_drop_V':distribution_allocation_V,'downstream_logic_delay_s':logic_delay_allocation_s},
      'derived_requirements':{'effective_capacitance_min_F':c,'remaining_decay_voltage_V':remaining,'startup_drop_margin_V':reglo-uv_release_hi,'upper_supply_margin_to_OV_V':ovlo-reghi,'conditional_10uF_time_after_overdrive_s':10e-6*remaining/current_allocation_A},
      'AUX_caps_to_requalify':caps,'board_changed':False,'all_load_voltage_compatibility_proven':False,'current_bound_proven':False,'fault_short_bound_proven':False,'shutdown_qualified':False,
      'source_sha256':{str(x.relative_to(BASE)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [Path(__file__),HERE/'primary/tps3703.pdf',HERE/'primary/tps3703.txt',BASE/'sources/TBP71-netlist.xml',BASE/'package_currents/regulator-facts.json']}}
if __name__=='__main__':
    (HERE/'candidate.json').write_text(json.dumps(calculate(),indent=2)+'\n')
