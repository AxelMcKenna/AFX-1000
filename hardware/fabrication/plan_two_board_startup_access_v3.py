"""Remove the obsolete ALL_RAILS_ALLOW via exposed by native DRC."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    source = STAGING/'two-board-startup-access-plan-02/plan.json'
    output = STAGING/'two-board-startup-access-plan-03'
    assert not output.exists()
    p = json.loads(source.read_text())
    for name, h in p['source_sha256'].items():
        assert sha(REPO/name) == h, name
    via = '13b2d201-c4b9-529e-a4cc-77dfc19a3ebc'
    assert via not in p['retired_objects']
    p['retired_objects'].append(via)
    transitions = p['reference_transitions']
    removed = [t for t in transitions if t['net']=='PWR_ALL_RAILS_ALLOW' and t['position_mm']==[122.4,151.0]]
    assert len(removed)==1 and removed[0]['same_reference_plane']
    p['reference_transitions'] = [t for t in transitions if t not in removed]
    p['obsolete_vias_removed'] = [dict(uuid=via, net='PWR_ALL_RAILS_ALLOW', position_mm=[122.4,151.0], reason='Both incident traces now use In3.Cu; no layer transition remains.')]
    for f in [Path(__file__),source]:
        p['source_sha256'][str(f.relative_to(REPO))] = sha(f)
    output.mkdir()
    (output/'plan.json').write_text(json.dumps(p,indent=2)+'\n')
    print('Removed one obsolete single-layer via from the plan')


if __name__=='__main__':
    run()
