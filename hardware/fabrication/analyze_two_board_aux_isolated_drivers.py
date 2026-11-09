"""Reconcile four Si8751 drivers and their shared master-enable load."""
import itertools
import json
from pathlib import Path

from hardware.fabrication.assess_two_board_aux_load import circuit, numeric, AUX, GND
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

SOURCE=STAGING/'two-board-power-startup-remaining-native-03'
OUT=STAGING/'two-board-aux-isolated-drivers-01'
PRIMARY=REPO/'hardware/qualification/boards/aux_current_partition/sources/primary'
MASTER='E_rail_disconnect/E28_MASTER_ENABLE'


def extract(parts,nets,pins):
    def resistor(ref):
        return dict(ref=ref,value=parts[ref].findtext('value'),
                    nominal_ohm=numeric(parts[ref].findtext('value')),pins=pins[ref])
    def edge(ref,a,b): assert set(pins[ref].values())=={a,b},ref
    assert parts['E_U29'].findtext('value')=='SN74AUP2G08DCUR'
    assert pins['E_U29']['7']==MASTER and pins['E_U29']['8']==AUX and pins['E_U29']['4']==GND
    assert [(x['ref'],x['pin']) for x in nets[MASTER] if x['pintype']=='output']==[('E_U29','7')]
    drivers=[]
    for i in range(4):
        ref=f'E_U{i+1}'; base=8*i
        assert parts[ref].findtext('value')=='SI8751AB-ISR'
        assert pins[ref]['1']==AUX and pins[ref]['4']==GND
        control=pins[ref]['3'];tt=pins[ref]['2'];common=pins[ref]['5'];drive=pins[ref]['8']
        series,down,timing,gate_series,gate_down=[f'E_R{base+j}' for j in [4,5,3,1,2]]
        edge(series,MASTER,control);edge(down,control,GND);edge(timing,tt,GND)
        assert {x['ref'] for x in nets[control]}=={ref,series,down}
        assert {x['ref'] for x in nets[tt]}=={ref,timing}
        assert numeric(parts[series].findtext('value'))==100
        assert numeric(parts[down].findtext('value'))==10000
        assert numeric(parts[timing].findtext('value'))==10000
        gate=next(n for n in pins[gate_series].values() if n!=drive)
        edge(gate_series,drive,gate);edge(gate_down,gate,common)
        fets=[f'E_Q{2*i+j}' for j in [1,2]]
        for q in fets:
            assert parts[q].findtext('value')=='CSD18540Q5B'
            assert pins[q]['1']==common and pins[q]['2']==gate
        miller=[]
        for pin in ['7','6']:
            cap=next(x['ref'] for x in nets[pins[ref][pin]] if x['ref']!=ref)
            assert parts[cap].findtext('value')=='10pF 100V C0G 5%'
            peer=next(n for n in pins[cap].values() if n!=pins[ref][pin])
            limit=next(x['ref'] for x in nets[peer] if x['ref']!=cap)
            assert {x['ref'] for x in nets[peer]}=={cap,limit}
            drain=next(n for n in pins[limit].values() if n!=peer)
            assert numeric(parts[limit].findtext('value'))==15000
            assert drain in {pins[q]['3'] for q in fets}
            miller.append(dict(driver_pin=pin,capacitor=cap,value=parts[cap].findtext('value'),
                capacitor_pins=pins[cap],series_limit=resistor(limit),drain_net=drain))
        clamp=None
        if i in [1,3]:
            relay,rs=('N_U6','N_R7') if i==1 else ('N_U12','N_R14')
            edge(rs,gate,pins[relay]['4']);assert pins[relay]['6']==common
            assert numeric(parts[rs].findtext('value'))==220
            clamp=dict(relay=relay,part=parts[relay].findtext('value'),pins=pins[relay],series=resistor(rs))
        drivers.append(dict(ref=ref,part=parts[ref].findtext('value'),pins=pins[ref],
            series=resistor(series),pulldown=resistor(down),timing=resistor(timing),
            gate_series=resistor(gate_series),gate_pulldown=resistor(gate_down),
            gate_net=gate,common_net=common,FETs=[dict(ref=q,part=parts[q].findtext('value'),pins=pins[q]) for q in fets],
            miller_capacitors=miller,external_clamp=clamp,
            gate_contacts=nets[gate],common_contacts=nets[common]))
    pulldowns=[resistor(r) for r in ['E_R104','E_R141']]
    for row in pulldowns:edge(row['ref'],MASTER,GND)
    actual_resistors={x['ref'] for x in nets[MASTER] if x['ref'].split('_')[-1].startswith('R')}
    assert actual_resistors=={d['series']['ref'] for d in drivers}|{r['ref'] for r in pulldowns}
    return drivers,pulldowns


def solve(drivers,pulldowns,ohms,voltage,pin_sink=None,direct_sink=0.):
    pin_sink=pin_sink or [0.]*4
    branches=[]
    for d,leak in zip(drivers,pin_sink):
        top=ohms[d['series']['ref']];bottom=ohms[d['pulldown']['ref']]
        alpha=bottom/(top+bottom);rth=top*bottom/(top+bottom)
        node=voltage*alpha-leak*rth
        current=(voltage-node)/top
        branches.append(dict(driver=d['ref'],input_V=node,master_A=current,
            pulldown_A=node/bottom,pin_sink_A=leak,
            master_A_per_input_sink_A=alpha,input_V_per_input_sink_A=-rth))
    direct=sum(voltage/ohms[r['ref']] for r in pulldowns)
    return dict(branches=branches,new_driver_input_resistors_A=sum(b['master_A'] for b in branches),
        previously_counted_master_pulldowns_A=direct,
        master_total_A=direct+direct_sink+sum(b['master_A'] for b in branches))


def run():
    assert not (OUT/'analysis.json').exists()
    parts,nets,pins=circuit(SOURCE/'netlist.xml')
    native=json.loads((SOURCE/'review.json').read_text())
    for name,h in native['artifact_sha256'].items():assert sha(SOURCE/name)==h
    drivers,pulldowns=extract(parts,nets,pins)
    rows=[r for d in drivers for r in [d['series'],d['pulldown']]]+pulldowns
    resistor_order=[r['ref'] for r in rows]
    cases=[]
    for voltage,factors in itertools.product([0.,.45,1.85,2.7],itertools.product([.97,1.03],repeat=10)):
        ohms={r['ref']:r['nominal_ohm']*f for r,f in zip(rows,factors)}
        cases.append(dict(master_V=voltage,resistor_factors=list(factors),**solve(drivers,pulldowns,ohms,voltage)))
    maxima={field:max(c[field] for c in cases) for field in
        ['new_driver_input_resistors_A','previously_counted_master_pulldowns_A','master_total_A']}
    high=[b['input_V'] for c in cases if c['master_V']==1.85 for b in c['branches']]
    low=[b['input_V'] for c in cases if c['master_V']==.45 for b in c['branches']]
    previous_file=STAGING/'two-board-aux-current-reconciliation-01/output-loads.json'
    previous=json.loads(previous_file.read_text())
    prior={r['resistor'] for r in previous['all_direct_ground_resistors_from_aux_supplied_packages']}
    assert prior&set(resistor_order)=={'E_R104','E_R141'}
    for name,key in [('two-board-aux-resistor-networks-01','networks'),('two-board-aux-reference-amplifier-01','reference_networks')]:
        earlier=json.loads((STAGING/name/'analysis.json').read_text())
        refs={r['ref'] for g in earlier[key] for r in g['resistors']}
        if 'amplifier_channels' in earlier:refs|={r['ref'] for g in earlier['amplifier_channels'] for r in g['resistors']}
        assert not refs&set(resistor_order)
    sources=[Path(__file__),SOURCE/'netlist.xml',SOURCE/'review.json',previous_file,
        STAGING/'two-board-aux-resistor-networks-01/analysis.json',
        STAGING/'two-board-aux-reference-amplifier-01/analysis.json',
        REPO/'hardware/fabrication/assess_two_board_aux_load.py',PRIMARY/'Si8751.pdf',PRIMARY/'SN74AUP2G08.pdf',
        REPO/'hardware/qualification/boards/startup_negative_protection/sources/primary/csd18540q5b.pdf']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},
        selected_revision='TBP50',drivers=drivers,master_driver=dict(ref='E_U29',pin='7',supply=AUX,contacts=nets[MASTER]),
        master_pulldowns= pulldowns,resistor_order=resistor_order,cases=cases,
        conditional_maxima=maxima,
        conditional_HIGH_minimum_input_V=min(high),conditional_LOW_maximum_input_V=max(low),
        HIGH_margin_to_0p5_times_2p7V=min(high)-.5*2.7,
        LOW_margin_to_0p25_times_2p3V=.25*2.3-max(low),
        residual_master_source_current_to_3p1mA_A=.0031-maxima['master_total_A'],
        new_resistors=sorted(set(resistor_order)-prior),previously_counted_resistors=sorted(set(resistor_order)&prior),
        resistor_fraction_requirement=[.97,1.03],actual_total_resistor_bounds_accepted=False,
        output_voltage_screen=dict(HIGH_floor_V=1.85,LOW_ceiling_V=.45,
            table_scope='AUP2G08 at VCC=2.3V, source/sink3.1mA, full temperature; use over2.3..2.7V here is a conditional receiving envelope, not an added datasheet guarantee.'),
        driver_current_table=dict(IN_equals_VDD_required=True,gate_capacitance_F=100e-12,
            four_TT_10kohm_max_A=4*.0095,four_TT_ground_max_A=4*.017,four_TT_open_max_A=4*.0018,
            OFF_140nA_per_device_is_typical_not_maximum=True,
            TT_resistor_current_is_not_AUX_divided_by_10kohm=True,
            selected_TT_tolerance_and_gate_load_applicability_verified=False),
        gate_load_comparison=dict(two_FETs_per_driver=True,
            Ciss_pair_typ_F=2*3250e-12,Ciss_pair_max_F=2*4230e-12,
            Ciss_conditions='25C, VGS0V, VDS30V,1MHz; not a nonlinear gate-charge or timing model.',
            Qg_pair_10V_typ_C=2*41e-9,Qg_pair_10V_max_C=2*53e-9,
            Qg_conditions='25C, VDS30V, ID28A; not actual installed fault/temperature envelope.',
            gate_clamp_overlap_states_qualified=False,table_turn_on_and_off_times_transferred_to_actual_load=False),
        assumptions='Fixed MASTER voltage, zero receiver/connector leakage, no switching current. Four IN branches share MASTER. Local supply and return drops excluded.',
        complete_master_receiver_voltage_and_current_qualification=False,
        package_supply_currents_added_to_resistor_result=False,
        complete_current_bound_established=False,fabrication_released=False)
    (OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['conditional_maxima','conditional_HIGH_minimum_input_V',
        'conditional_LOW_maximum_input_V','HIGH_margin_to_0p5_times_2p7V','LOW_margin_to_0p25_times_2p3V',
        'residual_master_source_current_to_3p1mA_A']}))


if __name__=='__main__':run()
