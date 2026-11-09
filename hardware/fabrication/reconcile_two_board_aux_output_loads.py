"""Assign direct output pulldowns by actual output supply, not package presence.

Conditional DC resistor screens are not a complete AUX current guarantee.
Historical allocations remain intact until all their terms are reconciled.
"""
import itertools
import json
from pathlib import Path

from hardware.fabrication.assess_two_board_aux_load import circuit, numeric, AUX, GND
from hardware.fabrication.assess_two_board_buck_enable_dc import solve
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

SOURCE = STAGING / 'two-board-power-startup-remaining-native-03'
OUT = STAGING / 'two-board-aux-current-reconciliation-01'


def output_rail(ref, pin, parts, pins, nodes):
    value = parts[ref].findtext('value')
    if value == 'SN74LVC2T45DCUR':
        assert pins[ref]['5'] == pins[ref]['1'], 'DIR must select A to B'
        assert pin in ['6', '7'], 'Unexpected active translator output'
        return pins[ref]['8']
    supply = {net for net, rows in nodes.items() for row in rows
              if row['ref'] == ref and row['pintype'] == 'power_in' and net != GND}
    assert len(supply) == 1, (ref, supply)
    return next(iter(supply))


def run():
    target = OUT / 'output-loads.json'
    assert not target.exists()
    review = json.loads((SOURCE / 'review.json').read_text())
    for name, digest in review['artifact_sha256'].items():
        assert sha(SOURCE / name) == digest
    parts, nets, pins = circuit(SOURCE / 'netlist.xml')
    supplied = {row['ref'] for row in nets[AUX] if row['pintype'] == 'power_in'}
    assert len(supplied) == 81
    rows = []
    for ref in sorted(parts):
        if not ref.split('_')[-1].startswith('R') or GND not in pins[ref].values():
            continue
        net = next(n for n in pins[ref].values() if n != GND)
        drivers = [r for r in nets[net] if r['ref'] in supplied
                   and r['pintype'] in ['output', 'power_out']]
        if not drivers:
            continue
        assert len(drivers) == 1, (ref, drivers)
        driver = drivers[0]
        owner = output_rail(driver['ref'], driver['pin'], parts, pins, nets)
        value = parts[ref].findtext('value')
        reference = driver['ref'] == 'E_U7'
        # Existing 2.7 V rail and 3% resistor allowances are requirements,
        # not acceptance of actual voltage, MPN drift or board leakage.
        voltage = 1.2625 if reference else 2.7 if owner == AUX else 5.2
        resistance = numeric(value)
        rows.append(dict(resistor=ref, value=value, nominal_ohm=resistance,
            net=net, driver_ref=driver['ref'], driver_pin=driver['pin'],
            driver_part=parts[driver['ref']].findtext('value'), output_supply=owner,
            output_class='reference' if reference else 'logic',
            high_voltage_requirement_V=voltage, resistor_lower_fraction_requirement=.97,
            resistor_bound_explicit_in_value='3%' in value and 'RECEIVING' in value,
            nominal_at_upper_voltage_A=voltage/resistance,
            conditional_high_resistor_A=voltage/(resistance*.97),
            low_ideal_resistor_A=0., leakage_and_dynamic_current_included=False,
            connections=nets[net]))
    assert len(rows) == 25
    aux = [r for r in rows if r['output_supply'] == AUX and r['output_class'] == 'logic']
    other = [r for r in rows if r['output_supply'] != AUX]
    assert len(aux) == 22
    assert {r['resistor'] for r in other} == {'N_R61', 'N_R78'}
    nf = [r for r in aux if r['resistor'].startswith('N_')]
    assert {r['resistor'] for r in nf} == {'N_R3','N_R10',*[f'N_R{i}' for i in range(15,23)],'N_R68','N_R85'}
    assert len(nf) == 12 and all(r['resistor_bound_explicit_in_value'] for r in nf)
    u42 = [r for r in aux if r['driver_ref'] == 'E_U42']
    assert {r['resistor'] for r in u42} == {'N_R15', 'N_R16'}
    assert all(r['nominal_ohm'] == 47000 for r in u42)
    u42nets = {pin: nets[pins['E_U42'][pin]] for pin in ['1','3','6','7','5','2']}
    assert {(x['ref'],x['pin']) for x in u42nets['2']} == {('E_U42','2'),('N_J1','5'),('N_R16','1'),('N_U35','1')}
    assert {(x['ref'],x['pin']) for x in u42nets['5']} == {('E_U42','5'),('N_J1','6'),('N_R15','1'),('N_U35','2')}
    assert {(x['ref'],x['pin']) for x in u42nets['7']} == {('E_U42','7'),('E_U26','10')}
    # Native shared READY network; the original full-pullup fault term must
    # not be added again merely because its released state also draws current.
    rr = ['P_R110','P_R204','P_R205','P_R224','P_R225']
    nom = [numeric(parts[r].findtext('value')) for r in rr]
    assert nom == [1000,10000,22000,10000,22000]
    ready = pins['P_R110']['2']
    assert pins['P_R110']['1'] == AUX
    assert {pins[r]['1'] for r in ['P_R204','P_R224']} == {ready}
    assert pins['P_R204']['2'] == pins['P_R205']['1'] == pins['P_U20']['7']
    assert pins['P_R224']['2'] == pins['P_R225']['1'] == pins['P_U23']['7']
    assert pins['P_R205']['2'] == pins['P_R225']['2'] == GND
    assert {(x['ref'],x['pin']) for x in nets[ready]} == {
        ('P_J103','2'),('P_J22','3'),('P_R110','2'),('P_R204','1'),
        ('P_R224','1'),('P_U101','16'),('P_U26','6')}
    cases = []
    for tol in itertools.product([.99,1.01], repeat=5):
        res = [a*b for a,b in zip(nom,tol)]
        for voltage, di, ai, leak in itertools.product([2.3,2.7],[0,25e-6],[0,25e-6],[-10.15e-6,10.15e-6]):
            v = solve(res,voltage,di,ai,leak)
            i = (voltage-v[0])/res[0]
            # KCL, independently summing both ground legs and injected currents.
            assert abs(i-(v[1]/res[2]+v[2]/res[4]-di-ai-leak)) < 1e-14
            cases.append(dict(resistor_ohm=res,AUX_V=voltage,D_EN_source_A=di,
                A_EN_source_A=ai,ready_injected_A=leak,ready_V=v[0],
                AUX_source_A=i,ground_leg_A=[v[1]/res[2],v[2]/res[4]]))
    assert len(cases) == 512
    nominal = 2.7/(1000+1/(1/32000+1/32000))
    direct = [dict(ref=x['ref'],pin=x['pin'],value=parts[x['ref']].findtext('value'),pins=pins[x['ref']])
              for x in nets[AUX] if x['ref'].split('_')[-1].startswith('R')]
    assert len(direct) == 45
    primaries = {
        'sn74lvc3g17': dict(revision='SCES470F',pages=[5],url='https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf',
            scope='10 uA no-load ICC has VI=5.5V or GND; 500 uA delta-ICC has VCC=3..5.5V and one VI=VCC-0.6V. Not an actual AUX-band transition bound.'),
        'sn74hcs08': dict(revision='SCLS778D',pages=[5],url='https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf',
            scope='1 uA input leakage maximum is at VCC=6V and VI=VCC or 0. No extrapolated continuous 2.3..2.7V leakage/current guarantee is asserted.'),
        'sn74lvc2t45': dict(revision='SCES516N',pages=[1,2],url='https://www.ti.com/lit/ds/symlink/sn74lvc2t45.pdf',
            scope='DCU B1/B2 are pins7/6, powered from VCCB pin8; DIR at VCCA selects A-to-B.'),
        'tps7a16': dict(revision='SBVS171F',pages=[4,11],url='https://www.ti.com/lit/ds/symlink/tps7a16.pdf',
            scope='DELAY sets PG timing after the output threshold; internal output soft start is distinct. Do not infer the AUX ramp from C110.')}
    source_paths = [Path(__file__),SOURCE/'netlist.xml',SOURCE/'review.json',
        STAGING/'two-board-fabrication-status-50/status.json',
        STAGING/'two-board-aux-distribution-survey-02/inventory.json',
        REPO/'hardware/fabrication/assess_two_board_aux_load.py',
        REPO/'hardware/fabrication/assess_two_board_buck_enable_dc.py',
        REPO/'hardware/qualification/boards/startup_negative_circuit/compact/analyze.py',
        REPO/'hardware/qualification/boards/startup_negative_circuit/compact/components.json',
        REPO/'hardware/qualification/boards/startup_negative_circuit/uv_recovery/analyze.py',
        *[OUT/'primary'/(name+'.pdf') for name in primaries]]
    result = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in source_paths},
        selected_revision='TBP50',all_direct_ground_resistors_from_aux_supplied_packages=rows,
        aux_logic_direct_pulldown_count=len(aux),aux_logic_direct_pulldown_conditional_sum_A=sum(r['conditional_high_resistor_A'] for r in aux),
        NF_aux_output_pulldown_count=len(nf),NF_aux_output_pulldown_conditional_sum_A=sum(r['conditional_high_resistor_A'] for r in nf),
        RAW5_output_loads_excluded_from_AUX=[r['resistor'] for r in other],
        U42_output_resistors=u42,U42_output_resistor_conditional_sum_A=sum(r['conditional_high_resistor_A'] for r in u42),
        U42_connected_inputs_outputs=u42nets,
        READY_released=dict(references=rr,nominal_zero_injection_at2p7_A=nominal,
            previous_released_allocation_A=2e-6,nominal_released_delta_A=nominal-2e-6,
            cases=cases,source_current_range_A=[min(c['AUX_source_A'] for c in cases),max(c['AUX_source_A'] for c in cases)],
            initial_tolerance_only=True,EN_and_ready_currents_are_unqualified_allocations=True,
            external_J103_J22_loads_assumed_absent=True,asserted_full_pullup_current_is_already_a_separate_historical_term=True),
        direct_AUX_resistors_requiring_full_network_state_accounting=direct,
        primary_tables=primaries,primary_pages_visually_reviewed=False,
        historical_NF_aggregate_reserve_reduced=False,historical_E28_external_output_reserve_reduced=False,
        ownership_scope='Explicit direct output-to-ground resistor branches only. Supply ICC, input leakage, resistor networks, reference/OPA loads, capacitive switching, isolated-driver power and external/clamp loads remain separate.',
        historical_nine_pulldown_term_has_no_per_resistor_ownership_proof=True,
        current_bound_established=False,loaded_source_startup_and_thermal_qualified=False,fabrication_released=False)
    with target.open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ['aux_logic_direct_pulldown_count','aux_logic_direct_pulldown_conditional_sum_A','NF_aux_output_pulldown_count','NF_aux_output_pulldown_conditional_sum_A','U42_output_resistor_conditional_sum_A']}))
    print(json.dumps(result['READY_released']['source_current_range_A']))


if __name__ == '__main__':
    run()
