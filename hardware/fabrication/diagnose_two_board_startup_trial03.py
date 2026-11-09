"""Record why startup trial 03 is unselected, including validator metadata changes."""
import json
from collections import Counter
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr


def run():
    before=STAGING/'two-board-power-support-references-native-01/power_protection.kicad_pcb'
    after=STAGING/'two-board-power-startup-references-native-03/power_protection.kicad_pcb'
    report=after.parent/'startup-reference-routing.json'
    r=json.loads(report.read_text())
    removed=set(r['retired_objects'])
    added={u for rr in r['routes'] for u in rr['segment_uuids']}|{v['uuid'] for v in r['vias']}
    trees=[read_sexpr(p.read_text()) for p in [before,after]]
    fps=[{str(first(f,'uuid')[1]):f for f in children(t,'footprint')} for t in trees]
    duplicate_paths=[]
    for u,f in fps[0].items():
        g=fps[1][u]
        if f==g:continue
        a,b=[Counter(sexpr(n) for n in items) for items in [f,g]]
        diff=b-a
        assert not a-b and sum(diff.values())==1
        path=first(f,'path')
        assert path is not None and diff==Counter({sexpr(path):1})
        duplicate_paths.append(u)
        g.remove(path)
        assert f==g
    def stable(t):
        return [n for n in t if not(isinstance(n,list) and n and (n[0]=='zone' or n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in removed|added))]
    assert stable(trees[0])==stable(trees[1])
    out=STAGING/'two-board-startup-trial03-diagnosis';out.mkdir(exist_ok=False)
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),before,after,report,after.parent/'review.json',REPO/'hardware/fabrication/native_two_board_power.py',REPO/'hardware/fabrication/native_two_board_power_v2.py']},
        duplicate_footprint_path_count=len(duplicate_paths),duplicate_footprint_path_uuids=duplicate_paths,
        all_other_nonrouting_nonzone_syntax_preserved=True,
        cause='The historical native_two_board_power validator appended a second identical instance path to each electrical footprint.',
        next_action='Use native_two_board_power_v2 for the next candidate; retain the strict unchanged-component syntax audit.',
        selected=False,fabrication_released=False)
    (out/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(duplicate_footprint_paths=len(duplicate_paths),all_other_nonrouting_nonzone_syntax_preserved=True)))


if __name__=='__main__':run()
