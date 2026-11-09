"""Solve every direct AUX resistor branch as disjoint passive networks.

Ideal sink/switch states and zero pin leakage give a conditional resistive
screen. They are not a complete current or functional startup bound.
"""
import itertools
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from hardware.fabrication.assess_two_board_aux_load import circuit, numeric, AUX, GND
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

SOURCE = STAGING/'two-board-power-startup-remaining-native-03'
OUT = STAGING/'two-board-aux-resistor-networks-01'
REF = 'PWR_PROTECT_REF'
RUN = 'PWR_POWER_RUN'
SW = 'PWR_SWITCH_SUPPLY'


def extract(parts, nets, pins):
    resistors = {r:dict(ref=r,nets=list(pins[r].values()),nominal_ohm=numeric(p.findtext('value')),value=p.findtext('value'))
                 for r,p in parts.items() if r.split('_')[-1].startswith('R')}
    boundary = {AUX,GND}|{n for n,rows in nets.items() if any(x['pintype'] in ['power_in','power_out','output'] for x in rows)}
    adjacency = defaultdict(list)
    for r,d in resistors.items():
        a,b=d['nets'];adjacency[a].append((r,b));adjacency[b].append((r,a))
    # Reachability includes the real switch's ON connection. State solving
    # below separately uses ON (1-2) or OFF (2-3), never both.
    assert pins['I_S1']=={'3':GND,'2':RUN,'1':SW}
    assert pins['I_J3']==pins['P_J104']==pins['I_S1']
    adjacency[SW].append((None,RUN));adjacency[RUN].append((None,SW))
    roots={x['ref'] for x in nets[AUX] if x['ref'] in resistors}
    groups=[];pending=set(roots)
    while pending:
        root=min(pending);owned={root};seen=set();todo=[n for n in resistors[root]['nets'] if n not in boundary]
        while todo:
            node=todo.pop()
            if node in seen:continue
            seen.add(node)
            for r,peer in adjacency[node]:
                if r is not None:owned.add(r)
                if peer not in boundary:todo.append(peer)
        pending-=owned
        touched={n for r in owned for n in resistors[r]['nets']}
        sink_nodes={n for n in touched if any(x['pintype']=='open_collector' for x in nets[n])}
        if root=='P_R113':
            assert pins['P_Q103']['3']==RUN and pins['P_Q103']['2']==GND
            sink_nodes.add(RUN)
        contacts={n:[dict(x,value=parts[x['ref']].findtext('value')) for x in nets[n]
                     if x['ref'] not in owned and not x['ref'].split('_')[-1].startswith('C')]
                  for n in sorted(touched-boundary)}
        groups.append(dict(id='+'.join(sorted(owned&roots)),roots=sorted(owned&roots),
            resistors=[resistors[r] for r in sorted(owned)],nodes=sorted(touched),
            boundary_nodes=sorted(touched&boundary),sink_nodes=sorted(sink_nodes),
            non_resistor_contacts=contacts,has_power_switch=root=='P_R113'))
    assert len(roots)==45 and len(groups)==44
    allrefs=[r['ref'] for g in groups for r in g['resistors']]
    assert len(allrefs)==len(set(allrefs))==77
    assert {r for g in groups for r in g['roots']}==roots
    assert {n for g in groups for n in g['boundary_nodes']}=={AUX,GND,REF}
    assert next(g for g in groups if 'E_R88' in g['roots'])['roots']==['E_R88','E_R92']
    assert {r['ref'] for g in groups if g['has_power_switch'] for r in g['resistors']}=={'P_R112','P_R113'}
    return groups


def solve(group, factors, aux_v, ref_v, sinks_low, switch_on, injections=None):
    injections=injections or {}
    alias={}
    if group['has_power_switch']:
        alias[SW if switch_on else RUN]=RUN if switch_on else GND
    canon=lambda n:alias.get(n,n)
    fixed={canon(n):v for n,v in [(AUX,aux_v),(GND,0.),(REF,ref_v)]}
    for n in sinks_low:
        k=canon(n);assert k not in fixed or fixed[k]==0.;fixed[k]=0.
    edges=[(r['ref'],canon(r['nets'][0]),canon(r['nets'][1]),r['nominal_ohm']*f)
           for r,f in zip(group['resistors'],factors)]
    nodes={n for _,a,b,_ in edges for n in [a,b]}
    free=sorted(nodes-fixed.keys());index={n:i for i,n in enumerate(free)}
    m=np.zeros((len(free),len(free)));rhs=np.zeros(len(free))
    for _,a,b,res in edges:
        if a==b:continue
        for left,right in [(a,b),(b,a)]:
            if left not in index:continue
            i=index[left];m[i,i]+=1/res
            if right in index:m[i,index[right]]-=1/res
            else:rhs[i]+=fixed[right]/res
    for node,current in injections.items():
        key=canon(node)
        if key in index:rhs[index[key]]+=current
    v=dict(fixed)
    if free:
        answer=np.linalg.solve(m,rhs)
        assert max(abs(m@answer-rhs))<1e-13
        v.update(zip(free,map(float,answer)))
    port=defaultdict(float);currents={};dissipation=0.
    for ref,a,b,res in edges:
        current=(v[a]-v[b])/res;currents[ref]=current
        port[a]+=current;port[b]-=current;dissipation+=current*current*res
    for n in free:
        applied=sum(i for key,i in injections.items() if canon(key)==n)
        assert abs(port[n]-applied)<1e-12
    assert abs(sum(v[n]*i for n,i in port.items())-dissipation)<1e-12
    return dict(AUX_source_A=port[AUX],reference_source_A=port[REF],
        node_voltage_V={n:v[canon(n)] for n in group['nodes']},
        boundary_and_sink_currents_A={n:port[n] for n in nodes if n in fixed},
        resistor_current_A=currents,resistor_dissipation_W=dissipation)


def run():
    assert not OUT.exists()
    native=json.loads((SOURCE/'review.json').read_text())
    for n,h in native['artifact_sha256'].items():assert sha(SOURCE/n)==h
    parts,nets,pins=circuit(SOURCE/'netlist.xml');groups=extract(parts,nets,pins)
    results=[];total_cases=0
    for group in groups:
        # Global +/-3% is an explicit receiving screen, not initial tolerance
        # inferred as lifetime tolerance. Tighter declared bounds remain in
        # the netlist but are not needed to claim more margin here.
        states=[]
        switches=[False,True] if group['has_power_switch'] else [None]
        for levels,switch_on in itertools.product(itertools.product([False,True],repeat=len(group['sink_nodes'])),switches):
            low=[n for n,on in zip(group['sink_nodes'],levels) if on]
            cases=[]
            refs=[1.2375,1.2625] if REF in group['boundary_nodes'] else [1.25]
            for aux,reference,factors in itertools.product([2.3,2.7],refs,itertools.product([.97,1.03],repeat=len(group['resistors']))):
                solved=solve(group,factors,aux,reference,low,switch_on)
                cases.append(dict(AUX_V=aux,reference_V=reference,resistor_factors=list(factors),**solved))
            nominal=solve(group,[1.]*len(group['resistors']),2.7,1.25,low,switch_on)
            response=[]
            for node,contacts in group['non_resistor_contacts'].items():
                if not contacts:continue
                shifted=solve(group,[1.]*len(group['resistors']),2.7,1.25,low,switch_on,{node:1e-6})
                response.append(dict(node=node,
                    AUX_source_change_per_positive_node_injection=(shifted['AUX_source_A']-nominal['AUX_source_A'])/1e-6,
                    reference_source_change_per_positive_node_injection=(shifted['reference_source_A']-nominal['reference_source_A'])/1e-6))
            states.append(dict(ideal_sinks_low=low,switch_ON=switch_on,
                cases=cases,AUX_current_range_A=[min(c['AUX_source_A'] for c in cases),max(c['AUX_source_A'] for c in cases)],
                reference_current_range_A=[min(c['reference_source_A'] for c in cases),max(c['reference_source_A'] for c in cases)],
                nominal_2p7V=nominal,nominal_leakage_transfer=response))
            total_cases+=len(cases)
        results.append(dict(**group,states=states,
            conditional_AUX_max_A=max(s['AUX_current_range_A'][1] for s in states),
            conditional_AUX_min_A=min(s['AUX_current_range_A'][0] for s in states)))
    output_loads=STAGING/'two-board-aux-current-reconciliation-01/output-loads.json'
    prev=json.loads(output_loads.read_text())
    direct_refs={r['ref'] for g in groups for r in g['resistors']}
    pulldowns={r['resistor'] for r in prev['all_direct_ground_resistors_from_aux_supplied_packages']}
    assert not direct_refs&pulldowns
    sources=[Path(__file__),SOURCE/'netlist.xml',SOURCE/'review.json',output_loads,
        STAGING/'two-board-fabrication-status-50/status.json',
        REPO/'hardware/fabrication/assess_two_board_aux_load.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},
        selected_revision='TBP50',direct_AUX_resistors=45,disjoint_networks=44,
        total_resistors_in_networks=77,corner_solutions=total_cases,networks=results,
        conservative_sum_of_network_maxima_A=sum(g['conditional_AUX_max_A'] for g in results),
        scope='Direct AUX resistor-network DC draw only. All pin currents zero; fixed reference voltage; ideal OC/MOSFET sinks and ideal ON/OFF switch. State maxima need not be simultaneously functional.',
        supply_range_requirement_V=[2.3,2.7],reference_range_requirement_V=[1.2375,1.2625],
        total_resistor_fraction_requirement=[.97,1.03],actual_total_resistor_bounds_accepted=False,
        input_leakage_included=False,non_resistor_contacts_require_separate_models=True,
        RUN_switch_and_PG_or_Q103_sink_included=True,
        PG_and_Q103_individual_sink_currents_not_separated=True,
        previous_output_pulldown_resistors_disjoint=True,
        no_historical_aggregate_reserve_reduction=True,
        state_correlations_and_logic_function_verified=False,
        complete_current_bound_established=False,fabrication_released=False)
    OUT.mkdir();(OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if isinstance(v,(str,int,float,bool)) and k not in ['scope']}))


if __name__=='__main__':run()
