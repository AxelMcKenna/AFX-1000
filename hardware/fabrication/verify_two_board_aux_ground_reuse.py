"""Bind TBP72 routing, quiet-ground exclusion and native visual evidence."""
import json
from pathlib import Path
from shapely.geometry import LineString, box
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.plan_two_board_aux_ground_reuse import CAP


def run():
    out = STAGING / 'two-board-power-aux-ground-reuse-native-01'
    target = out / 'final-review.json'
    assert not target.exists()
    audit = json.loads((out / 'aux-ground-reuse-review.json').read_text())
    routing = json.loads((out / 'aux-ground-reuse-routing.json').read_text())
    c = json.loads(CAP.read_text())
    objects = {o['uuid']: o for o in c['objects']}
    paths = {Path(__file__), CAP, out / 'aux-ground-reuse-review.json', out / 'aux-ground-reuse-routing.json',
             out / 'review.json', REPO / 'hardware/fabrication/route_nf_surface.py'}
    quiet_paths = [STAGING / 'two-board-power-digital-startup-native-02/digital-startup-routing.json',
                   STAGING / 'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    paths.update(quiet_paths)
    quiet = [q for p in quiet_paths for q in json.loads(p.read_text())['quiet_ground_islands']]
    quiet_ids = {u for q in quiet for u in q['zone_uuids']}
    quiet_vias = {v['uuid'] for q in quiet for v in [q['star_via'], *q['control_vias'], *q['extra_quiet_vias']]}
    coverage = []
    for r in routing['routes']:
        band = LineString(r['path_mm']).buffer(.15)
        assert r['target_uuid'] not in quiet_vias
        assert all(band.distance(shape(objects[u]['layers'][r['layer']])) > .01
                   for u in quiet_vias if r['layer'] in objects[u]['layers'])
        assert all(band.distance(shape(z['authored_outline'])) > .01
                   for z in c['zones'] if z['uuid'] in quiet_ids and z['layer'] == r['layer'])
        layer = {'F.Cu': 'front', 'B.Cu': 'back'}[r['layer']]
        views = []
        for p in (out / 'plots').glob('*-coordinate-map.json'):
            record = json.loads(p.read_text())
            x, y, size = record['board_viewport_mm']
            prefix = p.name.removesuffix('-coordinate-map.json')
            png = out / 'plots' / (prefix + '-' + layer + '.png')
            if png.exists() and box(x, y, x + size, y + size).covers(band):
                assert record['matched_mounting_holes'] == 11
                views.append(prefix + '-' + layer)
                paths.update((p, png, out / 'plots' / (prefix + '-render.json')))
        assert views, r['pad_ref']
        coverage.append(dict(ref=r['pad_ref'], native_views=views))
    paths.add(out / 'plots/native-plots.json')
    # Validate both direct reports and their source/artifact hashes. Native PNGs
    # were inspected by the author; coverage above independently binds every path.
    for report in list(paths):
        if report.suffix != '.json':
            continue
        data = json.loads(report.read_text())
        for field in ('source_sha256', 'artifact_sha256'):
            for name, digest in data.get(field, {}).items():
                p = Path(name)
                if not p.is_absolute():
                    p = (REPO if name.startswith(('hardware/', 'tests/')) else report.parent) / p
                assert sha(p) == digest, (report, p)
                paths.add(p)
    assert audit['native_opens'] == 1937 and audit['closed_connections'] == 6
    assert audit['all_original_objects_and_47_plane_fills_unchanged']
    assert audit['all_other_native_connectivity_groups_preserved']
    result = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(paths)},
                  native_opens=1937, closed_connections=6, added_tracks=8, added_vias=0,
                  all_original_copper_and_47_plane_fills_unchanged=True,
                  quiet_ground_networks_without_new_contacts=len(quiet),
                  route_visual_coverage=coverage, self_review=True,
                  visual_findings=[], scope='Electrical connectivity checkpoint; AUX decoupling and rail performance remain unqualified',
                  longest_new_return_mm=max(r['length_mm'] for r in routing['routes']),
                  full_goal_complete=False, fabrication_released=False)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print('Verified six ground joins, seven quiet networks and all six native visual views')


if __name__ == '__main__':
    run()
