"""Adopt the verified internal SW/bootstrap-return model without geometry edits."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-boot-return-native-01'
    previous=STAGING/'two-board-fabrication-status-12/status.json'
    prior=STAGING/'two-board-power-buck-local-native-01'
    reports=[previous,*[power/n for n in ['review.json','circuit-audit.json','boot-return-change.json','boot-return-audit.json','rejected-source-net-status.json']],
             STAGING/'two-board-power-routing-inputs-2533-boot-return/capture.json',
             *[prior/n for n in ['buck-local-audit.json','plots/native-plots.json','plots/preview-render.json','plots/visual-review.json']],
             STAGING/'two-board-signal-routed-native-03/review.json']
    count=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,h in data.get(field,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert p.is_file() and sha(p)==h,(report,name)
                count+=1
    audit=json.loads((power/'boot-return-audit.json').read_text());native=json.loads((power/'review.json').read_text())
    assert audit['native_opens']==native['opens']==2533
    assert audit['all_board_geometry_unchanged'] and audit['complete_pin_partition_restored_by_declared_internal_bridges']
    assert audit['all_native_objects_preserved']==5967 and audit['all_prior_physical_groups_preserved']==3271
    assert audit['geometry_findings']==audit['parity_findings']==audit['erc_errors']==0
    status=json.loads(previous.read_text())
    status.update(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,power/'README.md']},
        verified_direct_source_and_artifact_bindings=count,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),power_opens=2533,
        power_connections_closed_this_pass=0,power_model_only_external_obligations_removed=2,
        power_moved_footprints_this_pass=0,power_replaced_footprints_this_pass=0,power_changed_pad_instances_this_pass=0,
        power_schematic_pin_net_changes_this_pass=4,power_retained_track_net_changes_this_pass=2,
        power_remaining_pin_net_map_unchanged=False,power_all_retained_copper_objects_unchanged=False,
        power_all_retained_copper_geometry_unchanged=True,power_all_component_poses_preserved=True,
        power_pin_partition_equivalent_through_declared_internal_bridges=True,
        power_previous_native_connection_groups_preserved=3271,
        power_boot_return_internal_pin_reconciliation_pending=False,
        power_visual_evidence_reused_from_identical_geometry=str(prior.relative_to(REPO)),
        fabrication_released=False,goal_complete=False)
    status['next_required_design_work']=[s for s in status['next_required_design_work'] if not s.startswith('Reconcile BOOT-return pin 13')]
    out=STAGING/'two-board-fabrication-status-13';out.mkdir(exist_ok=False)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(dict(bindings=count,power_opens=2533,signal_opens=251,physical_connections_added=0,fabrication_released=False)))

if __name__=='__main__':run()
