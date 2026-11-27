"""Reuse a computed sheet comparison only after exact model-input equality.

The revised timeout signal and its return stitches must not change either
DC-input sheet or any of the physical feed contacts. This is input equivalence,
not an additional current or temperature qualification.
"""
import copy
import json
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.compare_two_board_western_inlet_via import feed_cases


def run():
    original = STAGING / 'two-board-western-inlet-via-comparison-01/review.json'
    before_path = STAGING / 'two-board-power-routing-inputs-logic-ground-access-01/capture.json'
    old_path = STAGING / 'two-board-power-routing-inputs-western-logic-returns-01/capture.json'
    new_path = STAGING / 'two-board-power-routing-inputs-western-logic-returns-02/capture.json'
    manifest_path = STAGING / 'two-board-power-western-logic-returns-native-02/western-logic-returns-routing.json'
    out = STAGING / 'two-board-western-inlet-via-comparison-02'
    assert not out.exists()
    result, before, old, new, manifest = [json.loads(p.read_text()) for p in
                                        [original, before_path, old_path, new_path, manifest_path]]
    for data in [result, before, old, new, manifest]:
        for name, digest in data['source_sha256'].items():
            path = Path(name)
            assert sha(path if path.is_absolute() else REPO / path) == digest, name
    assert result['source_sha256'][str(before_path.relative_to(REPO))] == sha(before_path)
    assert result['source_sha256'][str(old_path.relative_to(REPO))] == sha(old_path)
    maps = [{z['uuid']: z for z in cap['zones']} for cap in [before, old, new]]
    supply = {uid for uid, z in maps[0].items() if z['net'] != 'PWR_AGND'}
    assert len(supply) == 11
    assert all(maps[1][uid] == maps[2][uid] for uid in supply)
    exception, = manifest['supply_plane_via_exceptions']
    changed = set(exception['affected_supply_zone_uuids'])
    assert len(changed) == 2 and changed == {d['uuid'] for d in result['supply_deltas']}
    assert exception['position_mm'] == result['source_via_position_mm'] == [25.45, 115.25]
    assert all(maps[0][uid] == maps[2][uid] for uid in supply - changed)
    old_objects, new_objects = [{o['uuid']: o for o in cap['objects']} for cap in [old, new]]
    checked = []
    old_models, new_models = [feed_cases(cap) for cap in [old, new]]
    for a, b in zip(old_models, new_models, strict=True):
        for key in ['label', 'net', 'layer', 'source_objects', 'sink_objects']:
            assert a[key] == b[key], key
        assert a['copper'].equals_exact(b['copper'], 0)
        for kind in ['sources', 'sinks']:
            assert a[kind].keys() == b[kind].keys()
            assert all(a[kind][k].equals_exact(b[kind][k], 0) for k in a[kind])
        contacts = a['source_objects'] + a['sink_objects']
        assert all(old_objects[uid] == new_objects[uid] for uid in contacts)
        checked.append(dict(layer=a['layer'], exact_filled_copper=True,
                            exact_source_and_sink_shapes=True,
                            exact_physical_contact_records=True,
                            contact_uuids=contacts))
    assert len(checked) == 2
    report = copy.deepcopy(result)
    paths = [Path(__file__), original, before_path, old_path, new_path, manifest_path,
             REPO / 'hardware/fabrication/compare_two_board_western_inlet_via.py']
    report['source_sha256'].update({str(p.relative_to(REPO)): sha(p) for p in paths})
    report['computation_reuse'] = dict(
        original_report=str(original.relative_to(REPO)),
        original_report_sha256=sha(original), exact_model_inputs_verified=checked,
        all_eleven_supply_zone_records_identical_to_computed_candidate=True,
        method='Exact captured zone records, complete feed-contact object records, and zero-tolerance solver geometry equality. Original solver outputs are reused without alteration.')
    assert report['cases'] == result['cases']
    assert report['paired_comparisons'] == result['paired_comparisons']
    out.mkdir()
    (out / 'review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(exact_model_inputs=True, layers=len(checked),
                          reused_cases=len(report['cases']), fabrication_released=False)))


if __name__ == '__main__':
    run()
