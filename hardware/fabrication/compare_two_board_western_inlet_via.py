"""Compare actual DC-input sheets before/after the local E_U37 ground via.

The native copper delta must be exactly one bounded antipad in each feed
plane. The resistive-sheet comparison retains identical ideal contact ports;
it does not establish an installed current rating, temperature or full loop.
"""
import json
from pathlib import Path
from shapely.geometry import Point
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.sheet_resistance_with_probes import solve_sheet

BEFORE = STAGING / 'two-board-power-routing-inputs-logic-ground-access-01/capture.json'
AFTER = STAGING / 'two-board-power-routing-inputs-western-logic-returns-01/capture.json'
CANDIDATE = STAGING / 'two-board-power-western-logic-returns-native-01'
OUT = STAGING / 'two-board-western-inlet-via-comparison-01'


def feed_cases(cap):
    # Retain the historical inlet/source contact banks, but select only the
    # two feed sheets. New ground-zone subdivisions are irrelevant here.
    objects=cap['objects']
    def via(xy):
        matches=[o for o in objects if o['kind']=='PCB_VIA' and o['position_mm']==xy]
        assert len(matches)==1
        return matches[0]
    starts=[via([x,y]) for x in [280.5,281.2,281.9,282.6] for y in [20.8,21.5,22.2]]
    ends=[via(xy) for xy in [[189.95,112.75],[191.5,112.8],[192.1,112.8],[189.5,114.8],[193.9,114.3]]]
    assert all(o['net']=='PWR_DC_IN' for o in starts+ends)
    assert len({o['group'] for o in starts+ends})==1
    rows=[]
    for layer in ['In2.Cu','In3.Cu']:
        zone,=[z for z in cap['zones'] if z['net']=='PWR_DC_IN' and z['layer']==layer]
        copper=shape(zone['polygons'])
        def ports(items):
            result={}
            for o in items:
                port=shape(o['layers'][layer]).intersection(copper)
                assert not port.is_empty
                result['via:'+','.join(map(str,o['position_mm']))]=port
            return result
        rows.append(dict(label=layer,net='PWR_DC_IN',layer=layer,copper=copper,
                         sources=ports(starts),sinks=ports(ends),
                         source_objects=[o['uuid'] for o in starts],sink_objects=[o['uuid'] for o in ends]))
    return rows


def run():
    assert not OUT.exists()
    captures = [json.loads(p.read_text()) for p in [BEFORE, AFTER]]
    manifest_path = CANDIDATE / 'western-logic-returns-routing.json'
    manifest = json.loads(manifest_path.read_text())
    for data in [*captures, manifest]:
        for name, digest in data['source_sha256'].items():
            path = Path(name)
            assert sha(path if path.is_absolute() else REPO / path) == digest, name
    exceptions = manifest['supply_plane_via_exceptions']
    assert len(exceptions) == 1
    exception = exceptions[0]
    site = exception['position_mm']
    assert site == [25.45, 115.25]
    allowed = set(exception['affected_supply_zone_uuids'])
    maps = [{z['uuid']: z for z in c['zones']} for c in captures]
    supply_ids = {u for u, z in maps[0].items() if z['net'] != 'PWR_AGND'}
    assert len(supply_ids) == 11 and len(allowed) == 2 and allowed <= supply_ids
    assert all(maps[0][u] == maps[1][u] for u in supply_ids-allowed)
    delta = []
    for uid in sorted(allowed):
        old, new = [m[uid] for m in maps]
        assert old['net'] == new['net'] == 'PWR_DC_IN'
        assert old['layer'] == new['layer'] and old['authored_outline'] == new['authored_outline']
        a, b = shape(old['polygons']), shape(new['polygons'])
        removed, added = a.difference(b), b.difference(a)
        assert .1 < removed.area < 1 and added.area < 1e-8
        assert removed.difference(Point(site).buffer(.550002)).area < 1e-8
        assert len(old['polygons']) == len(new['polygons'])
        old_holes, new_holes = [sum(len(p['holes']) for p in z['polygons']) for z in [old, new]]
        assert new_holes == old_holes+1
        delta.append(dict(uuid=uid, layer=old['layer'], removed_mm2=removed.area,
                          added_mm2=added.area, unchanged_components=len(old['polygons']),
                          old_holes=old_holes, new_holes=new_holes,
                          change_inside_declared_via_radius_mm=.550002))
    models = [{r['layer']: r for r in feed_cases(c) if r['net'] == 'PWR_DC_IN' and r['label'].startswith('In')}
              for c in captures]
    assert all(set(m) == {'In2.Cu', 'In3.Cu'} for m in models)
    for layer in models[0]:
        for terminal in ['sources', 'sinks']:
            a, b = [m[layer][terminal] for m in models]
            assert a.keys() == b.keys() and all(a[k].equals_exact(b[k], 1e-9) for k in a)
        assert models[0][layer]['source_objects'] == models[1][layer]['source_objects']
        assert models[0][layer]['sink_objects'] == models[1][layer]['sink_objects']
    results = []
    for label, model in zip(['before', 'after'], models):
        for layer, case in sorted(model.items()):
            rows = []
            for step, origin in [(.1, (0, 0)), (.075, (0, 0)), (.0625, (0, 0)), (.0625, (.03125, .03125))]:
                row = solve_sheet(case['copper'], case['sources'], case['sinks'], step, origin,
                                  probe_regions={'via_neighborhood_3mm': Point(site).buffer(3)})
                rows.append(row)
                print(json.dumps(dict(board=label, layer=layer, step=step, origin=origin,
                                      squares=row['resistance_squares'], nodes=row['active_nodes'],
                                      local_peak=row['probes']['via_neighborhood_3mm']['maximum_edge_normal_A_per_mm_per_terminal_A'])), flush=True)
            results.append(dict(board=label, layer=layer, source_objects=case['source_objects'],
                                sink_objects=case['sink_objects'], meshes=rows,
                                fine_refinement_relative_difference=abs(rows[1]['resistance_squares']/rows[2]['resistance_squares']-1),
                                fine_grid_shift_relative_difference=abs(rows[3]['resistance_squares']/rows[2]['resistance_squares']-1)))
    paired = []
    for index in range(4):
        snapshots = []
        for label in ['before', 'after']:
            selected = [r for r in results if r['board'] == label]
            resistance = 1/sum(1/r['meshes'][index]['resistance_squares'] for r in selected)
            layers = []
            for r in selected:
                mesh = r['meshes'][index]
                fraction = resistance/mesh['resistance_squares']
                peak = mesh['probes']['via_neighborhood_3mm']['maximum_edge_normal_A_per_mm_per_terminal_A']
                layers.append(dict(layer=r['layer'], ideal_layer_current_fraction=fraction,
                                   local_peak_face_normal_A_per_mm_at_4A=peak*fraction*4))
            snapshots.append(dict(board=label, paired_squares=resistance, layers=layers))
        assert snapshots[1]['paired_squares'] >= snapshots[0]['paired_squares']-1e-8
        paired.append(dict(mesh_index=index, before=snapshots[0], after=snapshots[1],
                           paired_resistance_relative_change=snapshots[1]['paired_squares']/snapshots[0]['paired_squares']-1))
    sources = [Path(__file__), BEFORE, AFTER, manifest_path,
               *[REPO/'hardware/fabrication'/n for n in ['sheet_resistance_with_probes.py',
                  'sheet_resistance.py', 'analyze_two_board_inlet_resistance.py', 'route_nf_surface.py']],
               REPO/'tests/tooling/test_sheet_resistance_probes.py', REPO/'uv.lock']
    report = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
                  supply_deltas=delta, nine_other_supply_fields_exact=True,
                  native_contacts_identical=True, source_via_position_mm=site,
                  cases=results, paired_comparisons=paired,
                  numerical_refinement_within_2_percent=all(r['fine_refinement_relative_difference'] < .02 and r['fine_grid_shift_relative_difference'] < .02 for r in results),
                  assumptions='Uniform isotropic sheet and identical thickness/conductivity on both parallel feed layers; ideal equipotential contact banks; 4 A is a conditional comparison scenario.',
                  limits=['Excludes via barrels, unequal bank voltage and intermediate interlayer coupling',
                          'Face-normal grid current is not peak vector current density',
                          'No accepted copper thickness, load envelope, temperature rise or current rating',
                          'Numerical estimates are not guaranteed physical bounds'],
                  thermal_qualified=False, fabrication_released=False)
    OUT.mkdir()
    (OUT/'review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(supply_deltas=delta, fine_relative_resistance_change=paired[2]['paired_resistance_relative_change'],
                          numerical_refinement_within_2_percent=report['numerical_refinement_within_2_percent'])))


if __name__ == '__main__':
    run()
