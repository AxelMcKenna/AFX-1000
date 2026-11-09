"""Conditional resistance screen of TBP35's actual inlet planes and local copper.

This does not establish a stack, load envelope, temperature rise, current rating
or a complete input-loop resistance. Ideal contacts exclude barrel/local-board
voltage differences. The report explicitly distinguishes estimates from bounds.
"""
import argparse
import json
from shapely.ops import unary_union
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.sheet_resistance import solve_sheet

CAP = STAGING/'two-board-power-routing-inputs-2372-inlet-fuse-01/capture.json'
STATUS = STAGING/'two-board-fabrication-status-35/status.json'
NATIVE = STAGING/'two-board-power-inlet-fuse-native-01'


from hardware.fabrication.analyze_two_board_inlet_resistance import cases


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    assert all(c.isalnum() or c in '-_' for c in args.output)
    out = STAGING/args.output
    assert not out.exists()
    cap = json.loads(CAP.read_text())
    for p in [CAP, STATUS]:
        for name, h in json.loads(p.read_text())['source_sha256'].items():
            assert sha(REPO/name) == h, name
    results = []
    for case in cases(cap):
        # Surface net groups also contain distant islands linked only through
        # other layers. Drop polygons that touch neither end, or only one
        # ideal terminal: they carry no DC current in this separate-sheet model.
        if case['layer'] == 'F.Cu':
            copper = case['copper']
            pieces = [copper] if copper.geom_type == 'Polygon' else list(copper.geoms)
            active = [g for g in pieces if any(g.intersects(p) for p in case['sources'].values())
                      and any(g.intersects(p) for p in case['sinks'].values())]
            case['excluded_zero_current_copper_mm2'] = copper.area-sum(g.area for g in active)
            assert active
            case['copper'] = unary_union(active)
            assert all(case['copper'].intersects(p) for p in [*case['sources'].values(), *case['sinks'].values()])
        case['steps'] = [.1, .075, .0625] if case['label'].startswith('In') else [.025, .0125, .00625]
        rows = []
        for step in case['steps']:
            row = solve_sheet(case['copper'], case['sources'], case['sinks'], step)
            rows.append(row)
            print(json.dumps(dict(case=case['label'], step=step, squares=row['resistance_squares'], nodes=row['active_nodes'])), flush=True)
        # A shifted fine grid exposes contact/raster alignment sensitivity.
        step = case['steps'][-1]
        shifted = solve_sheet(case['copper'], case['sources'], case['sinks'], step, (step/2, step/2))
        fine = rows[-1]['resistance_squares']
        result = {k: v for k, v in case.items() if k not in ['copper', 'sources', 'sinks', 'steps']}
        result.update(meshes=rows, shifted_fine_mesh=shifted,
            fine_refinement_relative_difference=abs(rows[-2]['resistance_squares']/fine-1),
            fine_grid_shift_relative_difference=abs(shifted['resistance_squares']/fine-1))
        results.append(result)
    squares = {r['label']: r['meshes'][-1]['resistance_squares'] for r in results}
    def parallel(names):
        return 1/sum(1/squares[n] for n in names)
    feed = parallel(['In2.Cu', 'In3.Cu']); ret = parallel(['In4.Cu', 'In5.Cu'])
    front = sum(r for n, r in squares.items() if not n.startswith('In'))
    scenarios = []
    # Explicit assumptions, not a transferred E28 stack or accepted fabrication
    # minimum: same chosen thickness on each modeled layer in each scenario.
    for thickness_um in [35, 70]:
        for temperature_C in [20, 85]:
            sheet = 1.7241e-8/(thickness_um*1e-6)*(1+.00393*(temperature_C-20))
            resistance = (feed+ret+front)*sheet
            scenarios.append(dict(copper_thickness_um=thickness_um, uniform_copper_temperature_C=temperature_C,
                sheet_resistance_ohm=sheet, paired_feed_ohm=feed*sheet, paired_return_ohm=ret*sheet,
                modeled_front_sections_ohm=front*sheet, modeled_copper_subtotal_ohm=resistance,
                at_4A=dict(drop_v=4*resistance, dissipation_w=16*resistance),
                at_4_83A=dict(drop_v=4.83*resistance, dissipation_w=4.83**2*resistance)))
    shares = {}
    for names in [['In2.Cu', 'In3.Cu'], ['In4.Cu', 'In5.Cu']]:
        resistance = parallel(names)
        for n in names:
            fraction = resistance/squares[n]
            r = next(r for r in results if r['label'] == n)
            shares[n] = dict(layer_current_fraction=fraction,
                ideal_port_currents_at_4A={p: 4*fraction*v['fraction'] for p, v in r['meshes'][-1]['ports'].items()})
    sources = [Path(__file__), REPO/'hardware/fabrication/analyze_two_board_inlet_resistance.py', STAGING/'two-board-inlet-resistance-01/review.json', REPO/'hardware/fabrication/sheet_resistance.py', CAP, STATUS,
               REPO/'tests/tooling/test_sheet_resistance.py', REPO/'uv.lock',
               REPO/'hardware/fabrication/route_nf_surface.py',
               NATIVE/'inlet-fuse-review.json', NATIVE/'inlet-fuse-change.json']
    report = dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        model='2D uniform isotropic sheet; four-neighbour finite-volume resistor grid; ideal equipotential contact ports',
        copper_reference='https://nvlpubs.nist.gov/nistpubs/Legacy/hb/nbshandbook100.pdf',
        assumptions=dict(resistivity_20C_ohm_m=1.7241e-8, resistance_temperature_coefficient_per_C=.00393,
                         conductivity='100% IACS assumed; actual PCB foil/plating conductivity unaccepted',
                         temperatures_are_imposed_not_predicted=True, physical_current_rating_established=False),
        cases=results, layer_and_port_shares=shares, scenarios=scenarios,
        numerical_refinement_within_2_percent=all(r['fine_refinement_relative_difference'] < .02 and r['fine_grid_shift_relative_difference'] < .02 for r in results),
        excluded=['Jack/plug contacts and jack barrel/solder', 'Fuse hot operating resistance',
                  'All via-barrel resistances and non-equipotential transition banks',
                  'MOSFET and eFuse device on-resistances', 'Local bulk-return copper and downstream distribution',
                  'Solder joints, adapter/cable impedance and connector aging',
                  'Interlayer coupling at intermediate vias and other parallel copper paths',
                  'Actual thermal boundary conditions, current rating, surge inductance and fault energy'],
        results_are_estimates_not_guaranteed_bounds=True, full_input_loop_resistance_established=False,
        stack_accepted=False, thermal_qualified=False, fabrication_released=False)
    out.mkdir()
    (out/'review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(feed_squares=feed, return_squares=ret, modeled_front_squares=front, scenarios=scenarios)))


if __name__ == '__main__':
    run()
