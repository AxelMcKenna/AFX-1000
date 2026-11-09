"""Inventory native startup connection groups without treating proximity as routing."""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in n) for n in [args.capture, args.output])
    source = STAGING / args.capture / 'capture.json'
    output = STAGING / args.output
    assert not output.exists()
    capture = json.loads(source.read_text())
    for name, digest in capture['source_sha256'].items():
        path = Path(name)
        assert sha(path if path.is_absolute() else REPO / path) == digest
    objects = {o['uuid']: o for o in capture['objects']}
    by_net = defaultdict(list)
    for gid, members in capture['all_groups'].items():
        nets = {objects[u]['net'] for u in members}
        assert len(nets) == 1
        net = next(iter(nets))
        if 'E28_' not in net and 'ANA_PG' not in net and 'DIG_PG' not in net and net != 'PWR_ALL_RAILS_ALLOW':
            continue
        pads = sorted([dict(uuid=u, ref=objects[u]['ref'], pin=objects[u]['pin'],
                            xy_mm=objects[u]['position_mm'], layers=list(objects[u]['layers']))
                       for u in members if objects[u]['kind'] == 'PAD'],
                      key=lambda p: (p['ref'], p['pin'], p['uuid']))
        assert pads
        by_net[net].append(dict(native_group=gid, object_count=len(members), pads=pads))
    records = []
    for net, groups in sorted(by_net.items()):
        pairs = []
        for i, left in enumerate(groups):
            for right in groups[i+1:]:
                distance, p, q = min(((math.dist(p['xy_mm'], q['xy_mm']), p, q)
                                     for p in left['pads'] for q in right['pads']), key=lambda x: x[0])
                pairs.append(dict(distance_mm=distance, left_group=left['native_group'],
                                  right_group=right['native_group'], left_pad=p, right_pad=q))
        records.append(dict(net=net, groups=groups, missing_joins=len(groups)-1,
                            nearest_pad_pairs=sorted(pairs, key=lambda p: p['distance_mm'])))
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), source]},
                  selection='All native nets containing E28_, ANA_PG or DIG_PG, plus PWR_ALL_RAILS_ALLOW',
                  native_board_opens=capture['native_uncapped_opens'],
                  selected_net_count=len(records), open_selected_net_count=sum(r['missing_joins'] > 0 for r in records),
                  selected_missing_joins=sum(r['missing_joins'] for r in records), nets=records,
                  scope='Native pad connectivity only. Nearest-pad distances are survey hints, not clearance, ownership, reference, timing or load validation.',
                  startup_functionally_verified=False, fabrication_released=False)
    output.mkdir()
    (output / 'inventory.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['nets', 'source_sha256']}))


if __name__ == '__main__':
    run()
