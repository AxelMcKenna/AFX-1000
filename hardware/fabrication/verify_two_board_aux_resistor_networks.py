"""Check all direct AUX networks with explicit series/parallel formulas."""
import itertools
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from hardware.fabrication.assess_two_board_aux_load import circuit,numeric,AUX,GND
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

OUT=STAGING/'two-board-aux-resistor-networks-01'
REF='PWR_PROTECT_REF';RUN='PWR_POWER_RUN';SW='PWR_SWITCH_SUPPLY'


def direct_formula(g,c,s):
    r={x['ref']:x['nominal_ohm']*f for x,f in zip(g['resistors'],c['resistor_factors'])}
    v=c['AUX_V'];lo=bool(s['ideal_sinks_low']);root=g['roots'][0]
    if root=='P_R113':
        return 0. if not s['switch_ON'] else v/r['P_R113'] if lo else v/(r['P_R113']+r['P_R112'])
    if root=='P_R110':
        return v/r[root] if lo else v/(r[root]+1/(1/(r['P_R204']+r['P_R205'])+1/(r['P_R224']+r['P_R225'])))
    if root=='E_R88':
        assert set(r)=={'E_R88','E_R89','E_R90','E_R91','E_R92'}
        tail=r['E_R90']+r['E_R91']
        return v/r['E_R92']+v/(r['E_R88']+1/(1/r['E_R89']+1/tail)) if lo else v/(r['E_R89']+1/(1/r['E_R88']+1/(tail+r['E_R92'])))
    if REF in g['boundary_nodes']:
        assert len(r)==3 and len(g['roots'])==1 and len(g['sink_nodes'])==1
        return v/r[root] if lo else (v-c['reference_V'])/sum(r.values())
    if g['sink_nodes']:
        assert len(g['sink_nodes'])==1 and len(r) in [1,2]
        return v/r[root] if lo else v/sum(r.values()) if GND in g['boundary_nodes'] else 0.
    assert GND in g['boundary_nodes'] and len(r) in [1,2,3]
    return v/sum(r.values())


def reciprocal_weights(g,s,which):
    # Independent bordered MNA: solve all node voltages and ideal voltage-
    # source currents together, instead of eliminating fixed nodes.
    alias={SW:RUN} if g['has_power_switch'] and s['switch_ON'] else {RUN:GND} if g['has_power_switch'] else {}
    canon=lambda n:alias.get(n,n)
    nodes=sorted({canon(n) for n in g['nodes']}|{GND})
    idx={n:i for i,n in enumerate(nodes)}
    fixed={canon(n):float(n==which) for n in [AUX,GND,REF] if canon(n) in idx}
    for n in s['ideal_sinks_low']:fixed[canon(n)]=0.
    m=np.zeros((len(nodes)+len(fixed),)*2);rhs=np.zeros(len(m))
    for r in g['resistors']:
        a,b=[idx[canon(n)] for n in r['nets']];y=1/r['nominal_ohm']
        m[a,a]+=y;m[b,b]+=y;m[a,b]-=y;m[b,a]-=y
    for k,(n,v) in enumerate(sorted(fixed.items()),len(nodes)):
        i=idx[n];m[i,k]=m[k,i]=1.;rhs[k]=v
    answer=np.linalg.solve(m,rhs)
    assert max(abs(m@answer-rhs))<1e-12
    return {n:float(answer[idx[canon(n)]]) for n in g['nodes']}


def run():
    path=OUT/'analysis.json';d=json.loads(path.read_text())
    for name,h in d['source_sha256'].items():assert sha(REPO/name)==h
    netpath=STAGING/'two-board-power-startup-remaining-native-03/netlist.xml'
    parts,nets,pins=circuit(netpath)
    roots={x['ref'] for x in nets[AUX] if x['ref'].split('_')[-1].startswith('R')}
    actual_rs={r:tuple(pins[r].values()) for r in parts if r.split('_')[-1].startswith('R')}
    boundary={AUX,GND}|{n for n,ns in nets.items() if any(x['pintype'] in ['power_in','power_out','output'] for x in ns)}
    # Traverse from each root independently; equal closures must be one group.
    closures=set()
    for root in roots:
        owned={root};visited=set();queue=list(actual_rs[root])
        while queue:
            node=queue.pop()
            if node in visited or node in boundary:continue
            visited.add(node)
            if node in [SW,RUN]:queue.append(RUN if node==SW else SW)
            for r,ends in actual_rs.items():
                if node in ends:
                    owned.add(r);queue.extend(n for n in ends if n!=node)
        closures.add(frozenset(owned))
    groups=d['networks'];allrs=[r['ref'] for g in groups for r in g['resistors']]
    assert len(groups)==len(closures)==44 and len(allrs)==len(set(allrs))==77
    assert {frozenset(r['ref'] for r in g['resistors']) for g in groups}==closures
    claimed=[r for g in groups for r in g['roots']]
    assert len(claimed)==len(set(claimed))==45 and set(claimed)==roots
    cases=responses=0;maximums=[];errors=[]
    for g in groups:
        for r in g['resistors']:
            assert r['nets']==list(actual_rs[r['ref']]) and r['nominal_ohm']==numeric(parts[r['ref']].findtext('value'))
        statekeys={(tuple(s['ideal_sinks_low']),s['switch_ON']) for s in g['states']}
        expectedkeys={(tuple(n for n,b in zip(g['sink_nodes'],flags) if b),sw) for flags in itertools.product([False,True],repeat=len(g['sink_nodes'])) for sw in ([False,True] if g['has_power_switch'] else [None])}
        assert statekeys==expectedkeys and len(statekeys)==len(g['states'])
        values=[]
        for s in g['states']:
            wanted=set(itertools.product([2.3,2.7],[1.2375,1.2625] if REF in g['boundary_nodes'] else [1.25],itertools.product([.97,1.03],repeat=len(g['resistors']))))
            got={(c['AUX_V'],c['reference_V'],tuple(c['resistor_factors'])) for c in s['cases']}
            assert wanted==got and len(got)==len(s['cases'])
            current=[]
            for c in s['cases']:
                expected=direct_formula(g,c,s);error=abs(expected-c['AUX_source_A']);errors.append(error)
                assert error<1e-14,(g['id'],s['ideal_sinks_low'],error)
                current.append(expected);cases+=1
                # Check each resistor's voltage/current relationship from
                # the stored native-node voltages, without solver imports.
                kcl=defaultdict(float);power=0.
                for r,f in zip(g['resistors'],c['resistor_factors']):
                    a,b=r['nets'];i=(c['node_voltage_V'][a]-c['node_voltage_V'][b])/(r['nominal_ohm']*f)
                    assert abs(i-c['resistor_current_A'][r['ref']])<1e-14
                    kcl[a]+=i;kcl[b]-=i;power+=i*i*r['nominal_ohm']*f
                if g['has_power_switch']:
                    a,b=(SW,RUN) if s['switch_ON'] else (RUN,GND)
                    kcl[b]+=kcl.pop(a,0.)
                fixed=set(g['boundary_nodes'])|set(s['ideal_sinks_low'])|{GND}
                assert all(abs(i)<1e-12 for n,i in kcl.items() if n not in fixed)
                assert abs(power-c['resistor_dissipation_W'])<1e-14
            assert max(abs(a-b) for a,b in zip([min(current),max(current)],s['AUX_current_range_A']))<1e-14
            values.extend(current)
            wa,wr=[reciprocal_weights(g,s,n) for n in [AUX,REF]]
            for row in s['nominal_leakage_transfer']:
                assert abs(row['AUX_source_change_per_positive_node_injection']+wa[row['node']])<1e-8
                assert abs(row['reference_source_change_per_positive_node_injection']+wr[row['node']])<1e-8
                responses+=1
        assert abs(max(values)-g['conditional_AUX_max_A'])<1e-14
        maximums.append(max(values))
    assert cases==d['corner_solutions']==1044
    assert abs(sum(maximums)-d['conservative_sum_of_network_maxima_A'])<1e-13
    switch=next(g for g in groups if g['has_power_switch'])
    off=next(s for s in switch['states'] if not s['switch_ON'])
    assert all(abs(direct_formula(switch,c,off))<1e-14 for c in off['cases'])
    # Counterexamples ensure the two material shortcuts cannot pass.
    assert abs(2.7/(3300*.97)-direct_formula(switch,off['cases'][0],off))>.0007
    coupled=next(g for g in groups if g['id']=='E_R88+E_R92')
    released=next(s for s in coupled['states'] if not s['ideal_sinks_low'])
    c=next(c for c in released['cases'] if c['AUX_V']==2.7 and all(f==.97 for f in c['resistor_factors']))
    wrong=2.7/(7500*.97)+2.7/(10000*.97)
    assert wrong-direct_formula(coupled,c,released)>.0004
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),path,netpath,REPO/'hardware/fabrication/assess_two_board_aux_load.py']},
        all_45_direct_resistors_covered_once=True,all_44_network_closures_checked=True,
        all_77_resistors_checked=True,independent_closed_form_cases=cases,
        maximum_closed_form_difference_A=max(errors),reciprocal_leakage_transfers_checked=responses,
        false_RUN_off_load_and_independent_shared_pullups_rejected=True,
        conditional_resistor_maximum_A=sum(maximums),complete_current_bound_established=False,fabrication_released=False)
    with (OUT/'verification.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))


if __name__=='__main__':run()
