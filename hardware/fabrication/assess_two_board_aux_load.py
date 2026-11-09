"""Reconcile the actual AUX rail with the historical AX03 planning budget.

This produces a load inventory and sensitivity screens, not a guaranteed
whole-rail current bound. In particular, delta-ICC table points must not be
extrapolated into a full input-voltage/temperature guarantee.
"""
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.qualification.boards.aux_low_power_run.analyze import analyze

SOURCE = STAGING / 'two-board-power-aux-ground-native-02'
OUT = STAGING / 'two-board-aux-load-review-01'
OLD = REPO / 'hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work/generated/native-signal-stub-cleanup-06/netlist.xml'
AX03 = REPO / 'hardware/qualification/boards/aux_low_power_run'
AUX, GND = 'PWR_V2V5_AUX', 'PWR_AGND'


def numeric(value):
    match = re.match(r'^(\d+(?:\.\d+)?)([pnuµmkM]?)', value)
    assert match, value
    return float(match[1]) * {'': 1, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6,
                              'µ': 1e-6, 'm': 1e-3, 'k': 1e3, 'M': 1e6}[match[2]]


def circuit(path):
    tree = ET.parse(path)
    parts = {c.attrib['ref']: c for c in tree.findall('./components/comp')}
    nets, pins = {}, defaultdict(dict)
    for net in tree.findall('./nets/net'):
        name = net.attrib['name'].lstrip('/')
        nets[name] = [dict(n.attrib) for n in net.findall('node')]
        for node in nets[name]:
            ref, pin = node['ref'], node['pin']
            assert pin not in pins[ref]
            pins[ref][pin] = name
    return parts, nets, pins


def run():
    assert not OUT.exists(), 'Preserve earlier evidence'
    review = json.loads((SOURCE / 'review.json').read_text())
    for name, digest in review['artifact_sha256'].items():
        assert sha(SOURCE / name) == digest, name
    parts, nets, pins = circuit(SOURCE / 'netlist.xml')
    oldparts, oldnets, oldpins = circuit(OLD)
    terminals = []
    for node in nets[AUX]:
        ref = node['ref']
        kind = ref.split('_')[1][0]
        if node['pintype'] == 'power_out':
            category = 'source'
        elif node['pintype'] == 'power_in':
            category = 'IC_supply'
        elif node['pintype'] == 'input':
            category = 'tied_IC_input'
        else:
            category = {'C': 'capacitor', 'R': 'resistor', 'J': 'connector',
                        'D': 'diode'}[kind]
        terminals.append(dict(**node, category=category,
                              value=parts[ref].findtext('value')))
    counts = dict(Counter(x['category'] for x in terminals))
    assert len(terminals) == 229 and counts['source'] == 1
    assert [x['ref'] for x in terminals if x['category'] == 'source'] == ['P_U102']
    assert pins['P_U102']['1'] == AUX
    families = defaultdict(list)
    for row in terminals:
        if row['category'] == 'IC_supply':
            families[row['value']].append(row['ref'])
    assert all(len(refs) == len(set(refs)) for refs in families.values())
    assert families['SN74AUP3G17DCUR'] == [f'E_U{i}' for i in range(35, 42)]
    assert families['SN74LVC3G17DCUR'] == ['E_U42']
    caps, resistors, other = [], [], []
    for row in terminals:
        ref = row['ref']
        if row['category'] in ['capacitor', 'resistor']:
            assert len(pins[ref]) == 2
            peer = next(n for pin, n in pins[ref].items() if pin != row['pin'])
            item = dict(ref=ref, value=row['value'], other_net=peer,
                        nominal=numeric(row['value']),
                        datasheet=parts[ref].findtext('datasheet') or '')
            (caps if row['category'] == 'capacitor' else resistors).append(item)
        elif row['category'] in ['connector', 'diode']:
            other.append(dict(row, all_pins=pins[ref]))
    assert all(c['other_net'] == GND for c in caps)
    cap_by_role = {role: sum(c['nominal'] for c in caps if c['ref'].startswith(role + '_'))
                   for role in ['E', 'N', 'P']}
    nominal_cap = sum(cap_by_role.values())
    # Complete direct rail capacitor inventory; internal capacitance and
    # capacitors behind other nodes are deliberately outside this sum.
    cap_screens = [dict(ramp_s=t, nominal_capacitor_average_A=nominal_cap * 2.7 / t)
                   for t in [.001, .005, .01, .02, .05, .1]]
    driver_tt = []
    for ref in [f'E_U{i}' for i in range(1, 5)]:
        assert parts[ref].findtext('value') == 'SI8751AB-ISR'
        tt = pins[ref]['2']
        resistive = [n['ref'] for n in nets[tt] if n['ref'] != ref]
        assert len(resistive) == 1
        resistor = resistive[0]
        assert parts[resistor].findtext('value') == '10k 1%'
        assert set(pins[resistor].values()) == {tt, GND}
        driver_tt.append(dict(ref=ref, TT_resistor=resistor, nominal_ohm=10000,
                              initial_tolerance=.01))
    assert oldparts['U42'].findtext('value') == 'SN74AUP3G17DCUR'
    assert oldpins['U42']['3'] == oldpins['U42']['6'] == 'AGND'
    active = lambda ref, node_map, ground: [dict(pin=n['pin'], net=net)
        for net, nodes in node_map.items() for n in nodes
        if n['ref'] == ref and n['pintype'] == 'input' and net != ground]
    old_active = active('U42', oldnets, 'AGND')
    new_active = active('E_U42', nets, GND)
    assert len(old_active) == 1 and len(new_active) == 3
    legacy = analyze()
    # One old AUP active input becomes three LVC active inputs. The two newly
    # driven output loads are not added here: avoid double-counting the old NF
    # external-output reserve. That ownership needs whole-circuit reconciliation.
    sensitivity = []
    for allocation in [100e-6, 250e-6, 500e-6]:
        delta = 10e-6 - .9e-6 + len(new_active) * allocation - len(old_active) * 100e-6
        cases = [dict(name=r['name'], historical_A=r['source_total_receiving_a'],
                      changed_U42_only_A=r['source_total_receiving_a'] + 1.2 * delta,
                      margin_to_90mA_A=.09-r['source_total_receiving_a']-1.2*delta)
                 for r in legacy['pool_scenarios']]
        sensitivity.append(dict(LVC_per_active_input_allocation_A=allocation,
                                raw_delta_A=delta, scenarios=cases))
    overlap = next(r for r in legacy['pool_scenarios'] if r['name'] == 'unconstrained_overlap_NOT_closed')
    limit = ((.09-overlap['source_total_receiving_a']) / 1.2 - (10e-6-.9e-6) + 100e-6) / 3
    assert sensitivity[-1]['scenarios'][-1]['margin_to_90mA_A'] < 0
    # Existing resistor network consumes AUX even when POWER_READY is released.
    ready_refs = ['P_R110', 'P_R204', 'P_R205', 'P_R224', 'P_R225']
    ready_r = [numeric(parts[r].findtext('value')) for r in ready_refs]
    assert ready_r == [1000, 10000, 22000, 10000, 22000]
    assert pins['P_R110']['2'] == pins['P_R204']['1'] == pins['P_R224']['1']
    assert pins['P_R204']['2'] == pins['P_R205']['1'] == pins['P_U20']['7']
    assert pins['P_R224']['2'] == pins['P_R225']['1'] == pins['P_U23']['7']
    assert pins['P_R205']['2'] == pins['P_R225']['2'] == GND
    parallel = 1 / (1/(ready_r[1]+ready_r[2])+1/(ready_r[3]+ready_r[4]))
    ready_i = 2.7/(ready_r[0]+parallel)
    thermal = []
    for ambient in [40, 55, 70, 85]:
        power = (13.2-2.3)*.09 + 13.2*.0001
        thermal.append(dict(ambient_C=ambient, assumed_dissipation_W=power,
                            maximum_theta_JA_for_TJ125_C_per_W=(125-ambient)/power,
                            JEDEC_66p2_screen_TJ_C=ambient+66.2*power))
    paths = [Path(__file__), SOURCE/'netlist.xml', SOURCE/'review.json', OLD,
             AX03/'analyze.py', AX03/'sources/AX01-analysis.json', AX03/'sources/AX02-analysis.json',
             REPO/'hardware/fabrication/integrate_two_board_signal.py',
             REPO/'hardware/fabrication/assess_two_board_buck_enable_dc.py',
             REPO/'hardware/qualification/boards/aux_current_partition/sources/primary/SN74LVC3G17.pdf',
             REPO/'hardware/qualification/boards/aux_current_partition/sources/primary/Si8751.pdf',
             REPO/'hardware/electronics/power_distribution/p03/candidates/aux-front-cell/sources/tps7a16.pdf']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        source_project=str((SOURCE/'power_protection.kicad_pro').relative_to(REPO)),
        rail=AUX, terminal_count=len(terminals), categories=counts, terminals=terminals,
        IC_supply_families=dict(families), direct_capacitors=caps,
        direct_resistors=resistors, connector_and_diode_paths=other,
        direct_nominal_capacitance_F=nominal_cap, nominal_capacitance_by_role_F=cap_by_role,
        nominal_2p7V_capacitor_ramp_screens=cap_screens,
        capacitance_upper_or_effective_minimum_verified=False,
        Si8751_TT_connections=driver_tt, Si8751_four_at_exact_table_condition_A=.038,
        Si8751_table_scope='IN=VDD, TT=10k exactly; actual divided inputs, TT tolerance, switching and OFF upper current need separate bounds.',
        U42=dict(old_part='SN74AUP3G17DCUR', current_part='SN74LVC3G17DCUR',
                 old_active_inputs=old_active, current_active_inputs=new_active,
                 current_datasheet_field=parts['E_U42'].findtext('datasheet'),
                 stale_AUP_datasheet_field='aup3g17' in parts['E_U42'].findtext('datasheet'),
                 correct_datasheet='https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf'),
        historical_AX03_scenarios=legacy['pool_scenarios'], U42_only_sensitivity=sensitivity,
        U42_per_input_allocation_limit_for_old_90mA_overlap_A=limit,
        sensitivity_is_full_current_reconciliation=False,
        ready_released_nominal_zero_EN_source=dict(supply_V=2.7, references=ready_refs,
            resistor_ohm=ready_r, AUX_A=ready_i, historical_off_leak_allocation_A=2e-6),
        thermal_scenarios=thermal,
        thermal_assumptions=dict(VIN_V=13.2, AUX_V=2.3, load_A=.09, ground_current_allocation_A=.0001,
            standard_DGN_theta_JA_C_per_W=66.2, actual_board_theta_JA_verified=False),
        primary_references={
            'LVC3G17_SCES470F_table_6_5': 'https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf',
            'Si8751_table_4_1': 'https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si8751-2.pdf',
            'TPS7A16_SBVS171F_sections_6_4_6_5_10_3_10_4': 'https://www.ti.com/lit/ds/symlink/tps7a16.pdf'},
        unresolved=['Reconcile every present E/P/N IC and resistor load against circuit states; current census is not a total-current bound.',
            'Do not reuse AX03 89.357mA as current-board acceptance; changed U42 and loaded POWER_READY invalidate exact transfer.',
            '500uA LVC delta-ICC is specified at VCC3..5.5V/one input VCC-0.6V, not the actual AUX voltage range.',
            'Retain NF output-load reserve until current ownership is reconciled; do not add the two driven NF loads twice.',
            'Replace stale E_U42 AUP datasheet metadata in next native revision, preserving the selected LVC part.',
            'Resolve direct capacitor MPN/tolerance/DC-bias bounds and actual ramp/current peak.',
            'Establish thermal path at required installed ambient; added copper area does not prove thetaJA.',
            'Finalize connector loads and P_D102 clamp/backfeed state behavior.'],
        full_AUX_current_qualified=False, fabrication_released=False)
    OUT.mkdir()
    (OUT/'review.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['terminal_count','categories','direct_nominal_capacitance_F',
          'U42_per_input_allocation_limit_for_old_90mA_overlap_A','ready_released_nominal_zero_EN_source','thermal_scenarios']}, indent=2))


if __name__ == '__main__':
    run()
