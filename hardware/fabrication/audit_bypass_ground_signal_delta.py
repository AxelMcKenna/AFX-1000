"""Audit BYPASS_SENSE closure, two signal restorations and thermal-branch relocation."""
import copy
import json
import math
from collections import Counter
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import sha, geometry_delta, native_evidence_errors
from hardware.fabrication.audit_blank_codec_delta import check as parent_check
from hardware.fabrication.audit_digital_pot_filter import check as physical_check
from hardware.fabrication.digital_copper_clearance import verify_added_track_clearance
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen as DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

ROOT = Path(__file__).resolve().parent
LED, CODEC, LATCH, GROUND = 'BYPASS_SENSE', 'CODEC_RUN', '/LED/LATCH_5V', 'AGND'
NETS = {LED,CODEC,LATCH,GROUND}
SIGNALS = {LED,CODEC,LATCH}
RETIRED = {'af606d42-b58e-5757-9568-378377db938e','b30f01e6-b9f7-54aa-9d6a-2761e55ac0e2','169e771c-c1c3-4b76-988a-dd2d411f24f8','6bede44e-44ec-43a7-8ed5-9b0649087a5b'}
GROUND_TRACK = 'c69d87f9-b134-552b-97be-347c7c20a818'
GROUND_VIA = '1709749b-df70-5b29-a600-bf25408c657f'


def copper(tree):
    return {first(n, 'uuid')[1]: n for tag in ('segment', 'via') for n in children(tree, tag)}


def xy(values):
    return tuple(round(float(v), 6) for v in values)


def verify_delta(before, after, recipe):
    delta = geometry_delta(before, after)
    assert delta == recipe['geometry_delta'] and delta['other_root_geometry_exact']
    assert all(delta[t] == dict(added=[], removed=[], changed=[]) for t in ('footprint', 'zone'))
    assert len(delta['segment']['added']) == 59 and len(delta['segment']['removed']) == 4 and delta['segment']['changed'] == [GROUND_TRACK]
    assert len(delta['via']['added']) == 7 and not delta['via']['removed'] and delta['via']['changed'] == [GROUND_VIA]
    old, new = copper(before), copper(after)
    retired = RETIRED
    assert retired == set(delta['segment']['removed']+delta['via']['removed']) == set(recipe['removed_uuids'])
    assert {first(n, 'uuid')[1] for n in recipe['removed_objects']} == retired
    assert all(n == old[first(n, 'uuid')[1]] for n in recipe['removed_objects'])
    assert all(first(old[uid], 'net')[1] in {CODEC,LATCH} and first(old[uid], 'layer')[1] == 'B.Cu' and float(first(old[uid], 'width')[1]) == .2 for uid in RETIRED)
    assert recipe['ground_track_before'] == old[GROUND_TRACK] and recipe['ground_via_before'] == old[GROUND_VIA]
    assert float(first(old[GROUND_TRACK],'width')[1]) == 1.
    assert xy(first(old[GROUND_TRACK],'start')[1:]) == (100.,28.)
    assert xy(first(old[GROUND_TRACK],'end')[1:]) == xy(first(old[GROUND_VIA],'at')[1:]) == (100.,27.)
    assert float(first(old[GROUND_VIA],'size')[1]) == .6 and float(first(old[GROUND_VIA],'drill')[1]) == .3
    ground = recipe['ground_relocation']
    assert ground['track_start_mm'] == [98.,28.] and ground['via_point_mm'] == ground['track_end_mm'] == [99.5,25.7]
    assert ground['track_width_mm'] == 1.
    assert xy(first(new[GROUND_TRACK],'start')[1:]) == xy(ground['track_start_mm'])
    assert xy(first(new[GROUND_TRACK],'end')[1:]) == xy(first(new[GROUND_VIA],'at')[1:]) == xy(ground['via_point_mm'])
    for uid, tags in ((GROUND_TRACK,('start','end')),(GROUND_VIA,('at',))):
        restored = copy.deepcopy(new[uid])
        for tag in tags:
            restored[restored.index(first(restored,tag))] = copy.deepcopy(first(old[uid],tag))
        assert restored == old[uid]
    assert math.isclose(ground['track_length_mm'],math.dist(ground['track_start_mm'],ground['track_end_mm']),abs_tol=1e-9)
    expected_tracks, expected_vias = Counter(), Counter()
    assert {r['net'] for r in recipe['routes']} == SIGNALS and len(recipe['routes']) == 4
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
    parent = ROOT/'staging/digital-blank-codec-native-01'
    out = ROOT/'staging/digital-bypass-ground-signal-native-02'
    rd = ROOT/'staging/digital-bypass-ground-signal-repair-03'
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
    pp, physical = parent/'blank-codec-review.json', out/'corridor-audit.json'
    assert parent_check() == json.loads(pp.read_text())
    assert physical_check(out.name, 'digital-bypass-ground-signal-inputs-31') == json.loads(physical.read_text())
    paths = [Path(__file__), rp, candidate, pp, physical]
    records = []
    for folder, opens in ((parent, 32), (out, 31)):
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
    assert records[1]['open_nets'] == 31
    assert sum(n.startswith('/LED/LED_') and not r['all_pads_connected'] for n,r in new.items()) == 29
    assert all(new[f'/CONTROLS/CONTROL_{i:02d}']['all_pads_connected'] for i in range(32))
    assert len(children(after,'segment')) == 3236 and len(children(after,'via')) == 525
    cp = ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json'
    cap = json.loads(cp.read_text())
    assert all(sha(Path(p)) == h for p,h in cap['source_sha256'].items())
    clearance = verify_added_track_clearance(cap, delta['segment']['added']+[GROUND_TRACK])
    surface.WIDTH = layers.WIDTH = .2
    surface.MARGIN = .001
    faces = surface.SIGNAL_LAYERS = ('F.Cu','In3.Cu','In5.Cu','B.Cu')
    via_ids = set(delta['via']['added']+[GROUND_VIA])
    for obj in cap['objects']:
        if obj['uuid'] in via_ids:
            work = copy.deepcopy(cap)
            work['objects'] = [o for o in cap['objects'] if o['uuid'] != obj['uuid']]
            assert DigitalViaScreen(work, signal_layers=faces).via_legal(obj['net'], obj['position_mm'])
    for net, count in ((LED,4), (CODEC,0), (LATCH,3)):
        routes = [r for r in recipe['routes'] if r['net'] == net]
        assert sum(len(r['new_vias_mm']) for r in routes) == count
        retired = [n for n in recipe['removed_objects'] if first(n,'net')[1] == net]
        retired_length = sum(math.dist(xy(first(n,'start')[1:]),xy(first(n,'end')[1:])) for n in retired if n[0] == 'segment')
        retired_vias = sum(n[0] == 'via' for n in retired)
        assert math.isclose(new[net]['planar_copper_length_mm'], old[net]['planar_copper_length_mm']-retired_length+sum(r['planar_length_mm'] for r in routes), abs_tol=1e-5)
        assert new[net]['via_count'] == old[net]['via_count']-retired_vias+count
    assert new[GROUND]['via_count'] == old[GROUND]['via_count']
    assert math.isclose(new[GROUND]['planar_copper_length_mm'],old[GROUND]['planar_copper_length_mm']-1.+recipe['ground_relocation']['track_length_mm'],abs_tol=1e-5)
    assert new[GROUND]['pad_groups'] == old[GROUND]['pad_groups']
    for name in ('conditional-assembly-review.json','visual-review.json'):
        p = out/name
        receipt = json.loads(p.read_text())
        assert all(sha(Path(k)) == v for k,v in receipt['source_sha256'].items())
        paths.append(p)
    paths += [cp]+[ROOT/n for n in ('audit_blank_codec_delta.py','audit_digital_pot_filter.py','digital_copper_clearance.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py')]
    return dict(source_sha256={str(p):sha(p) for p in paths}, geometry_delta=delta,
                before_opens=32, after_opens=31, improved_nets=improved, regressed_pad_groups=[],
                net_before_after={n:dict(before=old[n],after=new[n]) for n in sorted(NETS)},
                actual_added_copper_clearance=clearance, all_other_net_records_exact=True,
                all_component_poses_and_undeclared_copper_exact=True,
                thermal_via_identity_drill_and_1mm_branch_width_preserved=True, power_local_thermal_controls_SD_and_planes_preserved=True,
                ground_relocation=recipe['ground_relocation'],
                timing_thermal_loading_coupling_EMC_and_installed_performance_qualified=False, fabrication_released=False)


if __name__ == '__main__':
    result = check()
    with (ROOT/'staging/digital-bypass-ground-signal-native-02/bypass-ground-signal-review.json').open('x') as f:
        json.dump(result,f,indent=2)
        f.write('\n')
    print('BYPASS, CODEC, LATCH and thermal branch verified; 32 -> 31 opens')
