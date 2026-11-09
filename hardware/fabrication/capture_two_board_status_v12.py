"""Bind verified U23 local routing, declared moves and the boot substitution."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-buck-local-native-01'
    previous=STAGING/'two-board-fabrication-status-11/status.json'
    reports=[power/n for n in ['review.json','circuit-audit.json','buck-local-routing.json','buck-local-audit.json',
                              'rejected-source-net-status.json','plots/native-plots.json','plots/preview-render.json','plots/visual-review.json']]
    reports.extend([previous,STAGING/'two-board-power-routing-inputs-2535-buck-local/capture.json',
                    STAGING/'two-board-signal-routed-native-03/review.json'])
    count=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                count+=1
    audit=json.loads((power/'buck-local-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    rejected=json.loads((power/'rejected-source-net-status.json').read_text())
    assert audit['new_opens']==native['opens']==2535 and audit['connections_closed']==16
    assert audit['components']==native['placed_electrical_parts']==1088 and audit['footprints']==1103
    assert audit['unchanged_complete_pin_net_map'] and audit['all_previous_native_connection_groups_preserved']==3287
    assert audit['added_segments']==22 and audit['added_vias']==0
    assert audit['geometry_findings']==audit['parity_findings']==audit['erc_errors']==0
    assert rejected['now_fully_connected']==8 and rejected['still_incomplete']==44
    status=json.loads(previous.read_text())
    for key in ['power_moved_critical_cell_footprints','power_moved_native_pad_instances']:
        status.pop(key,None)
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2535,
        power_copper_segments=2116,power_copper_vias=124,power_connections_closed_this_pass=16,
        power_buck_U23_local_route_sections=17,power_buck_U23_added_tracks=22,power_buck_U23_added_vias=0,
        power_moved_footprints_this_pass=4,power_replaced_footprints_this_pass=1,power_changed_pad_instances_this_pass=13,
        power_boot_capacitor_substitution='P_C221: TDK C1005X7R1H104K050BB, 100nF 50V X7R 0402',
        power_buck_U23_feedback_region_repacked=True,power_buck_U23_boot_paths_mm=[2.017,1.786],
        power_buck_U23_power_loop_qualified=False,power_boot_return_internal_pin_reconciliation_pending=True,
        power_all_retained_copper_objects_unchanged=True,power_remaining_pin_net_map_unchanged=True,
        power_previous_native_connection_groups_preserved=3287,power_moved_courtyard_context_findings=0,
        power_all_vias_screened=124,power_minimum_all_via_drill_to_SMD_mm=audit['minimum_all_via_drill_to_SMD_mm'],
        power_copper_all_layers_visually_reviewed=True,power_local_buck_detail_visually_reviewed=True,
        power_remaining_opens_on_originally_rejected_source_nets=rejected['remaining_native_opens_on_these_nets'],
        fabrication_released=False,goal_complete=False)
    old=status['next_required_design_work']
    status['next_required_design_work']=[
        'Complete U23 output capacitors/sense, FSEL/MODE, enable and the input/AGND/PGND network with appropriate plane access',
        'Reconcile BOOT-return pin 13 internal SW connection with the final schematic/layout without an unnecessary external loop',
        'Route N_U28/N_C67 local bypass after their paired relocation',
        *[s for s in old if not s.startswith('Optimize U23 feedback/BP5/AGND placement')]]
    out=STAGING/'two-board-fabrication-status-12';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2535,signal_opens=251,connections_closed=16,fabrication_released=False)))


if __name__=='__main__':run()
