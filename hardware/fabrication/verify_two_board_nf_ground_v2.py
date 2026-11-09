"""Bind the checked startup-routing candidate and its review artifacts."""
import json
import re
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

OUT=STAGING/'two-board-power-nf-logic-ground-native-02'


def run():
    target=OUT/'final-review.json';assert not target.exists()
    reports=[OUT/'review.json',OUT/'nf-logic-ground-routing.json',OUT/'nf-logic-ground-review.json',OUT/'visual-review.json',
        OUT/'plots/native-plots.json',*sorted((OUT/'plots').glob('*-render.json')),
        STAGING/'two-board-power-nf-logic-detours-native-01/final-review.json',
        STAGING/'two-board-power-routing-inputs-nf-logic-ground-02/capture.json',
        STAGING/'two-board-power-nf-logic-ground-filled-03/local-plane-fill.json',
        STAGING/'two-board-nf-logic-ground-plan-02/plan.json',
        STAGING/'two-board-nf-ground-refill-diagnosis-01/native-comparison.json',
        STAGING/'two-board-nf-logic-reference-survey-02/survey.json']
    hashes={};bindings=0
    for report in reports:
        data=json.loads(report.read_text())
        for key in ['source_sha256','artifact_sha256']:
            for name,h in data.get(key,{}).items():
                path=Path(name)
                if not path.is_absolute():path=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/path
                if path not in hashes:hashes[path]=sha(path)
                assert hashes[path]==h,(report,name);bindings+=1
    native=json.loads((OUT/'review.json').read_text());audit=json.loads((OUT/'nf-logic-ground-review.json').read_text())
    inventory=json.loads(reports[-1].read_text());visual=json.loads((OUT/'visual-review.json').read_text())
    assert native['opens']==audit['new_opens']==inventory['native_board_opens']==2130
    assert audit['closed_connections']==14 and len(audit['retained_reference_checks'])==1954
    assert all(c['uncovered_mm2']<1e-6 for c in audit['new_reference_checks'])
    assert audit['all_eleven_supply_planes_unchanged'] and audit['quiet_network_fields_preserved']==7
    assert len(audit['repaired_pad_centers'])==26 and inventory['selected_open_pads']==118 and inventory['uncovered_pad_centers']==0
    assert len(audit['quiet_returns'])==7 and all(q['star_only_main_return'] for q in audit['quiet_returns'])
    assert len(visual['views_inspected'])==12 and visual['inspection_complete']
    old=STAGING/'two-board-fabrication-status-50/final-verification.json';checkpoint=json.loads(old.read_text())
    for name,h in checkpoint['documentation_snapshot_sha256'].items():assert sha(REPO/name)==h,name
    links=[]
    for doc in [OUT/'README.md']:
        for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
            if '://' in link or link.startswith('#'):continue
            dest=(doc.parent/link.split('#')[0]).resolve();assert dest.exists(),(doc,link);links.append(str(dest.relative_to(REPO)))
    sources=[Path(__file__),*reports,OUT/'README.md',old]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},verified_bindings=bindings,
        local_documentation_links_checked=len(links),working_candidate='TBP58-CANDIDATE',selected_checkpoint='TBP50',
        power_opens=2130,signal_opens=251,closed_connections=14,retained_reference_checks=1954,
        selected_nf_missing_joins=inventory['missing_selected_joins'],selected_nf_uncovered_pad_centers=0,prior_checkpoint_documentation_unchanged=True,
        fabrication_released=False,goal_complete=False)
    target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))


if __name__=='__main__':run()
