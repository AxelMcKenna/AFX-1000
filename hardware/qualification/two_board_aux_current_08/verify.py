"""Independent ledger membership and failure-injection checks."""
import copy
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def validate(d):
    for name, sha in d['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
    tree = ET.parse(ROOT / 'sources/TBP71-netlist.xml')
    nodes = next(n for n in tree.findall('./nets/net') if n.attrib['name'] == 'PWR_V2V5_AUX').findall('node')
    resistors = {n.attrib['ref'] for n in nodes if n.attrib['ref'].split('_')[-1].startswith('R')}
    rows = d['owned_source_ports']
    roots = [r for row in rows if row['source_port'] == 'PWR_V2V5_AUX' for r in row['branches']]
    assert len(roots) == len(set(roots)) and set(roots) == resistors
    ports = [(row['source_port'], ref) for row in rows for ref in row['branches']]
    assert len(ports) == len(set(ports)), 'A source port and branch cannot be charged twice'
    assert len({r['id'] for r in rows}) == len(rows)
    assert math.isclose(sum(row['conditional_max_A'] for row in rows), d['conditional_resistive_port_sum_A'], rel_tol=1e-12)
    for key in ['complete_current_bound_established', 'regulator_feasibility_proven', 'startup_qualified', 'thermal_qualified', 'fabrication_released']:
        assert d[key] is False, key
    assert all(s['total_A'] is None and s['qualified'] is False for s in d['state_ledger'])
    assert len(d['supply_inventory']) == 81


def main():
    data = json.loads((ROOT / 'ledger.json').read_text())
    validate(data)
    mutations = []
    d = copy.deepcopy(data); row = next(r for r in d['owned_source_ports'] if r['id'] == 'output:N_R15')
    duplicate = dict(row, id='extra-NF-reserve'); d['owned_source_ports'].append(duplicate)
    d['conditional_resistive_port_sum_A'] += duplicate['conditional_max_A']; mutations.append(('duplicate_NF_output', d))
    d = copy.deepcopy(data); removed = d['owned_source_ports'].pop(0); d['conditional_resistive_port_sum_A'] -= removed['conditional_max_A']; mutations.append(('missing_AUX_branch', d))
    d = copy.deepcopy(data); d['conditional_resistive_port_sum_A'] += .001; mutations.append(('incorrect_sum', d))
    d = copy.deepcopy(data); d['regulator_feasibility_proven'] = True; mutations.append(('unsupported_acceptance', d))
    rejected = []
    for name, item in mutations:
        try:
            validate(item)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError(name + ' was not rejected')
    result = dict(ledger_sha256=hashlib.sha256((ROOT / 'ledger.json').read_bytes()).hexdigest(),
                  verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  membership_and_hash_checks_passed=True, injected_errors_rejected=rejected,
                  full_current_or_physical_qualification=False)
    (ROOT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Verified source-port membership, arithmetic and four rejected defects')


if __name__ == '__main__':
    main()
