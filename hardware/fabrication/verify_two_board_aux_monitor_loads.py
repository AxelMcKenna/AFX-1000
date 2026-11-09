"""Independent eliminated-node formulas and current-netlist ownership checks."""
import itertools
import json
from collections import defaultdict
from pathlib import Path
from hardware.fabrication.assess_two_board_aux_load import circuit,numeric,AUX,GND
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

OUT=STAGING/'two-board-aux-monitor-loads-01'
SOURCE=STAGING/'two-board-power-startup-remaining-native-03/netlist.xml'


def run():
    assert not (OUT/'verification.json').exists()
    d=json.loads((OUT/'analysis.json').read_text())
    for name,h in d['source_sha256'].items():assert sha(REPO/name)==h
    parts,nets,pins=circuit(SOURCE)
    mon=d['monitor_reference'];fast=d['fast_OV_output']
    ref=pins['P_U25']['10'];bias=pins['P_R310']['2'];v7=pins['P_U25']['7'];v8=pins['P_U25']['8']
    n19='PWR_N19_SOURCE';n12='PWR_N12_SOURCE'
    output=pins['P_U103']['1'];sense=pins['P_U103']['3'];vin=pins['P_R115']['1'];gate=pins['P_R121']['2']
    exact={'P_R310':{ref,bias},'P_R311':{bias,GND},'P_R312':{bias,v7},'P_R313':{v7,n19},
        'P_R314':{bias,v8},'P_R315':{v8,n12},'P_R115':{vin,sense},'P_R116':{sense,GND},
        'P_R117':{output,sense},'P_R120':{gate,GND},'P_R121':{output,gate}}
    for group in [mon,fast]:
        for row in group['resistors']:
            r=row['ref'];assert row['nets']==list(pins[r].values())
            assert set(row['nets'])==exact[r]
            assert row['value']==parts[r].findtext('value') and row['nominal_ohm']==numeric(parts[r].findtext('value'))
        for node,contacts in group['contacts'].items():
            assert contacts==[dict(x,value=parts[x['ref']].findtext('value')) for x in nets[node] if x['ref'] not in exact]
    # Ensure internal nets have no unlisted resistor branches.
    for node in [bias,v7,v8,sense,gate]:
        assert {x['ref'] for x in nets[node] if x['ref'].split('_')[-1].startswith('R')}=={r for r,ns in exact.items() if node in ns}
    assert set(d['new_resistors'])==set(exact)
    max_error=0.;ref_seen=set();fast_seen=set();outside=0

    def check(group,case,fixed,injections):
        balance=defaultdict(float);power=0.;v=case['node_voltage_V']
        for row,f in zip(group['resistors'],case['resistor_factors']):
            a,b=row['nets'];r=row['nominal_ohm']*f;current=(v[a]-v[b])/r
            assert abs(current-case['resistor_current_A'][row['ref']])<1e-12
            balance[a]+=current;balance[b]-=current;power+=current*current*r
        for node,current in balance.items():
            if node not in fixed:assert abs(current-injections.get(node,0.))<1e-12
            else:assert abs(current-case['fixed_source_current_A'][node])<1e-12
        assert abs(power-case['resistor_power_W'])<1e-12
        assert abs(sum(v[n]*i for n,i in balance.items())-power)<1e-12

    for case in mon['cases']:
        key=(case['reference_V'],case['N19_V'],case['N12_V'],tuple(case['resistor_factors']),tuple(case['input_sink_A']))
        assert key not in ref_seen;ref_seen.add(key)
        a,b,c,e,f,g=[r['nominal_ohm']*factor for r,factor in zip(mon['resistors'],case['resistor_factors'])]
        j7,j8=case['input_sink_A'];vr=case['reference_V'];s19=case['N19_V'];s12=case['N12_V']
        vb=(vr/a+s19/(c+e)+s12/(f+g)-j7*e/(c+e)-j8*g/(f+g))/(1/a+1/b+1/(c+e)+1/(f+g))
        expected={bias:vb,v7:(e*vb+c*s19-j7*c*e)/(c+e),v8:(g*vb+f*s12-j8*f*g)/(f+g)}
        for node,v in expected.items():assert abs(v-case['node_voltage_V'][node])<1e-12
        current=(vr-vb)/a;max_error=max(max_error,abs(current-case['fixed_source_current_A'][ref]))
        assert abs(current-case['fixed_source_current_A'][ref])<1e-12
        check(mon,case,{ref,n19,n12,GND},{v7:-j7,v8:-j8})
    assert ref_seen==set(itertools.product([.985,1.020],[0.,-19.,-30.],[0.,-12.,-30.],
        itertools.product([.97,1.03],repeat=6),itertools.product([-30e-9,30e-9],repeat=2)))
    reference_currents=[c['fixed_source_current_A'][ref] for c in mon['cases']]
    assert mon['reference_current_range_A']==[min(reference_currents),max(reference_currents)]
    assert mon['margin_to_1mA_output_load_A']==.001-max(reference_currents)
    nominal=mon['nominal'];a,b,c,e,f,g=[r['nominal_ohm'] for r in mon['resistors']]
    vb=(1/a-19/(c+e)-12/(f+g))/(1/a+1/b+1/(c+e)+1/(f+g))
    assert abs(nominal['fixed_source_current_A'][ref]-(1-vb)/a)<1e-12

    for case in fast['cases']:
        key=(case['AUX_V'],case['output_ideal_HIGH'],case['VIN_V'],tuple(case['resistor_factors']))
        assert key not in fast_seen;fast_seen.add(key)
        a,b,c,e,f=[r['nominal_ohm']*factor for r,factor in zip(fast['resistors'],case['resistor_factors'])]
        vo=case['AUX_V'] if case['output_ideal_HIGH'] else 0.
        vs=(case['VIN_V']/a+vo/c)/(1/a+1/b+1/c);vg=vo*e/(e+f)
        current=(vo-vs)/c+vo/(e+f)
        assert abs(vs-case['node_voltage_V'][sense])<1e-12
        assert abs(vg-case['node_voltage_V'][gate])<1e-12
        max_error=max(max_error,abs(current-case['fixed_source_current_A'][output]))
        assert abs(current-case['fixed_source_current_A'][output])<1e-12
        valid=(.1 if case['AUX_V']<2.5 else 0.)<=vs<=case['AUX_V']+.1
        assert valid==case['sense_within_datasheet_common_mode_interval'];outside+=not valid
        check(fast,case,{output,vin,GND},{})
    assert fast_seen==set(itertools.product([2.3,2.7],[False,True],[0.,10.8,12.,13.2,15.,24.,30.],
        itertools.product([.97,1.03],repeat=5)))
    fast_currents=[c['fixed_source_current_A'][output] for c in fast['cases']]
    assert fast['output_current_range_A']==[min(fast_currents),max(fast_currents)]
    assert fast['outside_common_mode_case_count']==outside
    assert outside>0 and min(fast_currents)<0<max(fast_currents)
    actual={(x['ref'],x['pin']) for x in nets[AUX] if x['pintype']=='power_in'}
    inventory=d['IC_supply_inventory'];assert len(inventory)==len(actual)==81
    assert {(r['ref'],r['AUX_supply_pin']) for r in inventory}==actual
    families=defaultdict(list)
    for row in inventory:
        ref=row['ref'];assert row['part']==parts[ref].findtext('value') and row['all_pins']==pins[ref]
        assert row['all_contacts']==[dict(x,net=n) for n,contacts in nets.items() for x in contacts if x['ref']==ref]
        families[row['part']].append(ref)
    assert dict(families)==d['IC_supply_families'] and len(families)==29
    for r,package in d['monitored_packages'].items():
        assert package==dict(part=parts[r].findtext('value'),pins=pins[r])
    assert d['P_U26_output_receiver_contacts']==nets[pins['P_U26']['4']]
    prior=set()
    for name in d['source_sha256']:
        if not name.endswith(('/analysis.json','/output-loads.json')):continue
        data=json.loads((REPO/name).read_text())
        for key in ['networks','reference_networks','amplifier_channels']:
            prior|={r['ref'] for g in data.get(key,[]) for r in g['resistors']}
        prior|=set(data.get('resistor_order',[]))
        prior|={r['resistor'] for r in data.get('all_direct_ground_resistors_from_aux_supplied_packages',[])}
    assert not prior&set(exact)
    report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in
        [Path(__file__),OUT/'analysis.json',SOURCE,REPO/'hardware/fabrication/assess_two_board_aux_load.py']},
        reference_cases_verified=len(ref_seen),fast_OV_cases_verified=len(fast_seen),
        maximum_closed_form_current_difference_A=max_error,IC_supply_pins_verified=81,IC_families_verified=29,
        disjoint_new_resistors_verified=11,fast_OV_common_mode_exclusions_verified=outside,
        complete_current_bound_established=False,fabrication_released=False)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'}))


if __name__=='__main__':run()
