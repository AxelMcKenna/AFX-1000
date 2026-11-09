"""Independent series-path and ideal-amplifier checks against TBP50 netlist."""
import itertools
import json
from collections import defaultdict
from pathlib import Path

from hardware.fabrication.assess_two_board_aux_load import circuit, numeric, AUX, GND
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

OUT=STAGING/'two-board-aux-reference-amplifier-01'
SOURCE=STAGING/'two-board-power-startup-remaining-native-03/netlist.xml'
REF='PWR_PROTECT_REF'


def run():
    assert not (OUT/'verification.json').exists()
    result=json.loads((OUT/'analysis.json').read_text())
    for p,h in result['source_sha256'].items(): assert sha(REPO/p)==h
    parts,nets,pins=circuit(SOURCE)
    expected_paths=[['E_R94']]+[[f'N_R{i}' for i in row] for row in
        [(25,26,27),(29,30,31),(33,34,35),(42,43,44),(46,47),(49,50,51)]]
    feedbacks=[[f'E_R{i}' for i in row] for row in
        [(59,60,61),(62,63,64),(67,68,69),(70,71,72),(75,76,77),(80,81,82),(85,86,87)]]
    groups={g['id']:g for g in result['reference_networks']}
    direct={x['ref'] for x in nets[REF] if x['ref'].split('_')[-1].startswith('R')}
    assert direct==set(groups)=={p[0] for p in expected_paths+feedbacks}
    maximum_difference=0.; reference_cases=0; amplifier_cases=0; transfer_count=0

    def check_path(refs, start, stop):
        node=start
        for ref in refs:
            a,b=pins[ref].values(); assert node in [a,b]
            node=b if node==a else a
        assert node==stop

    def validate_rows(group):
        for row in group['resistors']:
            ref=row['ref']
            assert row['value']==parts[ref].findtext('value')
            assert row['nominal_ohm']==numeric(parts[ref].findtext('value'))
            assert row['nets']==list(pins[ref].values())
        assert set(group['nodes'])=={n for r in group['resistors'] for n in pins[r['ref']].values()}
        owned={r['ref'] for r in group['resistors']}
        for node,contacts in group['non_resistor_contacts'].items():
            assert contacts==[dict(x,value=parts[x['ref']].findtext('value'))
                              for x in nets[node] if x['ref'] not in owned]

    def physical_check(group, case, fixed):
        nonlocal maximum_difference
        voltage=case['node_voltage_V']; balance=defaultdict(float); dissipation=0.
        for row,f in zip(group['resistors'],case['resistor_factors']):
            ref=row['ref']; a,b=pins[ref].values(); r=numeric(parts[ref].findtext('value'))*f
            current=(voltage[a]-voltage[b])/r
            assert abs(current-case['resistor_current_A'][ref])<1e-12
            balance[a]+=current;balance[b]-=current;dissipation+=current*current*r
        for node,current in balance.items():
            if node not in fixed: assert abs(current)<1e-12,(node,current)
        assert abs(sum(voltage[n]*current for n,current in balance.items())-dissipation)<1e-12
        return balance

    for path in expected_paths+feedbacks:
        group=groups[path[0]];validate_rows(group)
        assert {r['ref'] for r in group['resistors']}==set(path)
        is_feedback=path in feedbacks
        check_path(path,REF,AUX if is_feedback else GND)
        sink=set(pins[path[-1]].values())-{AUX} if is_feedback else set()
        assert sink==set(group['sink_nodes'])
        expected={(v,w,flags,factors) for v,w,flags,factors in itertools.product(
            [2.3,2.7],[1.2375,1.2625],itertools.product([False,True],repeat=len(sink)),
            itertools.product([.97,1.03],repeat=len(path)))}
        found=set()
        for case in group['cases']:
            low=bool(case['ideal_sinks_low'])
            key=(case['AUX_V'],case['reference_V'],(low,) if sink else (),tuple(case['resistor_factors']))
            assert key not in found;found.add(key)
            resistance={r['ref']:r['nominal_ohm']*f for r,f in zip(group['resistors'],case['resistor_factors'])}
            v,w=case['AUX_V'],case['reference_V']
            if is_feedback:
                expected_i=w/sum(resistance[r] for r in path[:2]) if low else (w-v)/sum(resistance.values())
            else: expected_i=w/sum(resistance.values())
            maximum_difference=max(maximum_difference,abs(expected_i-case['reference_source_A']))
            assert abs(expected_i-case['reference_source_A'])<1e-12
            fixed={AUX,REF,GND}|set(case['ideal_sinks_low'])
            balance=physical_check(group,case,fixed)
            assert abs(balance[REF]-expected_i)<1e-12
            reference_cases+=1
        assert found==expected
        assert group['reference_current_range_A']==[
            min(c['reference_source_A'] for c in group['cases']),max(c['reference_source_A'] for c in group['cases'])]

    specs={
        'E_U8.1':(['E_R49','E_R50'],'E_R51',['E_R52','N_R36'],'PWR_N19_SOURCE',-19.),
        'E_U8.7':(['E_R53'],'E_R54',['E_R55','N_R52'],'PWR_N12_SOURCE',-12.),
        'N_U13.1':(['N_R23'],'N_R24',['N_R28','N_R32'],'PWR_N19',-19.),
        'N_U13.7':(['N_R40'],'N_R41',['N_R45','N_R48'],'PWR_N12',-12.)}
    assert {g['id'] for g in result['amplifier_channels']}==set(specs)
    for group in result['amplifier_channels']:
        validate_rows(group)
        inputs,feedback,senses,rail,nominal=specs[group['id']]
        assert set(group['input_resistors'])==set(inputs)
        assert group['feedback_resistor']==feedback and group['rail_node']==rail and group['nominal_rail_V']==nominal
        assert {r['ref'] for r in group['resistors']}==set(inputs+[feedback]+senses)
        package,out=group['id'].split('.'); inv='2' if out=='1' else '6'
        assert group['output_node']==pins[package][out] and group['summing_node']==pins[package][inv]
        check_path(inputs,rail,group['summing_node'])
        check_path([feedback],group['output_node'],group['summing_node'])
        seen=set()
        for case in group['cases']+[dict(resistor_factors=[1.]*len(group['resistors']),**group['nominal'])]:
            f=tuple(case['resistor_factors']);assert f not in seen;seen.add(f)
            r={row['ref']:row['nominal_ohm']*fac for row,fac in zip(group['resistors'],f)}
            # At virtual ground, input-chain current must be supplied by feedback.
            current=-nominal/sum(r[x] for x in inputs);voltage=current*r[feedback]
            maximum_difference=max(maximum_difference,abs(current-case['output_source_A']))
            assert abs(current-case['output_source_A'])<1e-12
            assert abs(voltage-case['output_V'])<1e-10
            balance=physical_check(group,case,{rail,group['output_node']})
            assert abs(balance[group['output_node']]-current)<1e-12
            assert abs(case['node_voltage_V'][group['summing_node']])<1e-12
            if f!=(1.,)*len(f):amplifier_cases+=1
        assert seen==set(itertools.product([.97,1.03],repeat=len(group['resistors'])))|{(1.,)*len(group['resistors'])}
        for response in group['nominal_pin_injection_transfers']:
            assert abs(response['output_A_change_per_A']+1.)<1e-8
            expected=-numeric(parts[feedback].findtext('value')) if response['node']==group['summing_node'] else 0.
            assert abs(response['output_V_change_per_A']-expected)<1e-6
            transfer_count+=1

    prior=json.loads((STAGING/'two-board-aux-resistor-networks-01/analysis.json').read_text())
    a={r['ref'] for g in prior['networks'] for r in g['resistors']}
    b={r['ref'] for g in groups.values() for r in g['resistors']}
    c={r['ref'] for g in result['amplifier_channels'] for r in g['resistors']}
    assert len(a&b)==21 and len(b-a)==18 and len(c)==17 and not c&(a|b)
    assert result['reference_shared_with_prior_AUX_resistors']==sorted(a&b)
    assert result['reference_new_resistors']==sorted(b-a)
    assert result['amplifier_resistors']==sorted(c)
    for field,index in [('reference_sum_of_branch_minima_A',0),('reference_sum_of_branch_maxima_A',1)]:
        assert result[field]==sum(g['reference_current_range_A'][index] for g in groups.values())
    assert result['amplifier_nominal_output_sum_A']==sum(g['nominal']['output_source_A'] for g in result['amplifier_channels'])
    assert result['amplifier_conditional_output_max_sum_A']==sum(max(c['output_source_A'] for c in g['cases']) for g in result['amplifier_channels'])
    assert result['reference_direct_contacts']==nets[REF]
    assert result['reference_sum_of_branch_minima_A']>0
    report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in
        [Path(__file__),OUT/'analysis.json',SOURCE,REPO/'hardware/fabrication/assess_two_board_aux_load.py']},
        reference_paths_checked=14,reference_corner_cases_checked=reference_cases,
        amplifier_channels_checked=4,amplifier_corner_cases_checked=amplifier_cases,
        amplifier_pin_injection_transfers_checked=transfer_count,
        maximum_closed_form_current_difference_A=maximum_difference,
        shared_resistors_counted_as_two_distinct_source_ports_not_duplicate_loads=True,
        reference_remains_net_source_with_zero_leakage=True,
        complete_current_bound_established=False,fabrication_released=False)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'}))


if __name__=='__main__':run()
