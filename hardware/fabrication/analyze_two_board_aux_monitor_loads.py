"""Current monitor reference and fast-OV output loads; conditional DC cases."""
import itertools
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from hardware.fabrication.assess_two_board_aux_load import circuit,numeric,AUX,GND
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

SOURCE=STAGING/'two-board-power-startup-remaining-native-03'
OUT=STAGING/'two-board-aux-monitor-loads-01'


def solve(rows,factors,fixed,injections=None):
    injections=injections or {}
    nodes={n for r in rows for n in r['nets']};free=sorted(nodes-fixed.keys())
    idx={n:i for i,n in enumerate(free)};m=np.zeros((len(free),len(free)));rhs=np.zeros(len(free))
    for row,f in zip(rows,factors):
        a,b=row['nets'];r=row['nominal_ohm']*f
        for left,right in [(a,b),(b,a)]:
            if left not in idx:continue
            i=idx[left];m[i,i]+=1/r
            if right in idx:m[i,idx[right]]-=1/r
            else:rhs[i]+=fixed[right]/r
    for node,current in injections.items():rhs[idx[node]]+=current
    answer=np.linalg.solve(m,rhs);assert max(abs(m@answer-rhs))<1e-12
    v=dict(fixed);v.update(zip(free,map(float,answer)))
    currents={};ports=defaultdict(float);power=0.
    for row,f in zip(rows,factors):
        a,b=row['nets'];r=row['nominal_ohm']*f;i=(v[a]-v[b])/r
        currents[row['ref']]=i;ports[a]+=i;ports[b]-=i;power+=i*i*r
    for n in free:assert abs(ports[n]-injections.get(n,0.))<1e-12
    assert abs(sum(v[n]*i for n,i in ports.items())-power)<1e-12
    return dict(node_voltage_V=v,resistor_current_A=currents,
                fixed_source_current_A={n:ports[n] for n in fixed},resistor_power_W=power)


def run():
    assert not (OUT/'analysis.json').exists()
    parts,nets,pins=circuit(SOURCE/'netlist.xml')
    native=json.loads((SOURCE/'review.json').read_text())
    for name,h in native['artifact_sha256'].items():assert sha(SOURCE/name)==h
    def rows(refs):return [dict(ref=r,value=parts[r].findtext('value'),
        nominal_ohm=numeric(parts[r].findtext('value')),nets=list(pins[r].values())) for r in refs]
    monitor=rows([f'P_R{i}' for i in range(310,316)])
    fast=rows(['P_R115','P_R116','P_R117','P_R120','P_R121'])
    ref=pins['P_U25']['10'];n19='PWR_N19_SOURCE';n12='PWR_N12_SOURCE'
    v7=pins['P_U25']['7'];v8=pins['P_U25']['8']
    reference_cases=[]
    for voltage,rail19,rail12,factors,leaks in itertools.product([.985,1.020],[0.,-19.,-30.],
            [0.,-12.,-30.],itertools.product([.97,1.03],repeat=6),itertools.product([-30e-9,30e-9],repeat=2)):
        fixed={ref:voltage,n19:rail19,n12:rail12,GND:0.}
        s=solve(monitor,factors,fixed,{v7:-leaks[0],v8:-leaks[1]})
        reference_cases.append(dict(reference_V=voltage,N19_V=rail19,N12_V=rail12,
            resistor_factors=list(factors),input_sink_A=list(leaks),**s))
    ref_current=[c['fixed_source_current_A'][ref] for c in reference_cases]
    ref_nominal=solve(monitor,[1.]*6,{ref:1.,n19:-19.,n12:-12.,GND:0.})
    vin=pins['P_R115']['1'];output=pins['P_U103']['1'];sense=pins['P_U103']['3'];gate=pins['P_R121']['2']
    fast_cases=[]
    for aux,high,voltage,factors in itertools.product([2.3,2.7],[False,True],[0.,10.8,12.,13.2,15.,24.,30.],
            itertools.product([.97,1.03],repeat=5)):
        s=solve(fast,factors,{output:aux if high else 0.,vin:voltage,GND:0.})
        # Conservative pin-range check, not a functional comparator/saturation model.
        minimum=.1 if aux<2.5 else 0.;maximum=aux+.1
        fast_cases.append(dict(AUX_V=aux,output_ideal_HIGH=high,VIN_V=voltage,resistor_factors=list(factors),
            sense_within_datasheet_common_mode_interval=minimum<=s['node_voltage_V'][sense]<=maximum,**s))
    fast_current=[c['fixed_source_current_A'][output] for c in fast_cases]
    owned={r['ref'] for r in monitor+fast}
    prior_files=[STAGING/'two-board-aux-resistor-networks-01/analysis.json',
        STAGING/'two-board-aux-reference-amplifier-01/analysis.json',
        STAGING/'two-board-aux-isolated-drivers-01/analysis.json',
        STAGING/'two-board-aux-current-reconciliation-01/output-loads.json']
    prior_res=set()
    for path in prior_files:
        d=json.loads(path.read_text())
        for key in ['networks','reference_networks','amplifier_channels']:
            prior_res|={r['ref'] for g in d.get(key,[]) for r in g['resistors']}
        prior_res|=set(d.get('resistor_order',[]))
        prior_res|={r['resistor'] for r in d.get('all_direct_ground_resistors_from_aux_supplied_packages',[])}
    assert not prior_res&owned and len(owned)==11
    ic_rows=[]
    for node in nets[AUX]:
        if node['pintype']!='power_in':continue
        r=node['ref']
        ic_rows.append(dict(ref=r,part=parts[r].findtext('value'),AUX_supply_pin=node['pin'],
            all_pins=pins[r],all_contacts=[dict(x,net=n) for n,contacts in nets.items() for x in contacts if x['ref']==r],
            current_bound_accepted=False))
    assert len(ic_rows)==len({r['ref'] for r in ic_rows})==81
    families=defaultdict(list)
    for row in ic_rows:families[row['part']].append(row['ref'])
    assert len(families)==29
    mon_nodes={n for r in monitor for n in r['nets']}
    fast_nodes={n for r in fast for n in r['nets']}
    contacts=lambda nodes,refs:{n:[dict(x,value=parts[x['ref']].findtext('value')) for x in nets[n] if x['ref'] not in refs] for n in sorted(nodes)}
    sources=[Path(__file__),SOURCE/'netlist.xml',SOURCE/'review.json',
        REPO/'hardware/fabrication/assess_two_board_aux_load.py']+prior_files
    sources += [OUT/'primary/tlv7011.pdf',OUT/'primary/sn74lvc1g97.pdf']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},selected_revision='TBP50',
        IC_supply_inventory=ic_rows,IC_supply_families=dict(families),
        monitored_packages={r:dict(part=parts[r].findtext('value'),pins=pins[r]) for r in ['P_U25','P_U103','P_U26']},
        monitor_reference=dict(resistors=monitor,contacts=contacts(mon_nodes-{GND,n19,n12},owned),
            reference_net=ref,input_nets=[v7,v8],nominal=ref_nominal,cases=reference_cases,
            reference_current_range_A=[min(ref_current),max(ref_current)],
            margin_to_1mA_output_load_A=.001-max(ref_current),
            domain='N19 in[-30,0]V, N12 in[-30,0]V; nominal -19/-12 points included. This is a chosen screen, not an accepted fault-voltage envelope.',
            input_sink_requirement_A=[-30e-9,30e-9],
            datasheet_reference_voltage_requirement_V=[.985,1.020]),
        fast_OV_output=dict(resistors=fast,contacts=contacts(fast_nodes-{GND,vin},owned),
            output_net=output,input_supply_net=vin,sense_net=sense,gate_net=gate,cases=fast_cases,
            output_current_range_A=[min(fast_current),max(fast_current)],
            outside_common_mode_case_count=sum(not c['sense_within_datasheet_common_mode_interval'] for c in fast_cases),
            output_state_correlations_checked=False,clamp_and_fault_current_bound_established=False),
        new_resistors=sorted(owned),prior_resistor_overlap=[],
        P_U26_output_receiver_contacts=nets[pins['P_U26']['4']],
        P_U25_minimum_operating_supply_V=2.3,
        margin_at_AUX_source_lower_screen_before_distribution_drop_V=2.3-2.3,
        resistor_fraction_requirement=[.97,1.03],actual_total_resistor_bounds_accepted=False,
        package_quiescent_and_dynamic_currents_included=False,
        complete_current_bound_established=False,fabrication_released=False)
    (OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(ICs=len(ic_rows),families=len(families),new_resistors=len(owned),
        reference_cases=len(reference_cases),reference_range_A=result['monitor_reference']['reference_current_range_A'],
        reference_nominal_A=ref_nominal['fixed_source_current_A'][ref],
        fast_OV_cases=len(fast_cases),fast_OV_current_range_A=result['fast_OV_output']['output_current_range_A'],
        outside_common_mode_cases=result['fast_OV_output']['outside_common_mode_case_count'])))


if __name__=='__main__':run()
