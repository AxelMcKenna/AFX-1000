"""Independently check direct-load coverage, domain assignment and READY KCL."""
import copy
import json
from pathlib import Path
from hardware.fabrication.assess_two_board_aux_load import circuit, numeric, AUX, GND
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

OUT = STAGING / 'two-board-aux-current-reconciliation-01'


def run():
    report = OUT/'output-loads.json'
    d = json.loads(report.read_text())
    for name, digest in d['source_sha256'].items():
        assert sha(REPO/name) == digest, name
    path = STAGING/'two-board-power-startup-remaining-native-03/netlist.xml'
    parts, nets, pins = circuit(path)
    supplied = {x['ref'] for x in nets[AUX] if x['pintype']=='power_in'}
    actual = {}
    for net, nodes in nets.items():
        drivers = [x for x in nodes if x['ref'] in supplied and x['pintype'] in ['output','power_out']]
        for x in nodes:
            ref = x['ref']
            if not ref.split('_')[-1].startswith('R') or GND not in pins[ref].values() or not drivers:
                continue
            assert len(drivers)==1
            driver = drivers[0]
            supply = pins[driver['ref']]['8'] if driver['ref'] in ['N_U16','N_U27'] else AUX
            actual[ref] = (driver['ref'],driver['pin'],supply,net,numeric(parts[ref].findtext('value')))
    rows = d['all_direct_ground_resistors_from_aux_supplied_packages']
    def matches(rows):
        return {r['resistor']:(r['driver_ref'],r['driver_pin'],r['output_supply'],r['net'],r['nominal_ohm']) for r in rows}==actual and len(rows)==len(actual)
    assert matches(rows) and len(actual)==25
    wrong = copy.deepcopy(rows)
    for r in wrong:
        if r['driver_ref'] in ['N_U16','N_U27']:
            r['output_supply']=pins[r['driver_ref']]['1']
    assert not matches(wrong), 'VCCA-for-all-outputs mutation not rejected'
    assert not matches(rows[:-1]), 'Missing resistor not rejected'
    assert not matches(rows+[rows[0]]), 'Duplicate resistor not rejected'
    for r in rows:
        assert abs(r['conditional_high_resistor_A']-r['high_voltage_requirement_V']/r['nominal_ohm']/.97)<1e-15
    aux=[r for r in rows if r['output_supply']==AUX and r['output_class']=='logic']
    assert len(aux)==22 and abs(sum(r['conditional_high_resistor_A'] for r in aux)-d['aux_logic_direct_pulldown_conditional_sum_A'])<1e-15
    assert abs(d['U42_output_resistor_conditional_sum_A']-2*2.7/(47000*.97))<1e-15
    current=[]
    for c in d['READY_released']['cases']:
        rp,sd,gd,sa,ga=c['resistor_ohm']
        ready=(c['AUX_V']/rp+c['ready_injected_A']+c['D_EN_source_A']*gd/(sd+gd)+c['A_EN_source_A']*ga/(sa+ga))/(1/rp+1/(sd+gd)+1/(sa+ga))
        i=(c['AUX_V']-ready)/rp
        assert abs(ready-c['ready_V'])<1e-12 and abs(i-c['AUX_source_A'])<1e-14
        current.append(i)
    assert len(current)==512
    assert max(abs(a-b) for a,b in zip([min(current),max(current)],d['READY_released']['source_current_range_A']))<1e-14
    assert abs(d['READY_released']['nominal_zero_injection_at2p7_A']-2.7/17000)<1e-15
    assert len(d['direct_AUX_resistors_requiring_full_network_state_accounting'])==45
    assert not any(d[k] for k in ['historical_NF_aggregate_reserve_reduced','historical_E28_external_output_reserve_reduced','current_bound_established','loaded_source_startup_and_thermal_qualified','fabrication_released'])
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),report,path,REPO/'hardware/fabrication/assess_two_board_aux_load.py']},
        report_source_bindings_checked=len(d['source_sha256']),direct_load_rows_checked=25,
        output_domain_assignment_verified=True,missing_duplicate_wrong_domain_mutations_rejected=True,
        independent_READY_closed_form_cases_checked=512,conditional_sums_verified=True,
        complete_current_bound_established=False,fabrication_released=False)
    with (OUT/'verification.json').open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))


if __name__=='__main__':
    run()
