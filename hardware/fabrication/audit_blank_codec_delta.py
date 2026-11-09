"""Independently audit LED_BLANK closure and full CODEC_RUN reconnection."""
import copy
import json
import math
from collections import Counter
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta, native_evidence_errors
from hardware.fabrication.audit_led35_dac_pot_delta import check as parent_check
from hardware.fabrication.audit_digital_pot_filter import check as physical_check
from hardware.fabrication.digital_copper_clearance import verify_added_track_clearance
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent
LED, CODEC = 'LED_BLANK', 'CODEC_RUN'
NETS = {LED,CODEC}
RETIRED = {'e62678be-4939-5f0b-8633-4a4e50f062b1'}


def copper(tree):
    return {first(n, 'uuid')[1]: n for tag in ('segment', 'via') for n in children(tree, tag)}


def xy(values):
    return tuple(round(float(v), 6) for v in values)


def verify_delta(before, after, recipe):
    delta = geometry_delta(before, after)
    assert delta == recipe['geometry_delta'] and delta['other_root_geometry_exact']
    assert all(delta[t] == dict(added=[], removed=[], changed=[]) for t in ('footprint', 'zone'))
    assert len(delta['segment']['added']) == 65 and len(delta['segment']['removed']) == 1 and not delta['segment']['changed']
    assert len(delta['via']['added']) == 10 and not delta['via']['removed'] and not delta['via']['changed']
    old, new = copper(before), copper(after)
    retired = RETIRED
    assert retired == set(delta['segment']['removed']+delta['via']['removed']) == set(recipe['removed_uuids'])
    assert {first(n, 'uuid')[1] for n in recipe['removed_objects']} == retired
    assert all(n == old[first(n, 'uuid')[1]] for n in recipe['removed_objects'])
    assert all(first(old[uid], 'net')[1] == CODEC and first(old[uid], 'layer')[1] == 'B.Cu' and float(first(old[uid], 'width')[1]) == .2 for uid in RETIRED)
    expected_tracks, expected_vias = Counter(), Counter()
    assert {r['net'] for r in recipe['routes']} == NETS and len(recipe['routes']) == 2
    for r in recipe['routes']:
        for face, path in r['runs']:
            for p, q in zip(path, path[1:]):
                if math.dist(p, q) >= 1e-7:
                    expected_tracks[(r['net'], face, xy(p), xy(q))] += 1
        for p in r['new_vias_mm']:
            expected_vias[(r['net'], xy(p))] += 1
    actual_tracks, actual_vias = Counter(), Counter()
    for uid in delta['segment']['added']:
        n = new[uid]
        assert float(first(n, 'width')[1]) == .2
        assert first(n, 'layer')[1] in ('F.Cu', 'In3.Cu', 'In5.Cu', 'B.Cu')
        actual_tracks[(first(n,'net')[1], first(n,'layer')[1], xy(first(n,'start')[1:]), xy(first(n,'end')[1:]))] += 1
    for uid in delta['via']['added']:
        n = new[uid]
        assert float(first(n, 'size')[1]) == .6 and float(first(n, 'drill')[1]) == .3
        assert first(n, 'layers')[1:] == ['F.Cu', 'B.Cu']
        actual_vias[(first(n,'net')[1], xy(first(n,'at')[1:]))] += 1
    assert actual_tracks == expected_tracks and actual_vias == expected_vias
    return delta


def check():
    parent = ROOT/'staging/digital-led35-dac-pot-native-01'
    out = ROOT/'staging/digital-blank-codec-native-01'
    rd = ROOT/'staging/digital-blank-codec-repair-02'
    rp = rd/'construction.json'
    recipe = json.loads(rp.read_text())
    assert all(sha(Path(p)) == h for p, h in recipe['source_sha256'].items())
    candidate = rd/'digital_core.kicad_pcb'
    assert sha(candidate) == recipe['candidate_PCB_sha256']
    before, after = [read_sexpr((p/'digital_core.kicad_pcb').read_text()) for p in (parent, out)]
    delta = verify_delta(before, after, recipe)
    native_delta = geometry_delta(read_sexpr(candidate.read_text()), after)
    assert native_delta['other_root_geometry_exact']
    assert all(native_delta[t] == dict(added=[], removed=[], changed=[]) for t in ('footprint','segment','via','zone'))
    pp, physical = parent/'led35-dac-pot-review.json', out/'corridor-audit.json'
    assert parent_check() == json.loads(pp.read_text())
    assert physical_check(out.name, 'digital-blank-codec-inputs-32') == json.loads(physical.read_text())
    paths = [Path(__file__), rp, candidate, pp, physical]
    records = []
    for folder, opens in ((parent, 33), (out, 32)):
        p = folder/'review.json'
        review = json.loads(p.read_text())
        assert not native_evidence_errors(folder/'digital_core.kicad_pro', review)
        assert review['status']['counts'] == dict(violations=0, unconnected_items=opens, schematic_parity=0, erc=0)
        cp = folder/'stage-connectivity-review.json'
        witness = json.loads(cp.read_text())
        assert all(sha(Path(p)) == h for p, h in witness['source_sha256'].items())
        records.append(witness)
        paths += [p, cp, folder/'digital_core.kicad_pcb']
    old, new = [{r['net']: r for r in w['nets']} for w in records]
    assert old.keys() == new.keys()
    improved = []
    for net, prior in old.items():
        a, b = [[set(map(tuple,g)) for g in r['pad_groups']] for r in (prior,new[net])]
        assert set.union(*a) == set.union(*b) and all(any(g <= h for h in b) for g in a), net
        if len(b) < len(a):
            improved.append(net)
        if net not in NETS:
            assert new[net] == prior, net
    assert improved == [LED] and all(new[n]['all_pads_connected'] for n in NETS)
    assert records[1]['open_nets'] == 32
    assert sum(n.startswith('/LED/LED_') and not r['all_pads_connected'] for n,r in new.items()) == 29
    assert all(new[f'/CONTROLS/CONTROL_{i:02d}']['all_pads_connected'] for i in range(32))
    assert len(children(after,'segment')) == 3181 and len(children(after,'via')) == 518
    cp = ROOT/'staging/digital-blank-codec-inputs-32/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p,h in cap['source_sha256'].items())
    clearance = verify_added_track_clearance(cap, delta['segment']['added'])
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .01
    faces = surface.SIGNAL_LAYERS = ('F.Cu','In3.Cu','In5.Cu','B.Cu')
    via_ids = set(delta['via']['added'])
    for obj in cap['objects']:
        if obj['uuid'] in via_ids:
            work = copy.deepcopy(cap)
            work['objects'] = [o for o in cap['objects'] if o['uuid'] != obj['uuid']]
            assert DigitalViaScreen(work, signal_layers=faces).via_legal(obj['net'], obj['position_mm'])
    for net, count in ((LED,4), (CODEC,6)):
        route, = [r for r in recipe['routes'] if r['net'] == net]
        assert len(route['new_vias_mm']) == count
        retired = [n for n in recipe['removed_objects'] if first(n,'net')[1] == net]
        retired_length = sum(math.dist(xy(first(n,'start')[1:]),xy(first(n,'end')[1:])) for n in retired if n[0] == 'segment')
        retired_vias = sum(n[0] == 'via' for n in retired)
        assert math.isclose(new[net]['planar_copper_length_mm'], old[net]['planar_copper_length_mm']-retired_length+route['planar_length_mm'], abs_tol=1e-5)
        assert new[net]['via_count'] == old[net]['via_count']-retired_vias+count
    for name in ('conditional-assembly-review.json','visual-review.json'):
        p = out/name
        receipt = json.loads(p.read_text())
        assert all(sha(Path(k)) == v for k,v in receipt['source_sha256'].items())
        paths.append(p)
    paths += [cp]+[ROOT/n for n in ('audit_led35_dac_pot_delta.py','audit_digital_pot_filter.py','digital_copper_clearance.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py')]
    return dict(source_sha256={str(p):sha(p) for p in paths}, geometry_delta=delta,
                before_opens=33, after_opens=32, improved_nets=improved, regressed_pad_groups=[],
                net_before_after={n:dict(before=old[n],after=new[n]) for n in sorted(NETS)},
                actual_added_copper_clearance=clearance, all_other_net_records_exact=True,
                all_component_poses_and_unretired_copper_exact=True, power_local_thermal_controls_SD_and_planes_preserved=True,
                expanded_search_bound_is_not_electrical_acceptance=True,
                CODEC_RUN_section_length_increase_mm=new[CODEC]['planar_copper_length_mm']-old[CODEC]['planar_copper_length_mm'],
                BLANK_and_CODEC_timing_loading_EMC_and_installed_performance_qualified=False, fabrication_released=False)


if __name__ == '__main__':
    result = check()
    with (ROOT/'staging/digital-blank-codec-native-01/blank-codec-review.json').open('x') as f:
        json.dump(result,f,indent=2)
        f.write('\n')
    print('LED_BLANK and CODEC_RUN verified; 33 -> 32 opens')
