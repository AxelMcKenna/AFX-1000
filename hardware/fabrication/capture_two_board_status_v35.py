"""Select the native, independently checked fuse correction without release."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    out = STAGING/'two-board-power-inlet-fuse-native-01'
    previous = STAGING/'two-board-fabrication-status-34/status.json'
    capture = STAGING/'two-board-power-routing-inputs-2372-inlet-fuse-01/capture.json'
    reports = [previous, capture, *[out/n for n in ['review.json', 'inlet-fuse-change.json', 'inlet-fuse-review.json']],
               STAGING/'two-board-signal-routed-native-03/review.json']
    count = 0
    for p in reports:
        d = json.loads(p.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, digest in d.get(field, {}).items():
                q = Path(name)
                if not q.is_absolute():
                    q = (REPO if name.startswith(('hardware/', 'tests/')) else p.parent)/q
                assert sha(q) == digest, (p, name)
                count += 1
    audit = json.loads((out/'inlet-fuse-review.json').read_text())
    assert audit['exact_geometry_unchanged'] and audit['all_native_groups_unchanged'] == 3110
    assert audit['power_opens'] == 2372 and audit['ERC_errors'] == 0 and audit['ERC_warnings'] == 2
    status = json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, out/'README.md']},
        previous_status=str(previous.relative_to(REPO)),
        previous_status_scope='TBP34 geometry, connectivity and visual evidence carries forward through exact whole-board and native-capture comparison; fuse value/MPN are corrected here.',
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((out/'power_protection.kicad_pro').relative_to(REPO)),
        power_connections_closed_this_pass=0, power_added_vias_this_pass=0, power_added_zones_this_pass=0,
        power_previous_native_connection_groups_preserved=3110,
        power_complete_footprints_unchanged=1100, power_moved_footprints_this_pass=0,
        power_changed_pad_instances_this_pass=0, power_unchanged_existing_zone_fills=21,
        power_changed_existing_zone_fills=0, power_native_group_merges=[],
        power_complete_footprint_geometries_unchanged=1101, power_changed_component_values_this_pass=1,
        power_input_fuse_MPN='045106.3MRL', power_input_fuse_current_rating_a=6.3,
        power_input_fuse_review=str((out/'inlet-fuse-review.json').relative_to(REPO)),
        power_input_fuse_hot_resistance_bounded=False,
        power_input_fuse_adapter_TVS_fault_coordination_qualified=False,
        power_visual_evidence_scope='TBP34 inspected copper exports remain geometrically identical; no new render claimed.',
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Qualify corrected 045106.3MRL fuse continuous/temperature derating, startup pulses, hot resistance and adapter/TVS/jack/copper fault coordination',
        *status['next_required_design_work']]
    target = STAGING/'two-board-fabrication-status-35'
    target.mkdir(exist_ok=False)
    (target/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(dict(bindings=count, fuse='045106.3MRL', power_opens=2372, signal_opens=251, fabrication_released=False)))


if __name__ == '__main__':
    run()
