"""Current-netlist reference and amplifier output ownership, conditional DC only."""
import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from hardware.fabrication.assess_two_board_aux_load import circuit, numeric, AUX, GND
from hardware.fabrication.analyze_two_board_aux_resistor_networks import solve, REF
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

SOURCE = STAGING / 'two-board-power-startup-remaining-native-03'
PRIOR = STAGING / 'two-board-aux-resistor-networks-01'
OUT = STAGING / 'two-board-aux-reference-amplifier-01'
PRIMARY = REPO / 'hardware/qualification/boards/aux_current_partition/sources/primary'


def topology(parts, nets, pins):
    resistors = {r: dict(ref=r, nets=list(pins[r].values()),
                         nominal_ohm=numeric(p.findtext('value')), value=p.findtext('value'))
                  for r, p in parts.items() if r.split('_')[-1].startswith('R')}
    adjacent = defaultdict(list)
    for r, d in resistors.items():
        a, b = d['nets']; adjacent[a].append((r, b)); adjacent[b].append((r, a))
    boundary = {AUX, GND, REF} | {n for n, rows in nets.items()
        if any(x['pintype'] in ['power_in', 'power_out', 'output'] for x in rows)}

    def closure(roots, stops):
        owned = set(roots)
        todo = [n for r in roots for n in resistors[r]['nets'] if n not in stops]
        seen = set()
        while todo:
            node = todo.pop()
            if node in seen: continue
            seen.add(node)
            for r, peer in adjacent[node]:
                owned.add(r)
                if peer not in stops: todo.append(peer)
        return sorted(owned)

    def contacts(nodes, owned):
        return {n: [dict(x, value=parts[x['ref']].findtext('value'))
                    for x in nets[n] if x['ref'] not in owned] for n in sorted(nodes)}

    roots = {x['ref'] for x in nets[REF] if x['ref'] in resistors}
    assert len(roots) == 14
    groups = []
    for r in sorted(roots):
        owned = closure([r], boundary)
        nodes = {n for x in owned for n in resistors[x]['nets']}
        assert set(owned) & roots == {r}
        group = dict(id=r, roots=[r], resistors=[resistors[x] for x in owned],
                     nodes=sorted(nodes), boundary_nodes=sorted(nodes & boundary),
                     sink_nodes=sorted(n for n in nodes if any(
                         x['pintype'] == 'open_collector' for x in nets[n])),
                     has_power_switch=False,
                     non_resistor_contacts=contacts(nodes - boundary, owned))
        assert set(group['boundary_nodes']) <= {AUX, GND, REF}
        groups.append(group)
    owned = [r['ref'] for g in groups for r in g['resistors']]
    assert len(owned) == len(set(owned)) == 39

    amplifiers = []
    for ref in ['E_U8', 'N_U13']:
        assert parts[ref].findtext('value') == 'OPA2333AID'
        assert pins[ref]['8'] == AUX and pins[ref]['4'] == GND
        for out, inv, noninv, rail, nominal in [
                ('1', '2', '3', 'PWR_N19' + ('_SOURCE' if ref == 'E_U8' else ''), -19.),
                ('7', '6', '5', 'PWR_N12' + ('_SOURCE' if ref == 'E_U8' else ''), -12.)]:
            assert pins[ref][noninv] == GND
            output, summing = pins[ref][out], pins[ref][inv]
            # Include all output sense branches and the full input chain.
            seeds = [r for r, _ in adjacent[output]] + [r for r, _ in adjacent[summing]]
            owned = closure(seeds, boundary | {summing, rail})
            nodes = {n for r in owned for n in resistors[r]['nets']}
            assert nodes & (boundary | {rail}) == {output, rail}
            feedback = [r for r in owned if set(resistors[r]['nets']) == {output, summing}]
            assert len(feedback) == 1
            input_owned = closure([r for r, _ in adjacent[summing] if r != feedback[0]],
                                  boundary | {summing, rail})
            assert feedback[0] not in input_owned
            amplifiers.append(dict(id=ref + '.' + out, package=ref, output_pin=out,
                inverting_pin=inv, noninverting_pin=noninv, output_node=output,
                summing_node=summing, rail_node=rail, nominal_rail_V=nominal,
                feedback_resistor=feedback[0], input_resistors=input_owned,
                resistors=[resistors[r] for r in owned], nodes=sorted(nodes),
                non_resistor_contacts=contacts(nodes - {rail}, owned)))
    return groups, amplifiers


def amplifier_solve(group, factors, injections=None):
    """MNA: ideal grounded noninverting input, KCL at the inverting node.

    Output source current is an extra unknown; forcing the summing voltage to
    zero closes the feedback constraint. This assumes linear operation only.
    """
    injections = injections or {}
    rail = group['rail_node']; output = group['output_node']; summing = group['summing_node']
    free = sorted(set(group['nodes']) - {rail}); index = {n:i for i,n in enumerate(free)}
    m = np.zeros((len(free)+1, len(free)+1)); rhs = np.zeros(len(free)+1)
    resistances = {}
    for row, f in zip(group['resistors'], factors):
        a,b = row['nets']; r = row['nominal_ohm']*f; resistances[row['ref']] = r
        for left,right in [(a,b),(b,a)]:
            if left == rail: continue
            i=index[left]; m[i,i] += 1/r
            if right == rail: rhs[i] += group['nominal_rail_V']/r
            else: m[i,index[right]] -= 1/r
    m[index[output],-1] = -1.; m[-1,index[summing]] = 1.
    for node,current in injections.items(): rhs[index[node]] += current
    answer = np.linalg.solve(m,rhs)
    assert max(abs(m@answer-rhs)) < 1e-12
    v = dict(zip(free,map(float,answer[:-1]))); v[rail]=group['nominal_rail_V']
    currents = {r['ref']:(v[r['nets'][0]]-v[r['nets'][1]])/resistances[r['ref']]
                for r in group['resistors']}
    return dict(node_voltage_V=v, resistor_current_A=currents,
                output_source_A=float(answer[-1]), output_V=v[output])


def run():
    assert not (OUT/'analysis.json').exists()
    parts,nets,pins=circuit(SOURCE/'netlist.xml')
    native=json.loads((SOURCE/'review.json').read_text())
    for name,h in native['artifact_sha256'].items(): assert sha(SOURCE/name)==h
    prior=json.loads((PRIOR/'analysis.json').read_text())
    for name,h in prior['source_sha256'].items(): assert sha(REPO/name)==h
    assert parts['E_U7'].findtext('value') == 'REF35125QDBVR'
    assert all(pins['E_U7'][p]==n for p,n in
               [('1',GND),('2',GND),('3',AUX),('4',AUX),('6',REF)])
    groups, amplifiers=topology(parts,nets,pins)
    for group in groups:
        cases=[]
        for aux,reference,low_flags,factors in itertools.product(
                [2.3,2.7],[1.2375,1.2625],
                itertools.product([False,True],repeat=len(group['sink_nodes'])),
                itertools.product([.97,1.03],repeat=len(group['resistors']))):
            low=[n for n,on in zip(group['sink_nodes'],low_flags) if on]
            cases.append(dict(AUX_V=aux,reference_V=reference,ideal_sinks_low=low,
                resistor_factors=list(factors),**solve(group,factors,aux,reference,low,None)))
        group['cases']=cases
        group['reference_current_range_A']=[min(c['reference_source_A'] for c in cases),
                                            max(c['reference_source_A'] for c in cases)]
    for group in amplifiers:
        group['nominal']=amplifier_solve(group,[1.]*len(group['resistors']))
        group['cases']=[dict(resistor_factors=list(f),**amplifier_solve(group,f))
            for f in itertools.product([.97,1.03],repeat=len(group['resistors']))]
        group['output_current_range_A']=[min(c['output_source_A'] for c in group['cases']),
                                         max(c['output_source_A'] for c in group['cases'])]
        group['output_voltage_range_V']=[min(c['output_V'] for c in group['cases']),
                                         max(c['output_V'] for c in group['cases'])]
        # Positive pin current here means injection into the resistor network.
        group['nominal_pin_injection_transfers']=[]
        for node,contacts in group['non_resistor_contacts'].items():
            if not any(x['pintype']=='input' for x in contacts): continue
            shifted=amplifier_solve(group,[1.]*len(group['resistors']),{node:1e-6})
            group['nominal_pin_injection_transfers'].append(dict(node=node,
                output_A_change_per_A=(shifted['output_source_A']-group['nominal']['output_source_A'])/1e-6,
                output_V_change_per_A=(shifted['output_V']-group['nominal']['output_V'])/1e-6))
    priorrefs={r['ref'] for g in prior['networks'] for r in g['resistors']}
    refrefs={r['ref'] for g in groups for r in g['resistors']}
    amprefs=[r['ref'] for g in amplifiers for r in g['resistors']]
    shared=refrefs & priorrefs
    assert len(shared)==21 and len(refrefs-priorrefs)==18
    assert len(amprefs)==len(set(amprefs))==17 and not set(amprefs)&(priorrefs|refrefs)
    sources=[Path(__file__),SOURCE/'netlist.xml',SOURCE/'review.json',PRIOR/'analysis.json',
        PRIOR/'verification.json',REPO/'hardware/fabrication/assess_two_board_aux_load.py',
        REPO/'hardware/fabrication/analyze_two_board_aux_resistor_networks.py',
        PRIMARY/'REF35.pdf',PRIMARY/'OPA333.pdf']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},
        selected_revision='TBP50',reference_networks=groups,amplifier_channels=amplifiers,
        reference_direct_contacts=nets[REF],reference_shared_with_prior_AUX_resistors=sorted(shared),
        reference_new_resistors=sorted(refrefs-priorrefs),amplifier_resistors=sorted(amprefs),
        reference_sum_of_branch_minima_A=sum(g['reference_current_range_A'][0] for g in groups),
        reference_sum_of_branch_maxima_A=sum(g['reference_current_range_A'][1] for g in groups),
        amplifier_nominal_output_sum_A=sum(g['nominal']['output_source_A'] for g in amplifiers),
        amplifier_conditional_output_max_sum_A=sum(g['output_current_range_A'][1] for g in amplifiers),
        scope='Steady-state, ideal linear amplifiers, zero input/connector leakage, ideal released/zero-volt comparator outputs, fixed reference. Amplifier rail inputs are nominal -19/-12 V only.',
        resistor_fraction_requirement=[.97,1.03],actual_total_resistor_bounds_accepted=False,
        reference_voltage_requirement_V=[1.2375,1.2625],reference_accuracy_qualified=False,
        no_shared_AUX_pullup_current_added_again=True,
        package_currents_and_pin_leakage_included=False,
        input_and_output_dynamic_capacitor_currents_included=False,
        negative_rail_extrema_and_startup_fault_states_verified=False,
        complete_current_bound_established=False,fabrication_released=False)
    (OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if isinstance(v,(str,float,bool))}))


if __name__=='__main__': run()
