"""Select the independently reviewed local TVS revision; keep release holds."""
import json
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape


def run():
    power = STAGING/'two-board-power-input-tvs-native-01'
    previous = STAGING/'two-board-fabrication-status-33/status.json'
    cp = STAGING/'two-board-power-routing-inputs-2372-input-tvs-01/capture.json'
    reports = [previous, cp, STAGING/'two-board-power-input-tvs-filled-01/local-plane-fill.json',
        STAGING/'two-board-signal-routed-native-03/review.json', *[power/n for n in [
            'review.json', 'circuit-audit.json', 'input-tvs-routing.json', 'input-tvs-review.json',
            'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
            'plots/tvs-render.json', 'plots/visual-review.json']]]
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
    audit, native, visual = [json.loads((power/n).read_text()) for n in ['input-tvs-review.json', 'review.json', 'plots/visual-review.json']]
    assert audit['new_opens'] == native['opens'] == 2372 and audit['old_opens'] == 2374
    assert audit['connections_closed'] == 2 and audit['previous_native_connection_groups_preserved'] == 3112
    assert (audit['unchanged_complete_footprints'], audit['moved_footprints'], audit['moved_pad_instances']) == (1100, 1, 2)
    assert (audit['total_tracks'], audit['total_vias'], audit['zones']) == (2444, 262, 21)
    assert audit['geometry_errors'] == audit['parity_errors'] == audit['ERC_errors'] == 0 and audit['ERC_warnings'] == 2
    assert audit['all_new_vias_directly_contact_both_force_planes'] and audit['all_filled_pieces_connected']
    assert audit['AUX_group_and_local_copper_unchanged'] and audit['G_NT1_isolated']
    assert len(audit['previous_full_width_adjacent_reference_cases']) == 228
    assert not visual['complete_delta_audit_pending'] and len(visual['inspected_views']) == 11
    cap = json.loads(cp.read_text()); objects = {o['uuid']: o for o in cap['objects']}
    dc = [o for o in objects.values() if o['kind'] == 'PAD' and o['net'] == 'PWR_DC_IN']
    assert len(dc) == 10 and len({o['group'] for o in dc}) == 1 and 'PWR_DC_IN' not in cap['open_nets']
    ground = next(o['group'] for o in objects.values() if o.get('ref') == 'P_U101' and o.get('pin') == '8')
    ground_members = set(cap['all_groups'][ground]); zones = []
    for z in cap['zones']:
        if z['net'] != 'PWR_AGND':
            continue
        g = shape(z['polygons'])
        if any(objects[u]['layers'].get(z['layer']) and g.intersection(shape(objects[u]['layers'][z['layer']])).area > 1e-9 for u in ground_members):
            zones.append(z)
    routes = []; extra = []
    for name in ['fast-ov-routing.json', 'fast-ov-return-routing.json']:
        p = power/name; extra.append(p)
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
    status.update(source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, *extra,
        power/'README.md', REPO/'hardware/fabrication/route_nf_surface.py']},
        previous_status=str(previous.relative_to(REPO)), verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)), power_opens=2372,
        power_copper_vias=262, power_filled_zones=21, power_connections_closed_this_pass=2,
        power_added_vias_this_pass=12, power_added_zones_this_pass=2,
        power_previous_native_connection_groups_preserved=3112, power_complete_footprints_unchanged=1100,
        power_moved_footprints_this_pass=1, power_changed_pad_instances_this_pass=2,
        power_unchanged_existing_zone_fills=13, power_changed_existing_zone_fills=6,
        power_native_group_merges=[dict(net=r['net'], joined_pad=['P_D101', r['pin']], anchor=r['anchor']) for r in audit['TVS_terminal_connections']],
        power_input_TVS_connected=True, power_input_TVS_review=str((power/'input-tvs-review.json').relative_to(REPO)),
        power_input_TVS_new_vias_per_terminal=6, power_DC_IN_all_ten_pads_connected=True,
        power_input_TVS_temperature_surge_and_fuse_coordination_qualified=False,
        power_inlet_geometry_review_scope='TBP33 historical inlet construction; TBP34 checks its retained geometry, refills, references and connections with the added TVS.',
        power_all_vias_screened=262, power_minimum_all_via_drill_to_SMD_mm=audit['all_via_minimum_drill_to_SMD_mm'],
        power_previous_full_width_adjacent_ground_reference_cases_preserved=228,
        power_fast_OV_current_reference_coverage=coverage,
        power_moved_component_mechanical_screen_findings=0, power_input_TVS_Z_range_mm=audit['TVS_bottom_installed_Z_range_mm'],
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Qualify the connected input TVS across surge waveform, temperature, negative/positive overshoot and fuse/adapter fault energy',
        *[q for q in status['next_required_design_work'] if not q.startswith('Connect and qualify the input TVS')]]
    out = STAGING/'two-board-fabrication-status-34'; out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(dict(bindings=count, power_opens=2372, signal_opens=251,
        connections_closed=2, fast_OV_references=33, fabrication_released=False)))


if __name__ == '__main__':
    run()
