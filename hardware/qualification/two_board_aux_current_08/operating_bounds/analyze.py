"""Qualify which existing specifications apply; leave unsupported bounds absent."""
import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
from hardware.qualification.two_board_aux_current_08.package_currents.analyze import calculate
from hardware.qualification.two_board_aux_current_08.package_currents.threshold_window import window
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def analyze():
    facts=json.loads((PARENT/'package_currents/facts.json').read_text())
    inventory=json.loads((PARENT/'sources/monitor-loads.json').read_text())['IC_supply_inventory']
    tree=ET.parse(PARENT/'sources/TBP71-netlist.xml')
    nets={n.attrib['name'].lstrip('/'):[x.attrib for x in n.findall('node')] for n in tree.findall('./nets/net')}
    pins={(x['ref'],x['pin']):n for n,nodes in nets.items() for x in nodes}
    wide={'SI8751AB-ISR','TPS3431SDRBR','LTC2910HGN#PBF','OPA2333AID','SN74LVC2T45DCUR','SN74LVC3G17DCUR','SN74LVC1G06DBVR','SN74LVC1G14DCKR','SN74LVC1G97DBVR'}
    rows=[]
    for f in facts['families']:
        covers=f['part'] in wide or f['part'].startswith('SN74AUP')
        missing=['Actual nonrail input/output states, loading, leakage ownership and transitions must match or receive separate bounds']
        if not covers:missing.insert(0,'Maximum supply current over actual2.534165..2.655700V is not given by the selected table point')
        if f['part'].startswith(('SN74','SI875')):missing.append('Guaranteed current during actual transitions/gate load; typical Cpd/current curves are not maxima')
        if f['part'].startswith('SI875'):missing.append('Installed two-MOSFET gate load differs from100pF table load; OFF current is typical-only')
        rows.append(dict(part=f['part'],references=f['references'],table_voltage_domain_covers_actual_rail=covers,
                         conditional_table_package_max_uA=f['table_max_uA_per_unit']*f['units_per_package'],
                         condition=f['table_condition'],missing=missing,application_current_bound_A=None))
    counts={'AUX_tied':0,'GND_tied':0,'signal':0};input_rows=[]
    for r in inventory:
        for contact in r['all_contacts']:
            if contact['pintype']!='input':continue
            n=contact['net'].lstrip('/')
            kind='AUX_tied' if n=='PWR_V2V5_AUX' else 'GND_tied' if n=='PWR_AGND' else 'signal'
            counts[kind]+=1
            input_rows.append(dict(ref=r['ref'],part=r['part'],pin=contact['pin'],net=n,category=kind,
                capacitor_on_same_net=any(x['ref'].split('_')[-1].startswith('C') for x in nets[n])))
    # Exact independent-gate path, not whole-package false dependencies.
    stages=[('E_U19','6','E_U35','3'),('E_U35','5','E_U31','5'),('E_U31','3','E_U29','2')]
    for a,b,c,d in stages:assert pins[a,b]==pins[c,d]
    assert pins['E_U31','6']=='PWR_V2V5_AUX'
    assert pins['E_U29','1']=='PWR_ALL_RAILS_ALLOW'
    assert pins['E_U29','7']=='E_rail_disconnect/E28_MASTER_ENABLE'
    driver_paths=[]
    for r,series in [('E_U1','E_R4'),('E_U2','E_R12'),('E_U3','E_R20'),('E_U4','E_R28')]:
        assert pins[series,'1']==pins['E_U29','7'] and pins[series,'2']==pins[r,'3']
        driver_paths.append(dict(driver=r,series_resistor=series,input_net=pins[r,'3']))
    c=calculate();w=window();i=c['mixed_condition_sensitivity_A'];old_margin=c['aux_supervisor']['falling_margin_to_2V4_V'];new_margin=w['proposal']['minimum_falling_V']-2.4
    planned_c=28.5e-6
    return dict(actual_rail_interval_V=c['regulator']['conditional_output_V'],temperature_screen_C=[-40,85],families=rows,
        table_voltage_covered_packages=sum(len(r['references']) for r in rows if r['table_voltage_domain_covers_actual_rail']),
        table_voltage_uncovered_packages=sum(len(r['references']) for r in rows if not r['table_voltage_domain_covers_actual_rail']),
        input_counts=counts,inputs=input_rows,
        shutdown_chain=dict(path=['E_U19.RESET_N','E_U35.gate2 buffer','E_U31.gate2 AND withAUX','E_U29.gate1 AND withALL_RAILS_ALLOW','100ohm input branch','Si8751','MOSFET gates'],drivers=driver_paths,
            actual_TPS3890_max_assertion_delay_s=None,
            TPS3890_nominal_assertion_s_at3V3=18e-6,TPS3890_nominal_assertion_s_at5V5=8e-6,
            TPS3890_timing_condition='5% input overdrive;CTopen;VDD3.3Vor5.5V;NOM column only',
            Si8751_table_max_turnoff_s=35e-6,Si8751_turnoff_condition='100pFgate capacitance;installedtwoCSD18540Q5B+22ohm differ',
            actual_total_shutdown_max_s=None,
            stage_requirements='Detect and forceMASTER_ENABLElow before comparator supply<2.4V; then completeFET turnoff while driverVDD>=2.25V or proveunpowered outputsafe. These are separate requirements.',
            independent_aux_valid_inhibit_proven=False,
            fallback_review='TPS7A16PG falling threshold83..93% ofnominal may bebelow2.4V. No independently bounded AUXvalidity has been established forALL_RAILS_ALLOW; its final gateE_U12 is also AUXpowered. No documented Si8751 UVLO assertion-delay bound was located; loss ofVDD is not proof ofshutdown before2.4V.'),
        capacitor_hold_sensitivity=dict(nominal_all_connected_C_F=planned_c,assumed_mixed_table_current_A=i,
            existing_threshold_zero_drop_hold_s=planned_c*old_margin/i,
            proposed_threshold_zero_drop_hold_s=planned_c*new_margin/i,
            proposed_after20mV_drop_allocation_hold_s=planned_c*(new_margin-.02)/i,
            comparator_min_to_driver_min_hold_s=planned_c*(2.4-2.25)/i,
            assumed_constant_current=True,predicted_actual_failure=False,
            limitation='Nominal capacitance without derating; mixed-condition current; no regulator replenishment. A diagnostic comparison, not a transient simulation or maximum delay'),
        full_current_bound_A=None,qualification_complete=False,
        source_sha256={str(p.relative_to(PARENT)):sha(p) for p in [PARENT/'package_currents/facts.json',PARENT/'package_currents/analyze.py',PARENT/'package_currents/threshold_window.py',PARENT/'sources/monitor-loads.json',PARENT/'sources/TBP71-netlist.xml',PARENT/'package_currents/primary/tps3890.txt',PARENT/'package_currents/primary/si8751.txt',Path(__file__)]})

if __name__=='__main__':
    r=analyze();(HERE/'analysis.json').write_text(json.dumps(r,indent=2)+'\n')
    print({k:r[k] for k in ['table_voltage_covered_packages','table_voltage_uncovered_packages','input_counts','capacitor_hold_sensitivity']})
