"""Locate uncovered pad centers in remaining selected NF logic networks."""
import argparse
import json
from pathlib import Path
from shapely.geometry import Point
from shapely.prepared import prep
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields


def run():
    parser = argparse.ArgumentParser()
    for name in ['capture', 'selection', 'output']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in n)
               for n in [args.capture, args.selection, args.output])
    source = STAGING / args.capture / 'capture.json'
    selection = STAGING / args.selection / 'plan.json'
    out = STAGING / args.output
    assert not out.exists()
    cap = json.loads(source.read_text())
    plan = json.loads(selection.read_text())
    for data in [cap, plan]:
        for name, digest in data['source_sha256'].items():
            path = Path(name)
            assert sha(path if path.is_absolute() else REPO / path) == digest, name
    pure = {n for n, nodes in plan['selected_nets'].items()
            if {p.get('pintype') for p in nodes} == {'input', 'output'}
            and all(p['ref'].startswith('N_') for p in nodes)}
    objects = {o['uuid']: o for o in cap['objects']}
    groups = {}
    for gid, members in cap['all_groups'].items():
        net = objects[members[0]]['net']
        if net in pure:
            groups.setdefault(net, []).append(gid)
    open_nets = {n: gs for n, gs in groups.items() if len(gs) > 1}
    fields, excluded = anchored_fields(cap)
    main = next(o['group'] for o in cap['objects']
                if o.get('ref') == 'P_C103' and o.get('pin') == '2')
    field = prep(fields['In1.Cu', main].buffer(-.1))
    pads = []
    for o in cap['objects']:
        if o['kind'] != 'PAD' or o['net'] not in open_nets:
            continue
        pads.append(dict(uuid=o['uuid'], ref=o['ref'], pin=o['pin'], net=o['net'],
                         native_group=o['group'], xy_mm=o['position_mm'],
                         covered_at_center=field.covers(Point(o['position_mm']))))
    sources = [Path(__file__), source, selection,
               REPO / 'hardware/fabrication/plan_two_board_startup_controls.py']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  native_board_opens=cap['native_uncapped_opens'],
                  selection='Previously selected nets whose every pin is an N_ logic input/output',
                  open_selected_nets=len(open_nets),
                  missing_selected_joins=sum(len(gs)-1 for gs in open_nets.values()),
                  reference_layer='In1.Cu', tested_trace_radius_mm=.1,
                  selected_open_pads=len(pads), uncovered_pad_centers=sum(not p['covered_at_center'] for p in pads),
                  pads=pads, excluded_unanchored_fragments=excluded,
                  scope='Pad-center coverage screen only; no full escape, routing, timing or electrical qualification.',
                  fabrication_released=False)
    out.mkdir()
    (out / 'survey.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['native_board_opens', 'open_selected_nets',
                                         'missing_selected_joins', 'selected_open_pads', 'uncovered_pad_centers']}))


if __name__ == '__main__':
    run()
