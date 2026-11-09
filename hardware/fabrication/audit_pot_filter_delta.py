"""Verify the sole R1040 move, replacement raw spur and new ADC connection."""
import copy
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta, native_evidence_errors
from hardware.fabrication.audit_digital_exact_regions_checkpoint import check as parent_check
from hardware.fabrication.audit_digital_pot_filter import check as physical_check
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v3 as search

ROOT = Path(__file__).resolve().parent
RAW, ADC = '/PROCESSOR/POT_RAW_09', '/PROCESSOR/POT_ADC_09'
SPUR = '3d975814-3478-589e-852c-ac1c628c708f'


def refs(tree):
    return {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f for f in children(tree, 'footprint')}


def copper(tree):
    return {first(n, 'uuid')[1]: n for tag in ('segment', 'via') for n in children(tree, tag)}


def verify_board_delta(before, after, recipe, template):
    old, new = refs(before), refs(after)
    assert old.keys() == new.keys()
    assert all(sexpr(f) == sexpr(new[r]) for r, f in old.items() if r != 'R1040')
    moved = copy.deepcopy(new['R1040'])
    assert list(map(float, first(old['R1040'], 'at')[1:3])) == [70., 30.]
    assert first(old['R1040'], 'layer')[1] == 'F.Cu'
    assert list(map(float, first(moved, 'at')[1:3])) == [40.5, 35.5]
    assert first(moved, 'layer')[1] == 'B.Cu'
    assert float(first(moved, 'at')[3]) == 90
    moved[moved.index(first(moved, 'at'))] = copy.deepcopy(first(template, 'at'))
    assert sexpr(moved) == sexpr(template)
    delta = geometry_delta(before, after)
    assert delta == recipe['geometry_delta'] and delta['other_root_geometry_exact']
    assert delta['footprint'] == dict(added=[], removed=[], changed=[first(old['R1040'], 'uuid')[1]])
    assert delta['zone'] == dict(added=[], removed=[], changed=[])
    assert len(delta['segment']['added']) == 25 and delta['segment']['removed'] == [SPUR] and not delta['segment']['changed']
    assert len(delta['via']['added']) == 4 and not delta['via']['removed'] and not delta['via']['changed']
    olds, news = copper(before), copper(after)
    assert recipe['removed_uuids'] == [SPUR] and recipe['removed_objects'] == [olds[SPUR]]
    assert first(olds[SPUR], 'net')[1] == RAW
    for tag in ('segment', 'via'):
        for ident in delta[tag]['added']:
            n = news[ident]
            assert first(n, 'net')[1] in (RAW, ADC)
            if tag == 'segment':
                assert float(first(n, 'width')[1]) == .2
                assert first(n, 'layer')[1] in ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
            else:
                assert float(first(n, 'size')[1]) == .6 and float(first(n, 'drill')[1]) == .3
    return delta


def check():
    parent = ROOT/'staging/digital-exact-regions-native-01'
    out = ROOT/'staging/digital-pot-filter-native-01'
    rd = ROOT/'staging/digital-pot-filter-repack-04'
    rp = rd/'construction.json'
    recipe = json.loads(rp.read_text())
    assert all(sha(Path(p)) == h for p, h in recipe['source_sha256'].items())
    candidate = rd/'digital_core.kicad_pcb'
    assert sha(candidate) == recipe['candidate_PCB_sha256']
    tp = ROOT/'staging/digital-pot-filter-templates-01/R1040-B-90.kicad_mod'
    template = read_sexpr(tp.read_text())
    paths = [Path(__file__), rp, candidate, tp]
    before, after = [read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (parent, out)]
    delta = verify_board_delta(before, after, recipe, template)
    native_delta = geometry_delta(read_sexpr(candidate.read_text()), after)
    assert native_delta['other_root_geometry_exact']
    assert all(native_delta[t] == dict(added=[], removed=[], changed=[]) for t in ('footprint', 'segment', 'via', 'zone'))
    pp, physical = parent/'exact-regions-review.json', out/'corridor-audit.json'
    assert parent_check() == json.loads(pp.read_text())
    assert physical_check(out.name, 'digital-pot-filter-inputs-40') == json.loads(physical.read_text())
    paths += [pp, physical]
    records = []
    for folder, opens in ((parent, 41), (out, 40)):
        p = folder/'review.json'
        review = json.loads(p.read_text())
        assert not native_evidence_errors(folder/'digital_core.kicad_pro', review)
        assert review['status']['counts'] == dict(violations=0, unconnected_items=opens, schematic_parity=0, erc=0)
        cp = folder/'stage-connectivity-review.json'
        witness = json.loads(cp.read_text())
        assert all(sha(Path(p)) == h for p, h in witness['source_sha256'].items())
        records.append(witness)
        paths += [p, cp, folder/'digital_core.kicad_pcb']
    old, new = [{r['net']: r for r in c['nets']} for c in records]
    assert old.keys() == new.keys()
    improved = []
    for net, prior in old.items():
        a, b = [[set(map(tuple, g)) for g in r['pad_groups']] for r in (prior, new[net])]
        assert set.union(*a) == set.union(*b) and all(any(g <= h for h in b) for g in a), net
        if len(b) < len(a):
            improved.append(net)
        if net not in (RAW, ADC):
            assert new[net] == prior, net
    assert improved == [ADC] and all(new[n]['all_pads_connected'] for n in (RAW, ADC))
    assert records[1]['open_nets'] == 40
    assert len(children(after, 'segment')) == 2768 and len(children(after, 'via')) == 480
    cp = ROOT/'staging/digital-pot-filter-inputs-40/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p, h in cap['source_sha256'].items())
    ids = set(delta['segment']['added']+delta['via']['added'])
    added = [o for o in cap['objects'] if o['uuid'] in ids]
    assert len(added) == 29
    surface.WIDTH = layers.WIDTH = raster.WIDTH = search.WIDTH = .2
    surface.MARGIN = .01
    faces = ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
    screen = DigitalViaScreen(cap, signal_layers=faces)
    for o in added:
        if o['kind'] == 'PCB_TRACK':
            assert screen.legal(o['net'], next(iter(o['layers'])), [o['position_mm'], o['end_mm']])
        else:
            work = copy.deepcopy(cap)
            work['objects'] = [p for p in cap['objects'] if p['uuid'] != o['uuid']]
            assert DigitalViaScreen(work, signal_layers=faces).via_legal(o['net'], o['position_mm'])
    for route in recipe['routes']:
        net = route['net']
        segments = [(f, p, q) for f, path in route['runs'] for p, q in zip(path, path[1:]) if math.dist(p, q) > 1e-7]
        tracks = [o for o in added if o['net'] == net and o['kind'] == 'PCB_TRACK']
        vias = [o for o in added if o['net'] == net and o['kind'] == 'PCB_VIA']
        assert len(segments) == len(tracks) and len(vias) == len(route['new_vias_mm'])
        assert all(any(f in o['layers'] and math.dist(p, o['position_mm']) < 2e-6 and math.dist(q, o['end_mm']) < 2e-6 for o in tracks) for f, p, q in segments)
        assert all(any(math.dist(p, o['position_mm']) < 2e-6 for o in vias) for p in route['new_vias_mm'])
        removed_length = math.dist([float(x) for x in first(copper(before)[SPUR], 'start')[1:3]], [float(x) for x in first(copper(before)[SPUR], 'end')[1:3]]) if net == RAW else 0
        assert math.isclose(new[net]['planar_copper_length_mm'], old[net]['planar_copper_length_mm']-removed_length+route['planar_length_mm'], abs_tol=1e-5)
        assert new[net]['via_count'] == old[net]['via_count']+len(vias)
    for name in ('conditional-assembly-review.json', 'visual-review.json'):
        p = out/name
        receipt = json.loads(p.read_text())
        assert all(sha(Path(k)) == v for k, v in receipt['source_sha256'].items())
        paths.append(p)
    paths += [cp]+[ROOT/n for n in ('digital_via_spacing_v2.py', 'route_nf_surface.py', 'nf_minimum_logic.py', 'nf_pin_escape_routes.py', 'digital_native_spacing_search_v3.py')]
    return dict(source_sha256={str(p): sha(p) for p in paths}, geometry_delta=delta, component_move=recipe['component_move'],
                before_opens=41, after_opens=40, improved_nets=improved, regressed_pad_groups=[],
                net_before_after={n: dict(before=old[n], after=new[n]) for n in (RAW, ADC)},
                all_other_net_records_exact=True, all_unretired_copper_and_other_component_poses_exact=True,
                power_local_thermal_SD_and_planes_preserved=True, control_settling_noise_loading_and_installed_performance_qualified=False,
                fabrication_released=False)


if __name__ == '__main__':
    result = check()
    with (ROOT/'staging/digital-pot-filter-native-01/pot-filter-review.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print('Exact R1040 relocation audit passed; 41 -> 40 opens; every earlier pad group retained')
