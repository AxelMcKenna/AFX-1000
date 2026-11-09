"""Bind the reviewed NF ground and logic candidates without promoting a release."""
import json
import re
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    prior=STAGING/'two-board-power-startup-controls-native-04/final-review.json'
    old=STAGING/'two-board-fabrication-status-50/final-verification.json'
    for name,h in json.loads(old.read_text())['documentation_snapshot_sha256'].items():
        assert sha(REPO/name)==h,name
    for suffix,rev,opens,closed in [('ground',55,2158,7),('routes',56,2152,6)]:
        out=STAGING/f'two-board-power-nf-logic-{suffix}-native-01'
        manifest='nf-logic-ground-routing.json' if suffix=='ground' else 'nf-logic-routing.json'
        audit_name='nf-logic-ground-review.json' if suffix=='ground' else 'nf-logic-review.json'
        reports=[prior,out/manifest,out/audit_name,out/'review.json',out/'visual-review.json',out/'plots/native-plots.json',
                 STAGING/f'two-board-power-nf-logic-{suffix}-filled-01/local-plane-fill.json',
                 STAGING/f'two-board-power-routing-inputs-nf-logic-{suffix}-01/capture.json',
                 *sorted((out/'plots').glob('*-render.json'))]
        if suffix=='routes':
            reports.extend([STAGING/'two-board-startup-connectivity-survey-10/inventory.json',STAGING/'two-board-startup-reference-access-05/survey.json'])
        else:reports.append(STAGING/'two-board-startup-reference-access-04/survey.json')
        hashes={};bindings=0
        for report in reports:
            data=json.loads(report.read_text())
            for key in ['source_sha256','artifact_sha256']:
                for name,h in data.get(key,{}).items():
                    path=Path(name)
                    if not path.is_absolute():path=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/path
                    if path not in hashes:hashes[path]=sha(path)
                    assert hashes[path]==h,(report,name);bindings+=1
        native=json.loads((out/'review.json').read_text());audit=json.loads((out/audit_name).read_text())
        visual=json.loads((out/'visual-review.json').read_text())
        assert native['opens']==opens and audit['closed_connections']==closed
        assert native['geometry_findings']==native['schematic_parity_findings']==0
        assert visual['inspection_complete'] and len(visual['views_inspected'])==(9 if suffix=='ground' else 4)
        links=[]
        for link in re.findall(r'\]\(([^)]+)\)',(out/'README.md').read_text()):
            if '://' in link or link.startswith('#'):continue
            dest=(out/link.split('#')[0]).resolve();assert dest.exists(),link;links.append(str(dest.relative_to(REPO)))
        result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,out/'README.md',old]},
                    verified_bindings=bindings,local_documentation_links_checked=len(links),working_candidate=f'TBP{rev}-CANDIDATE',
                    selected_checkpoint='TBP50',power_opens=opens,signal_opens=251,closed_connections=closed,
                    prior_checkpoint_documentation_unchanged=True,fabrication_released=False,goal_complete=False)
        target=out/'final-review.json'
        with target.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        prior=target
        print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))


if __name__=='__main__':run()
