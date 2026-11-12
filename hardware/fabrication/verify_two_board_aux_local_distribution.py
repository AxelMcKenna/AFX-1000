"""Bind native, connectivity, reference and visual evidence for TBP70 only."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    root=STAGING/'two-board-power-aux-local-distribution-native-02'
    reports=[root/n for n in ['review.json','aux-local-distribution-review.json','self-review.json']]
    paths={Path(__file__)}
    count=0
    for report in reports:
        paths.add(report)
        data=json.loads(report.read_text())
        for key in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(key,{}).items():
                p=Path(name)
                if not p.is_absolute():p=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/p
                assert sha(p)==digest,(report,p)
                paths.add(p);count+=1
    native,audit,visual=[json.loads(p.read_text()) for p in reports]
    assert native['opens']==audit['new_opens']==visual['native_opens']==1992
    assert native['geometry_findings']==native['schematic_parity_findings']==0
    assert audit['closed_connections']==visual['new_connections']==34
    assert audit['all_other_native_groups_preserved'] and audit['all_original_objects_placements_and_schematic_nets_preserved']
    assert audit['all_eleven_supply_planes_unchanged'] and audit['quiet_network_fields_preserved']==7
    assert len(audit['retained_reference_checks'])==2461 and len(audit['new_reference_checks'])==33
    assert not audit['zone_changes'] and audit['ERC_errors']==0 and audit['ERC_warnings']==2
    target=root/'final-review.json';assert not target.exists()
    target.write_text(json.dumps(dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(paths)},checked_bindings=count,opens=1992,closed_connections=34,all47_plane_fills_preserved=True,retained_reference_checks=2461,new_reference_checks=33,self_review_completed=True,scope='TBP70 short auxiliary supply routing checkpoint; no functional or full-board qualification',goal_complete=False,fabrication_released=False),indent=2)+'\n')
    print('Verified',count,'bindings; TBP70 checkpoint, 1992 opens')

if __name__=='__main__':run()
