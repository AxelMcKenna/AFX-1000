"""Verify additive routing and every parent pad-group connection independently."""
import argparse
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha

ROOT = Path(__file__).resolve().parent


def check(parent, source, construction):
    before_dir, after_dir, recipe_dir = [ROOT/'staging'/n for n in (parent, source, construction)]
    paths = [Path(__file__)]
    boards = []
    netlists = []
    for directory in (before_dir, after_dir):
        pcb = directory/'digital_core.kicad_pcb'
        review_path = directory/'review.json'
        review = json.loads(review_path.read_text())
        assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'), review)
        assert review['status']['counts']['violations'] == review['status']['counts']['schematic_parity'] == review['status']['counts']['erc'] == 0
        connectivity_path = directory/'stage-connectivity-review.json'
        connectivity = json.loads(connectivity_path.read_text())
        assert all(sha(Path(p)) == h for p, h in connectivity['source_sha256'].items())
        assert connectivity['preserved_power_ground_pads'] == 201
        assert connectivity['preserved_local_connections'] == 39 and connectivity['preserved_thermal_connections'] == 33
        boards.append(read_sexpr(pcb.read_text()))
        netlists.append(connectivity)
        paths += [pcb, review_path, connectivity_path]
    recipe_path = recipe_dir/'construction.json'
    recipe = json.loads(recipe_path.read_text())
    assert all(sha(Path(p)) == h for p, h in recipe['source_sha256'].items())
    candidate = recipe_dir/'digital_core.kicad_pcb'
    assert sha(candidate) == recipe['candidate_PCB_sha256']
    candidate_tree = read_sexpr(candidate.read_text())
    native_delta = geometry_delta(candidate_tree, boards[1])
    assert native_delta['other_root_geometry_exact']
    for tag in ('footprint', 'segment', 'via', 'zone'):
        assert native_delta[tag] == dict(added=[], removed=[], changed=[])
    delta = geometry_delta(*boards)
    assert delta['other_root_geometry_exact']
    for tag in ('footprint', 'zone'):
        assert delta[tag] == dict(added=[], removed=[], changed=[])
    for tag in ('segment', 'via'):
        assert not delta[tag]['removed'] and not delta[tag]['changed']
    assert len(delta['segment']['added']) == recipe['added_segments']
    assert len(delta['via']['added']) == recipe['added_vias']
    additions = {tag: [n for n in children(boards[1], tag) if first(n, 'uuid')[1] in delta[tag]['added']]
                 for tag in ('segment', 'via')}
    routed_nets = {r['net'] for r in recipe['routes']}
    assert {first(n, 'net')[1] for ns in additions.values() for n in ns} == routed_nets
    for n in additions['segment']:
        assert float(first(n, 'width')[1]) == .2
        assert first(n, 'layer')[1] in ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    for n in additions['via']:
        assert float(first(n, 'size')[1]) == .6 and float(first(n, 'drill')[1]) == .3
    old_nets, new_nets = [{r['net']: r for r in c['nets']} for c in netlists]
    assert old_nets.keys() == new_nets.keys()
    changed = []
    for net, old in old_nets.items():
        new = new_nets[net]
        old_groups = [set(map(tuple, g)) for g in old['pad_groups']]
        new_groups = [set(map(tuple, g)) for g in new['pad_groups']]
        assert set.union(*old_groups) == set.union(*new_groups)
        assert all(any(group <= merged for merged in new_groups) for group in old_groups), net
        if len(new_groups) < len(old_groups):
            changed.append(dict(net=net, before_groups=len(old_groups), after_groups=len(new_groups),
                                all_pads_connected=new['all_pads_connected'],
                                total_planar_copper_mm=new['planar_copper_length_mm'], total_vias=new['via_count']))
    assert {r['net'] for r in changed} == routed_nets
    joins = netlists[0]['uncapped_open_connections']-netlists[1]['uncapped_open_connections']
    assert joins == len(recipe['routes']) == sum(r['before_groups']-r['after_groups'] for r in changed)
    paths += [recipe_path, candidate]
    return dict(source_sha256={str(p): sha(p) for p in paths}, geometry_delta=delta,
                before_opens=netlists[0]['uncapped_open_connections'], after_opens=netlists[1]['uncapped_open_connections'],
                joins=joins, improved_nets=changed, regressed_pad_groups=[],
                exact_parent_copper_footprints_outline_mounts_and_zone_definitions_retained=True,
                added_tracks=len(additions['segment']), added_vias=len(additions['via']),
                electrical_performance_and_fabrication_qualified=False, fabrication_released=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('parent', 'source', 'construction'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    assert all(n and all(c.isalnum() or c in '-_' for c in n) for n in vars(args).values())
    result = check(args.parent, args.source, args.construction)
    with (ROOT/'staging'/args.source/'additive-route-review.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print('Verified', result['joins'], 'joins with every parent pad group and copper object retained')
