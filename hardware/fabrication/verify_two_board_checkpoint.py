"""Recheck selected status bindings and local documentation link targets."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--status',required=True)
    args=parser.parse_args()
    assert all(c.isalnum() or c in '-_' for c in args.status)
    path=STAGING/args.status/'status.json'
    output=path.parent/'final-verification.json'
    assert not output.exists()
    status=json.loads(path.read_text())
    count=0
    def verify(report, data):
        nonlocal count
        for field in ['source_sha256','artifact_sha256']:
            for name, digest in data.get(field,{}).items():
                target=Path(name)
                if not target.is_absolute():
                    target=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/target
                assert sha(target)==digest,(report,name)
                count+=1
    verify(path,status)
    for name in status['source_sha256']:
        report=REPO/name
        if report.suffix=='.json':verify(report,json.loads(report.read_text()))
    power=(REPO/status['power_project']).parent
    refs=json.loads((REPO/status['power_reference_review']).read_text())
    assert refs['retained_reference_complete'] and refs['new_reference_complete']
    assert refs['own_quiet_reference_preserved'] and refs['legacy_incomplete_paths_preserved']
    docs=[REPO/'README.md',REPO/'hardware/README.md',REPO/'hardware/fabrication/README.md',
          power/'README.md',(REPO/status['power_startup_connectivity_survey']).parent/'README.md']
    checked=0
    for doc in docs:
        for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
            target=target.strip('<>')
            url=urlsplit(target)
            if url.scheme or url.netloc or not url.path:continue
            local=(doc.parent/unquote(url.path)).resolve()
            assert local.exists(),(doc,target)
            checked+=1
    result=dict(source_sha256={str(Path(__file__).relative_to(REPO)):sha(Path(__file__))},
                status_sha256=sha(path),verified_status_and_direct_report_bindings=count,
                documentation_snapshot_sha256={str(p.relative_to(REPO)):sha(p) for p in docs},
                local_documentation_links_checked=checked,selected_revision=status['revision'],
                power_opens=status['power_opens'],signal_opens=status['signal_opens'],
                reference_regressions=0,new_reference_gaps=0,
                legacy_incomplete_reference_paths=status['power_legacy_incomplete_reference_paths_preserved'],
                fabrication_released=False,goal_complete=False)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','documentation_snapshot_sha256']}))


if __name__=='__main__':
    run()
