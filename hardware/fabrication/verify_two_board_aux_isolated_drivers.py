"""Independent nodal and source-ownership checks for the Si8751 ledger."""
import itertools
import json
from pathlib import Path

import numpy as np

from hardware.fabrication.assess_two_board_aux_load import circuit,numeric,AUX,GND
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

OUT=STAGING/'two-board-aux-isolated-drivers-01'
SOURCE=STAGING/'two-board-power-startup-remaining-native-03/netlist.xml'
MASTER='E_rail_disconnect/E28_MASTER_ENABLE'


def run():
    assert not (OUT/'verification.json').exists()
    d=json.loads((OUT/'analysis.json').read_text())
    for name,h in d['source_sha256'].items():assert sha(REPO/name)==h
    parts,nets,pins=circuit(SOURCE)
    ordered=[]
    for i,driver in enumerate(d['drivers']):
        ref=f'E_U{i+1}';assert driver['ref']==ref and driver['pins']==pins[ref]
        assert driver['part']==parts[ref].findtext('value')=='SI8751AB-ISR'
        assert pins[ref]['1']==AUX and pins[ref]['4']==GND
        for field,offset in [('series',4),('pulldown',5),('timing',3),('gate_series',1),('gate_pulldown',2)]:
            row=driver[field];r=f'E_R{8*i+offset}'
            assert row==dict(ref=r,value=parts[r].findtext('value'),nominal_ohm=numeric(parts[r].findtext('value')),pins=pins[r])
        series=driver['series']['ref'];down=driver['pulldown']['ref'];timing=driver['timing']['ref']
        ordered += [series,down]
        assert set(pins[series].values())=={MASTER,pins[ref]['3']}
        assert set(pins[down].values())=={GND,pins[ref]['3']}
        assert set(pins[timing].values())=={GND,pins[ref]['2']}
        assert {x['ref'] for x in nets[pins[ref]['2']]}=={ref,timing}
        assert {x['ref'] for x in nets[pins[ref]['3']]}=={ref,series,down}
        gate=driver['gate_net'];common=driver['common_net']
        assert common==pins[ref]['5']
        assert set(pins[driver['gate_series']['ref']].values())=={pins[ref]['8'],gate}
        assert set(pins[driver['gate_pulldown']['ref']].values())=={gate,common}
        assert driver['gate_contacts']==nets[gate] and driver['common_contacts']==nets[common]
        assert {x['ref'] for x in driver['FETs']}=={f'E_Q{2*i+1}',f'E_Q{2*i+2}'}
        for fet in driver['FETs']:
            q=fet['ref'];assert fet['part']==parts[q].findtext('value')=='CSD18540Q5B'
            assert fet['pins']==pins[q] and pins[q]['1']==common and pins[q]['2']==gate
        for miller in driver['miller_capacitors']:
            cap=miller['capacitor'];limit=miller['series_limit']['ref']
            assert miller['capacitor_pins']==pins[cap]
            assert miller['value']==parts[cap].findtext('value')=='10pF 100V C0G 5%'
            assert miller['series_limit']['pins']==pins[limit]
            assert miller['series_limit']['nominal_ohm']==numeric(parts[limit].findtext('value'))==15000
            intermediate=set(pins[cap].values()) & set(pins[limit].values());assert len(intermediate)==1
            assert set(pins[cap].values())-intermediate=={pins[ref][miller['driver_pin']]}
            assert set(pins[limit].values())-intermediate=={miller['drain_net']}
            assert miller['drain_net'] in {pins[q['ref']]['3'] for q in driver['FETs']}
        clamp=driver['external_clamp']
        if i in [1,3]:
            relay,rs=('N_U6','N_R7') if i==1 else ('N_U12','N_R14')
            assert clamp['relay']==relay and clamp['pins']==pins[relay]
            assert clamp['part']==parts[relay].findtext('value')
            assert clamp['series']['ref']==rs and clamp['series']['nominal_ohm']==numeric(parts[rs].findtext('value'))==220
            assert set(pins[rs].values())=={gate,pins[relay]['4']} and pins[relay]['6']==common
        else:assert clamp is None
    ordered+=['E_R104','E_R141'];assert d['resistor_order']==ordered
    assert [(x['ref'],x['pin']) for x in nets[MASTER] if x['pintype']=='output']==[('E_U29','7')]
    assert d['master_driver']['contacts']==nets[MASTER]
    assert pins['E_U29']['8']==AUX and pins['E_U29']['4']==GND
    for row in d['master_pulldowns']:
        assert row['pins']==pins[row['ref']] and set(row['pins'].values())=={MASTER,GND}
        assert row['nominal_ohm']==numeric(parts[row['ref']].findtext('value'))
    all_new=set(ordered)-{'E_R104','E_R141'}
    assert set(d['new_resistors'])==all_new and set(d['previously_counted_resistors'])=={'E_R104','E_R141'}
    old=json.loads((STAGING/'two-board-aux-current-reconciliation-01/output-loads.json').read_text())
    old_by_ref={r['resistor']:r for r in old['all_direct_ground_resistors_from_aux_supplied_packages']}
    assert set(ordered)&old_by_ref.keys()=={'E_R104','E_R141'}
    for ref in ['E_R104','E_R141']:
        assert old_by_ref[ref]['driver_ref']=='E_U29' and old_by_ref[ref]['driver_pin']=='7'

    # Five node voltages and ideal MASTER voltage-source current are unknowns.
    nodes=[MASTER]+[pins[f'E_U{i}']['3'] for i in range(1,5)]
    index={n:i for i,n in enumerate(nodes)}
    seen=set();max_error=0.;transfers=set()
    maxima={k:0. for k in d['conditional_maxima']}
    high=[];low=[]
    for case in d['cases']:
        key=(case['master_V'],tuple(case['resistor_factors']));assert key not in seen;seen.add(key)
        resistances={r:numeric(parts[r].findtext('value'))*f for r,f in zip(ordered,case['resistor_factors'])}
        m=np.zeros((6,6));rhs=np.zeros(6);rhs[-1]=case['master_V']
        for r,res in resistances.items():
            a,b=pins[r].values()
            for left,right in [(a,b),(b,a)]:
                if left==GND:continue
                m[index[left],index[left]]+=1/res
                if right!=GND:m[index[left],index[right]]-=1/res
        m[0,-1]=-1.;m[-1,0]=1.
        answer=np.linalg.solve(m,rhs)
        assert max(abs(m@answer-rhs))<1e-12
        max_error=max(max_error,abs(answer[-1]-case['master_total_A']))
        assert abs(answer[-1]-case['master_total_A'])<1e-12
        branch_sum=0.
        for i,branch in enumerate(case['branches']):
            top=resistances[ordered[2*i]];bottom=resistances[ordered[2*i+1]]
            current=(answer[0]-answer[i+1])/top
            assert branch['driver']==f'E_U{i+1}' and branch['pin_sink_A']==0.
            assert abs(branch['input_V']-answer[i+1])<1e-12
            assert abs(branch['master_A']-current)<1e-12
            assert abs(branch['pulldown_A']-answer[i+1]/bottom)<1e-12
            assert abs(current-answer[i+1]/bottom)<1e-12
            branch_sum+=current
            transfer_key=(i,top,bottom)
            if transfer_key not in transfers:
                shifted_rhs=rhs.copy();shifted_rhs[i+1]-=1e-6
                shifted=np.linalg.solve(m,shifted_rhs)
                assert abs((shifted[-1]-answer[-1])/1e-6-branch['master_A_per_input_sink_A'])<1e-8
                assert abs((shifted[i+1]-answer[i+1])/1e-6-branch['input_V_per_input_sink_A'])<1e-6
                transfers.add(transfer_key)
            if case['master_V']==1.85:high.append(answer[i+1])
            if case['master_V']==.45:low.append(answer[i+1])
        direct=answer[0]/resistances['E_R104']+answer[0]/resistances['E_R141']
        assert abs(case['new_driver_input_resistors_A']-branch_sum)<1e-12
        assert abs(case['previously_counted_master_pulldowns_A']-direct)<1e-12
        for k in maxima:maxima[k]=max(maxima[k],case[k])
    assert seen==set(itertools.product([0.,.45,1.85,2.7],itertools.product([.97,1.03],repeat=10)))
    assert maxima==d['conditional_maxima']
    expected_new=4*2.7/(10100*.97)
    expected_existing=2.7/(47000*.97)+2.7/(10000*.97)
    assert abs(maxima['new_driver_input_resistors_A']-expected_new)<1e-12
    assert abs(maxima['previously_counted_master_pulldowns_A']-expected_existing)<1e-12
    assert abs(d['conditional_HIGH_minimum_input_V']-min(high))<1e-12
    assert abs(d['conditional_LOW_maximum_input_V']-max(low))<1e-12
    assert abs(d['HIGH_margin_to_0p5_times_2p7V']-(min(high)-1.35))<1e-12
    assert abs(d['LOW_margin_to_0p25_times_2p3V']-(.575-max(low)))<1e-12
    assert abs(d['residual_master_source_current_to_3p1mA_A']-(.0031-expected_new-expected_existing))<1e-12
    report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in
        [Path(__file__),OUT/'analysis.json',SOURCE,REPO/'hardware/fabrication/assess_two_board_aux_load.py']},
        driver_and_gate_networks_verified=4,independent_MNA_cases=len(seen),
        pin_current_transfer_pairs_verified=len(transfers),maximum_source_current_difference_A=max_error,
        existing_two_pulldowns_not_counted_twice=True,
        new_input_divider_resistors_verified=8,
        actual_gate_loading_differs_from_driver_table_condition=True,
        current_and_timing_qualification_complete=False,fabrication_released=False)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'}))


if __name__=='__main__':run()
