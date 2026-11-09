"""Check native bindings, ports, conservation and arithmetic of the inlet screen."""
import json
import math
import subprocess
import sys
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape


def close(x, y):
    assert math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-12), (x, y)


def run():
    out = STAGING/'two-board-inlet-resistance-02'
    report = out/'review.json'
    capfile = STAGING/'two-board-power-routing-inputs-2372-inlet-fuse-01/capture.json'
    data = json.loads(report.read_text()); cap = json.loads(capfile.read_text())
    for p in [report, capfile]:
        for name, digest in json.loads(p.read_text())['source_sha256'].items():
            assert sha(REPO/name) == digest, name
    command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/tooling', '-p', 'test_sheet_resistance.py']
    test = subprocess.run(command, cwd=REPO, capture_output=True, text=True, timeout=60)
    assert test.returncode == 0, test.stdout+test.stderr
    cases = {c['label']: c for c in data['cases']}
    assert set(cases) == {'In2.Cu', 'In3.Cu', 'In4.Cu', 'In5.Cu', 'jack-to-fuse',
                          'fuse-to-inlet-vias', 'source-vias-to-Q101', 'Q101-to-U101', 'U101-to-bulk'}
    objects = {o['uuid']: o for o in cap['objects']}
    zones = {z['uuid']: z for z in cap['zones']}
    source_nodes = []
    max_grid_change = 0.
    for label, c in cases.items():
        if label.startswith('In'):
            z = zones[c['zone_uuid']]
            assert z['net'] == c['net'] and z['layer'] == label
            close(c['meshes'][-1]['exact_copper_area_mm2'], shape(z['polygons']).area)
        starts = [objects[u] for u in c['source_objects']]
        ends = [objects[u] for u in c['sink_objects']]
        assert all(o['net'] == c['net'] and c['layer'] in o['layers'] for o in starts+ends)
        assert len({o['group'] for o in starts+ends}) == 1
        def name(o):
            return f"{o['ref']}.{o['pin']}" if o['kind'] == 'PAD' else 'via:'+','.join(map(str, o['position_mm']))
        source_names, sink_names = [{name(o) for o in rows} for rows in [starts, ends]]
        for m in [*c['meshes'], c['shifted_fine_mesh']]:
            assert set(m['ports']) == source_names | sink_names
            close(sum(m['ports'][n]['fraction'] for n in source_names), 1)
            assert abs(sum(m['ports'][n]['fraction'] for n in sink_names)-1) < 1e-7
            assert all(-1e-9 <= p['fraction'] <= 1+1e-7 for p in m['ports'].values())
            assert m['current_balance_relative_error'] < 1e-7 and m['energy_relative_error'] < 1e-7
            assert m['maximum_interior_KCL_error'] < 1e-9
            close(m['resistance_squares']*m['source_current_at_unit_voltage'], 1)
        fine = c['meshes'][-1]['resistance_squares']
        close(c['fine_refinement_relative_difference'], abs(c['meshes'][-2]['resistance_squares']/fine-1))
        close(c['fine_grid_shift_relative_difference'], abs(c['shifted_fine_mesh']['resistance_squares']/fine-1))
        max_grid_change = max(max_grid_change, c['fine_refinement_relative_difference'], c['fine_grid_shift_relative_difference'])
        source_nodes.append(dict(label=label, sources=sorted(source_names), sinks=sorted(sink_names)))
    assert data['numerical_refinement_within_2_percent'] and max_grid_change < .02
    r = {n: c['meshes'][-1]['resistance_squares'] for n, c in cases.items()}
    feed = r['In2.Cu']*r['In3.Cu']/(r['In2.Cu']+r['In3.Cu'])
    ret = r['In4.Cu']*r['In5.Cu']/(r['In4.Cu']+r['In5.Cu'])
    front = sum(v for n, v in r.items() if not n.startswith('In'))
    assert {(s['copper_thickness_um'], s['uniform_copper_temperature_C']) for s in data['scenarios']} == {(t, T) for t in [35, 70] for T in [20, 85]}
    for s in data['scenarios']:
        # 0.017241 ohm mm²/m, evaluated for a 1 mm x 1 mm square.
        sheet = (.017241*.001/(s['copper_thickness_um']/1000))*(1+.00393*(s['uniform_copper_temperature_C']-20))
        close(sheet, s['sheet_resistance_ohm'])
        close(s['paired_feed_ohm'], sheet*feed)
        close(s['paired_return_ohm'], sheet*ret)
        close(s['modeled_front_sections_ohm'], sheet*front)
        close(s['modeled_copper_subtotal_ohm'], sheet*(feed+ret+front))
        for current, name in [(4, 'at_4A'), (4.83, 'at_4_83A')]:
            close(s[name]['drop_v'], current*s['modeled_copper_subtotal_ohm'])
            close(s[name]['dissipation_w'], current*s[name]['drop_v'])
    assert not any(data[k] for k in ['full_input_loop_resistance_established', 'stack_accepted', 'thermal_qualified', 'fabrication_released'])
    assert data['results_are_estimates_not_guaranteed_bounds'] and len(data['excluded']) == 8
    paths = [Path(__file__), report, capfile, REPO/'tests/tooling/test_sheet_resistance.py']
    audit = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        analytical_and_topology_test_command=command, test_result=test.stdout+test.stderr,
        test_returncode=test.returncode, native_contacts=source_nodes,
        all_nine_sections_have_native_contact_and_net_binding=True,
        current_conservation_energy_and_scenario_arithmetic_checked=True,
        maximum_final_refinement_or_grid_shift_fraction=max_grid_change,
        numerical_screen_reviewed=True, actual_stack_or_thermal_rating_proven=False,
        complete_input_loop_or_via_current_sharing_proven=False, fabrication_released=False)
    with (out/'independent-review.json').open('x') as f:
        json.dump(audit, f, indent=2); f.write('\n')
    print(json.dumps(dict(sections=9, tests=4, maximum_mesh_change_percent=100*max_grid_change,
                         fabrication_released=False)))


if __name__ == '__main__':
    run()
