"""Current native connectivity backlog, reconciled without changing copper.

Counts are native pad-cluster gaps, not estimated routing effort. This inventory
does not replace clearance, return-path, circuit, manufacturing or fit review.
"""
import json
from collections import defaultdict
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

CAPTURE = STAGING / 'two-board-power-routing-inputs-western-logic-returns-02/capture.json'
POWER = STAGING / 'two-board-power-western-logic-returns-native-02'
OUT = STAGING / 'two-board-completion-inventory-01'


def run():
    assert not OUT.exists(), 'Preserve earlier evidence'
    capture = json.loads(CAPTURE.read_text())
    for name, digest in capture['source_sha256'].items():
        path = Path(name)
        assert sha(path if path.is_absolute() else REPO / path) == digest, name
    review = json.loads((POWER / 'review.json').read_text())
    for name, digest in review['artifact_sha256'].items():
        assert sha(POWER / name) == digest, name
    objects = {o['uuid']: o for o in capture['objects']}
    nets = defaultdict(list)
    for group, members in capture['all_groups'].items():
        names = {objects[u]['net'] for u in members}
        assert len(names) == 1
        pads = sorted((dict(ref=objects[u]['ref'], pin=objects[u]['pin'],
                            position_mm=objects[u]['position_mm'])
                       for u in members if objects[u]['kind'] == 'PAD'),
                      key=lambda p: (p['ref'], p['pin']))
        assert pads
        nets[next(iter(names))].append(dict(group=group, pads=pads))
    rows = []
    for name, groups in nets.items():
        if len(groups) <= 1:
            continue
        roles = sorted({p['ref'].split('_')[0] for g in groups for p in g['pads']})
        rows.append(dict(net=name, missing_joins=len(groups)-1, roles=roles,
                         pad_count=sum(len(g['pads']) for g in groups), groups=groups))
    rows.sort(key=lambda r: (-r['missing_joins'], r['net']))
    total = sum(r['missing_joins'] for r in rows)
    assert total == capture['native_uncapped_opens'] == review['opens'] == 2042
    inputs = {
        'aux': STAGING / 'two-board-aux-distribution-survey-03/inventory.json',
        'startup': STAGING / 'two-board-startup-connectivity-survey-11/inventory.json',
        'cells': STAGING / 'two-board-startup-cell-survey-05/inventory.json',
        'logic_grounds': STAGING / 'two-board-logic-ground-access-survey-04/survey.json',
    }
    reports = {k: json.loads(p.read_text()) for k, p in inputs.items()}
    for key, data in reports.items():
        for name, digest in data['source_sha256'].items():
            path = Path(name)
            assert sha(path if path.is_absolute() else REPO / path) == digest, (key, name)
    priority = [
        {'task': 'Main ground distribution', 'native_gaps': next(r['missing_joins'] for r in rows if r['net'] == 'PWR_AGND'),
         'requirements': ['Preserve seven intentional quiet-ground networks and their single stars',
                          'Connect four remaining monitor-logic grounds',
                          'Preserve retained control references and repair connector-end gaps']},
        {'task': 'AUX source distribution', 'native_gaps': next(r['missing_joins'] for r in rows if r['net'] == 'PWR_V2V5_AUX'),
         'IC_supply_pins_without_source': reports['aux']['unconnected_IC_supply_pins'],
         'requirements': ['Complete load/startup/thermal budget', 'Route supply with verified returns']},
        {'task': 'Surveyed startup control routing',
         'native_gaps': reports['startup']['selected_missing_joins'],
         'open_nets': reports['startup']['open_selected_net_count'],
         'requirements': ['Review full startup/fault behavior; local bypass completion is insufficient']},
    ]
    sources = [Path(__file__), CAPTURE, POWER / 'review.json', *inputs.values()]
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  power_revision='TBP66', power_native_opens=total,
                  power_open_net_count=len(rows), priority_work=priority, nets=rows,
                  count_scope='Each net contributes number of native pad clusters minus one. Priority categories overlap and must not be summed.',
                  signal_board='two-board-signal-routed-native-03',
                  signal_work=['Approved ESS package/land/stencil inputs', '251 recorded open connections',
                               'Audio/digital shared-ground and bridge routing', 'Final inter-board interface'],
                  shared_release_work=['Accepted stackup and exact BOM', 'Complete installed CAD/harness/cooling fit',
                                       'Inspected manufacturing outputs', 'Isolated first-article bring-up plan'],
                  source_distribution_complete=False, fabrication_released=False)
    OUT.mkdir()
    (OUT / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['power_native_opens', 'power_open_net_count', 'priority_work']}))


if __name__ == '__main__':
    run()
