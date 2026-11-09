"""Select independently reviewed regulator distribution; retain release holds."""
import json
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape


def run():
    power = STAGING/'two-board-power-regulator-distribution-native-04'
    previous = STAGING/'two-board-fabrication-status-35/status.json'
    cp = STAGING/'two-board-power-routing-inputs-2369-regulator-distribution-04/capture.json'
    reports = [previous, cp, STAGING/'two-board-power-regulator-distribution-filled-04/local-plane-fill.json',
               STAGING/'two-board-signal-routed-native-03/review.json', *[power/n for n in [
                   'review.json', 'regulator-distribution-routing.json', 'regulator-distribution-review.json',
                   'regulator-reference-review.json', 'rejected-source-net-status.json',
                   'plots/native-plots.json', 'plots/preview-render.json', 'plots/distribution-left-render.json',
                   'plots/distribution-right-render.json', 'plots/visual-review.json']]]
    count = 0
    for p in reports:
        d = json.loads(p.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, h in d.get(field, {}).items():
                q = Path(name)
                if not q.is_absolute():
                    q = (REPO if name.startswith(('hardware/', 'tests/')) else p.parent)/q
                assert sha(q) == h, (p, name)
                count += 1
    audit, reference = [json.loads((power/n).read_text()) for n in ['regulator-distribution-review.json', 'regulator-reference-review.json']]
    assert audit['new_opens'] == 2369 and audit['all_prior_groups_preserved'] == 3110
    assert audit['all_footprints_unchanged'] == 1101 and audit['previous_full_width_adjacent_ground_cases_preserved'] == 228
    assert reference['uncovered_total_mm2'] < .05 and len(reference['uncovered_components']) == 8
    cap = json.loads(cp.read_text()); objects = {o['uuid']: o for o in cap['objects']}
    zones = [z for z in cap['zones'] if z['net'] == 'PWR_AGND']
    route_sources = [STAGING/'two-board-power-input-tvs-native-01'/n for n in ['fast-ov-routing.json', 'fast-ov-return-routing.json']]
    routes = []
    for p in route_sources:
        routes.extend(r for r in json.loads(p.read_text())['routes'] if all(u in objects for u in r['segment_uuids']))
    assert len(routes) == 33
    coverage = []; layers = cap['copper_layers']
    for r in routes:
        g = LineString(r['path_mm']).buffer(r['width_mm']/2)
        for o in objects.values():
            if o['kind'] == 'PCB_VIA' and o['net'] == r['net'] and o['net'] != 'PWR_AGND':
                g = g.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
        i = layers.index(r['layer']); adjacent = [layers[j] for j in [i-1, i+1] if 0 <= j < len(layers)]
        areas = {l: g.difference(unary_union([shape(z['polygons']) for z in zones if z['layer'] == l]).buffer(.0015)).area for l in adjacent}
        assert min(areas.values()) < 1e-6, (r['label'], areas)
        coverage.append(dict(label=r['label'], adjacent_reference_uncovered_mm2=areas))
    status = json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, *route_sources,
                   power/'README.md', REPO/'hardware/fabrication/route_nf_surface.py']},
        previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP35 circuit and fuse evidence; current copper and connectivity are described by TBP36 direct reports.',
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)), power_opens=2369,
        power_filled_zones=24, power_connections_closed_this_pass=3, power_added_zones_this_pass=3,
        power_complete_footprints_unchanged=1101, power_changed_component_values_this_pass=0,
        power_unchanged_existing_zone_fills=17, power_changed_existing_zone_fills=4,
        power_native_group_merges=audit['native_group_merges'],
        power_U20_and_U23_feed_connected=True, power_U23_force_return_connected=True,
        power_regulator_distribution_review=str((power/'regulator-distribution-review.json').relative_to(REPO)),
        power_regulator_distribution_current_thermal_noise_qualified=False,
        power_new_feed_reference_uncovered_mm2=reference['uncovered_total_mm2'],
        power_new_feed_reference_covered_fraction=reference['covered_fraction'],
        power_new_feed_reference_full_area_coverage=False,
        power_fast_OV_current_reference_coverage=coverage,
        power_visual_evidence_scope='Current TBP36 full front/back/inner overview and six distribution detail views inspected.',
        power_inlet_resistance_model_scope='TBP35 historical nine-section conditional model; new distribution and native In2 refill require a revised coupled-path model.',
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Qualify newly connected U20/U23 feed and return branches against actual stack, effective capacitance, current sharing, startup, noise and thermal limits',
        'Complete remaining regulator output, module input and force/quiet return distribution',
        *[s for s in status['next_required_design_work'] if not s.startswith('Connect wider U23 source feed')]]
    out = STAGING/'two-board-fabrication-status-36'; out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(dict(bindings=count, power_opens=2369, signal_opens=251, closed_connections=3,
                         fast_OV_references=len(coverage), fabrication_released=False)))


if __name__ == '__main__':
    run()
