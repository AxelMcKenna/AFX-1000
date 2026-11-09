"""Bind the checked access repair, native geometry, surveys and inspected views."""
import json
import re
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

OUT=STAGING/'two-board-power-startup-access-native-02'


def run():
    target=OUT/'final-review.json'
    assert not target.exists()
    reports=[OUT/n for n in ['review.json','startup-access-routing.json','startup-access-review.json','visual-review.json','plots/native-plots.json']]
    reports += [OUT/'plots'/f'{p}-render.json' for p in ['startup-access-full','startup-master-full','startup-master-transition']]
    reports += [STAGING/p for p in [
        'two-board-power-routing-inputs-startup-access-02/capture.json',
        'two-board-power-startup-access-filled-02/local-plane-fill.json',
        'two-board-startup-access-plan-03/plan.json',
        'two-board-startup-access-plan-02/plan.json',
        'two-board-startup-access-plan-01/plan.json',
        'two-board-startup-connectivity-survey-08/inventory.json',
        'two-board-startup-reference-access-02/survey.json']]
    bindings=0;hashes={}
    for report in reports:
        data=json.loads(report.read_text())
        for key in ['source_sha256','artifact_sha256']:
            for name,h in data.get(key,{}).items():
                path=Path(name)
                if not path.is_absolute():path=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/path
                if path not in hashes:hashes[path]=sha(path)
                assert hashes[path]==h,(report,name)
                bindings+=1
    native=json.loads((OUT/'review.json').read_text())
    audit=json.loads((OUT/'startup-access-review.json').read_text())
    inventory=json.loads(reports[-2].read_text());survey=json.loads(reports[-1].read_text())
    visual=json.loads((OUT/'visual-review.json').read_text())
    assert native['opens']==audit['new_opens']==inventory['native_board_opens']==2167
    assert audit['all_native_groups_preserved'] and audit['closed_connections']==0
    assert len(audit['verified_launch_corridors'])==21
    assert len(audit['retained_reference_checks'])==1622 and len(audit['new_reference_checks'])==14
    assert all(c['uncovered_mm2']<1e-6 for c in audit['new_reference_checks'])
    assert audit['all_eleven_supply_planes_unchanged'] and audit['quiet_network_fields_preserved']==7
    assert survey['covered_pads']==65 and survey['uncovered_pads']==10
    assert inventory['selected_missing_joins']==53
    assert len(visual['views_inspected'])==13 and visual['inspection_complete']
    old=STAGING/'two-board-fabrication-status-50/final-verification.json'
    for name,h in json.loads(old.read_text())['documentation_snapshot_sha256'].items():assert sha(REPO/name)==h,name
    doc=OUT/'README.md';links=[]
    for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
        if '://' in link or link.startswith('#'):continue
        dest=(doc.parent/link.split('#')[0]).resolve()
        assert dest.exists(),link
        links.append(str(dest.relative_to(REPO)))
    sources=[Path(__file__),*reports,doc,old]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},verified_bindings=bindings,
        local_documentation_links_checked=len(links),working_candidate='TBP53-CANDIDATE',selected_checkpoint='TBP50',
        power_opens=2167,signal_opens=251,closed_connections=0,verified_launch_corridors=21,
        repaired_pad_centers=12,remaining_uncovered_selected_pad_centers=10,
        prior_checkpoint_documentation_unchanged=True,fabrication_released=False,goal_complete=False)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))


if __name__=='__main__':run()
