"""Adopt U20 local routing with explicit internal-terminal retirement accounting."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power = STAGING / 'two-board-power-u20-local-native-01'
    previous = STAGING / 'two-board-fabrication-status-17/status.json'
    reports = [previous, *[power / n for n in [
        'review.json', 'circuit-audit.json', 'u20-local-change.json', 'u20-local-audit.json',
        'rejected-source-net-status.json', 'plots/native-plots.json', 'plots/preview-render.json',
        'plots/detail-render.json', 'plots/visual-review.json']],
        STAGING / 'two-board-power-routing-inputs-2486-u20-local/capture.json',
        STAGING / 'two-board-signal-routed-native-03/review.json']
    count = 0
    for report in reports:
        data = json.loads(report.read_text())
        for field in ['source_sha256', 'artifact_sha256']:
            for name, h in data.get(field, {}).items():
                p = Path(name)
                if not p.is_absolute():
                    p = (REPO if name.startswith(('hardware/', 'tests/')) else report.parent) / p
                assert p.is_file() and sha(p) == h, (report, name)
                count += 1
    a = json.loads((power / 'u20-local-audit.json').read_text())
    native = json.loads((power / 'review.json').read_text())
    assert a['new_opens'] == native['opens'] == 2486
    assert a['old_opens'] - a['new_opens'] == a['connections_closed'] + a['retired_terminal_groups'] == 22
    assert a['connections_closed'] == 16 and a['retired_terminal_groups'] == 6
    assert a['unchanged_remaining_pin_net_map'] and a['all_retained_tracks_vias_unchanged']
    assert a['existing_local_U23_planes_unchanged'] and a['preserved_native_connection_groups'] == 3240
    assert a['geometry_findings'] == a['parity_findings'] == a['erc_errors'] == 0
    assert a['moved_footprints'] == 20 and a['added_segments'] == 22 and a['added_vias'] == 0
    assert native['placed_electrical_parts'] == 1085 and native['mapped_pad_instances'] == 3479
    assert a['vias_screened'] == 151 and not a['return_replacement_qualified']
    status = json.loads(previous.read_text())
    status.update(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in [Path(__file__), *reports, power / 'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power / 'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=2486, power_parts=1085, power_footprints=1100,
        power_schematic_pin_entries=3418, power_mapped_pad_instances=3479,
        power_copper_segments=2199, power_copper_vias=151, power_connections_closed_this_pass=16,
        power_moved_footprints_this_pass=20, power_replaced_footprints_this_pass=1,
        power_changed_pad_instances_this_pass=68,
        power_schematic_pin_net_changes_this_pass=0, power_retired_schematic_pins_this_pass=6,
        power_retained_track_net_changes_this_pass=0,
        power_all_component_poses_preserved=False, power_remaining_pin_net_map_unchanged=True,
        power_all_retained_copper_objects_unchanged=False,
        power_all_retained_copper_geometry_unchanged=False,
        power_all_retained_tracks_vias_unchanged=True,
        power_all_other_copper_objects_unchanged=True,
        power_intentionally_replaced_MODE_tracks=0, power_intentionally_replaced_MODE_vias=0,
        power_previous_native_connection_groups_preserved=3240,
        power_previous_native_connection_groups_retired=6,
        power_all_vias_screened=151,
        power_minimum_all_via_drill_to_SMD_mm=a['minimum_all_via_drill_to_SMD_mm'],
        power_retired_internal_cable_connectors=['I_J2', 'P_J101', 'P_J106'],
        power_retired_internal_return_studs=['P_J20', 'P_J21'],
        power_retired_connector_terminal_opens=9,
        power_retired_terminal_opens_this_pass=6,
        power_retained_interface_header_pin_pairs=None,
        power_final_physical_interface_manifest_complete=False,
        power_U20_local_cell_regrouped=True, power_U20_local_route_sections=17,
        power_U20_local_connections_closed=16,
        power_U20_bulk_input_output_and_return_network_complete=False,
        power_U20_configuration_enable_and_feedback_top_complete=False,
        power_U20_and_AUX_local_placement_requires_repair=True,
        power_U20_placement_remaining_scope='Bulk input/output return topology and feedback/enable access; AUX remains unregrouped',
        power_U20_boot_capacitor_substitution='P_C201: TDK C1005X7R1H104K050BB, 100nF 50V X7R 0402',
        power_internal_return_bar_replacement_qualified=False,
        power_legacy_return_bar_assembly_requires_revision=True,
        power_local_filled_planes=2, power_local_plane_contacts_preserved=True,
        power_existing_U23_planes_unchanged=True, power_sense_reference_projection_preserved=True,
        power_copper_all_layers_visually_reviewed=True, power_local_buck_detail_visually_reviewed=True,
        fabrication_released=False, goal_complete=False)
    status['next_required_design_work'] = [
        'Complete U20 bulk input/output, FSEL/MODE/enable, feedback top and quiet/force returns',
        'Replace former P_J20/P_J21 return-bar functions with qualified analog/digital current-return paths',
        'Revise legacy return bars, harness/support CAD and final physical interface manifest after internal-port retirement',
        'Regroup AUX and remaining critical circuits; audit every terminal before further internal-port removal',
        *[s for s in status['next_required_design_work'] if not s.startswith('Regroup U20, AUX')]]
    out = STAGING / 'two-board-fabrication-status-18'
    out.mkdir(exist_ok=False)
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(dict(bindings=count, power_opens=2486, signal_opens=251,
                          physical_connections_added=16, retired_terminal_opens=6, fabrication_released=False)))


if __name__ == '__main__':
    run()
