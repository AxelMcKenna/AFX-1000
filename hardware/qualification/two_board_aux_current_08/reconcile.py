"""Bind existing AUX source-port models to TBP71 without aggregate double counting."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / 'sources'
RAIL = 'PWR_V2V5_AUX'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ohms(text):
    m = re.match(r'([0-9.]+)([kM]?)', text)
    assert m, text
    return float(m[1]) * {'': 1, 'k': 1e3, 'M': 1e6}[m[2]]


def analyze():
    manifest = json.loads((SOURCES / 'manifest.json').read_text())
    for row in manifest:
        assert digest(ROOT / row['snapshot']) == row['sha256'], row['snapshot']
    data = {p.stem: json.loads(p.read_text()) for p in SOURCES.glob('*.json') if p.name != 'manifest.json'}
    tree = ET.parse(SOURCES / 'TBP71-netlist.xml')
    components = {c.attrib['ref']: c.findtext('value') for c in tree.findall('./components/comp')}
    pins = {}
    nets = {}
    for n in tree.findall('./nets/net'):
        net = n.attrib['name'].removeprefix('/')
        assert net not in nets, 'Leading-slash normalization must remain one-to-one'
        nets[net] = [dict(node.attrib) for node in n.findall('node')]
        for node in nets[net]:
            pins.setdefault(node['ref'], {})[node['pin']] = net
    checks, differences = [], []

    def resistor(row, source):
        ref = row.get('ref', row.get('resistor'))
        if not ref or 'nominal_ohm' not in row:
            return
        assert ohms(components[ref]) == row['nominal_ohm'], (source, ref, 'nominal resistance changed')
        if 'nets' in row:
            assert set(pins[ref].values()) == set(row['nets']), (source, ref, 'nets changed')
        if 'pins' in row:
            assert pins[ref] == row['pins'], (source, ref, 'pins changed')
        if 'value' in row and components[ref] != row['value']:
            differences.append(dict(ref=ref, model_value=row['value'], current_value=components[ref], nominal_unchanged=True))
        checks.append(dict(source=source, ref=ref, nominal_ohm=row['nominal_ohm'], current_pins=pins[ref]))

    def walk(value, source):
        if isinstance(value, dict):
            resistor(value, source)
            for v in value.values():
                walk(v, source)
        elif isinstance(value, list):
            for v in value:
                walk(v, source)

    for name in ['current-reconciliation', 'resistor-networks', 'reference-amplifier', 'isolated-drivers', 'monitor-loads']:
        walk(data[name], name)
    inventory = data['monitor-loads']['IC_supply_inventory']
    for item in inventory:
        assert components[item['ref']] == item['part']
        assert pins[item['ref']] == item['all_pins'], item['ref']
    direct = {n['ref'] for n in nets[RAIL] if n['ref'].split('_')[-1].startswith('R')}
    resistor_models = data['resistor-networks']['networks']
    roots = [ref for row in resistor_models for ref in row['roots']]
    assert len(roots) == len(set(roots)) == 45 and set(roots) == direct
    supply_pins = {(r['ref'], r['pin']) for r in data['distribution-survey-05']['terminals'] if r['category'] == 'IC_supply'}
    assert supply_pins == {(r['ref'], r['AUX_supply_pin']) for r in inventory}
    assert len(supply_pins) == 81
    out = data['current-reconciliation']
    driven = [r for r in out['all_direct_ground_resistors_from_aux_supplied_packages'] if r['output_supply'] == RAIL and r['output_class'] == 'logic']
    assert len(driven) == 22 and len({r['resistor'] for r in driven}) == 22
    for row in driven:
        assert pins[row['driver_ref']][row['driver_pin']] == row['net']
        assert set(pins[row['resistor']].values()) == {row['net'], 'PWR_AGND'}
    assert not direct & {r['resistor'] for r in driven}
    isolated = data['isolated-drivers']
    assert set(isolated['previously_counted_resistors']) <= {r['resistor'] for r in driven}
    assert not set(isolated['new_resistors']) & (direct | {r['resistor'] for r in driven})
    for item in isolated['drivers']:
        assert pins[item['ref']] == item['pins'] and components[item['ref']] == item['part']
    ref = data['reference-amplifier']
    monitor = data['monitor-loads']
    rows = []
    for n in resistor_models:
        rows.append(dict(id='AUX:' + n['id'], source_port=RAIL, branches=n['roots'],
                         conditional_max_A=n['conditional_AUX_max_A'], owner='direct AUX network',
                         model='resistor-networks', physical_bound=False))
    for n in driven:
        rows.append(dict(id='output:' + n['resistor'], source_port=n['driver_ref'] + '.' + n['driver_pin'],
                         branches=[n['resistor']], conditional_max_A=n['conditional_high_resistor_A'],
                         owner='AUX supplied output pulldown', model='current-reconciliation', physical_bound=False))
    rows += [
        dict(id='isolated-IN', source_port='E_U29.7', branches=isolated['new_resistors'], conditional_max_A=isolated['conditional_maxima']['new_driver_input_resistors_A'], owner='Four isolated driver IN branches only', model='isolated-drivers', physical_bound=False),
        dict(id='reference-output', source_port='E_U7.OUT', branches=ref['reference_new_resistors'], conditional_max_A=ref['reference_sum_of_branch_maxima_A'], owner='Reference output port; AUX pullup ports already owned separately', model='reference-amplifier', physical_bound=False),
        dict(id='amplifier-outputs', source_port='E_U8/N_U13.outputs', branches=ref['amplifier_resistors'], conditional_max_A=ref['amplifier_conditional_output_max_sum_A'], owner='OPA output ports at nominal negative rails only', model='reference-amplifier', physical_bound=False),
        dict(id='monitor-reference', source_port='P_U25.10', branches=[r['ref'] for r in monitor['monitor_reference']['resistors']], conditional_max_A=monitor['monitor_reference']['reference_current_range_A'][1], owner='LTC2910 reference port', model='monitor-loads', physical_bound=False),
        dict(id='fast-OV-output', source_port='P_U103.1', branches=[r['ref'] for r in monitor['fast_OV_output']['resistors']], conditional_max_A=monitor['fast_OV_output']['output_current_range_A'][1], owner='Fast comparator output port, chosen voltage screen only', model='monitor-loads', physical_bound=False),
    ]
    assert len({r['id'] for r in rows}) == len(rows)
    subtotal = sum(r['conditional_max_A'] for r in rows)
    driver_table = isolated['driver_current_table']['four_TT_10kohm_max_A']
    cap = data['distribution-survey-05']['nominal_capacitance_F']
    states = []
    for name in ['startup', 'run', 'fault_latched', 'fault_overlap']:
        states.append(dict(state=name, actual_logic_state_assignment_verified=False,
                           source_port_models= [r['id'] for r in rows],
                           conditional_resistive_port_envelope_A=subtotal,
                           package_ICC_and_transition_currents_A=None,
                           switched_capacitor_current_A=None, external_and_clamp_current_A=None,
                           total_A=None, qualified=False))
    result = dict(source_sha256={str(p.relative_to(ROOT)): digest(p) for p in sorted(SOURCES.glob('*')) if p.is_file()},
                  current_source='TBP71', resistor_transfer_checks=checks, metadata_differences=differences,
                  direct_AUX_resistors_covered=sorted(direct), supply_inventory=inventory,
                  owned_source_ports=rows, conditional_resistive_port_sum_A=subtotal,
                  all_source_ports_are_conditioned_models_not_accepted_bounds=True,
                  driver_table_sensitivity=dict(four_Si8751_exact_table_condition_A=driver_table,
                      resistor_plus_driver_table_A=subtotal+driver_table,
                      residual_to_90mA_A=.09-subtotal-driver_table,
                      actual_gate_load_and_input_conditions_match=False,
                      omitted=['Other 77 package ICC/transition currents', 'Si8751 deviations from exact table conditions', 'pin/board leakage', 'capacitive switching', 'external interfaces', 'clamp/backfeed', 'distribution drop']),
                  capacitor_nominal_F=cap,
                  nominal_ramp_sensitivity=[dict(ramp_s=t, nominal_average_charge_A=cap*2.7/t,
                      plus_conditional_resistor_and_driver_A=cap*2.7/t+subtotal+driver_table)
                      for t in [.001,.005,.01,.05]],
                  state_ledger=states,
                  explicit_no_double_counting=['U42 driven N_R15/N_R16 included in 22 output pulldowns; the 12 NF pulldowns are a subset, not a second additive term, not added again',
                      'E_R104/E_R141 master pulldowns owned in output rows, excluded from added isolated IN term',
                      'Reference shared resistor networks count each source port separately, not all resistor dissipation as AUX current',
                      'READY branch and PG/Q103 sinks belong to direct AUX network models, not a second standalone READY term',
                      'No historical AX03/NF/E28 reserve is added to or replaced by this ledger',
                      'Si8751 output gate charging and TT resistor are not added independently to specified supply current'],
                  complete_current_bound_established=False, regulator_feasibility_proven=False,
                  startup_qualified=False, thermal_qualified=False, fabrication_released=False)
    result['source_sha256']['reconcile.py'] = digest(Path(__file__))
    return result


if __name__ == '__main__':
    result = analyze()
    (ROOT / 'ledger.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['conditional_resistive_port_sum_A', 'driver_table_sensitivity', 'complete_current_bound_established']}, indent=2))
