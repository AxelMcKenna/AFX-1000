"""Apply the two native-ground-informed path repairs without dropping any joins."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha


def run():
    original=STAGING/'two-board-control-corridor-plan-01/plan.json'
    repairs=STAGING/'two-board-control-corridor-repair-plan-01/plan.json'
    out=STAGING/'two-board-control-corridor-plan-02';assert not out.exists()
    p=json.loads(original.read_text());r=json.loads(repairs.read_text())
    for d in [p,r]:
        for n,h in d['source_sha256'].items():assert sha(REPO/n)==h,n
    assert not r['deferred'] and {x['route_index'] for x in r['repairs']}=={7,38}
    for x in r['repairs']:
        route=p['routes'][x['route_index']]
        assert route['net']==x['net'] and route['layer']==x['layer'] and route['path_mm']==x['original_path_mm']
        assert route['path_mm'][0]==x['path_mm'][0] and route['path_mm'][-1]==x['path_mm'][-1]
        route['path_mm']=x['path_mm']
    p['source_sha256'].update({str(f.relative_to(REPO)):sha(f) for f in [Path(__file__),original,repairs]})
    p['native_ground_path_repairs']=r['repairs']
    p['all_original_24_joins_retained']=True
    # Existing length fields describe original screening candidates; avoid
    # implying those estimates include the two subsequent local detours.
    for j in p['joins']:j['initial_screened_length_mm']=j.pop('length_mm')
    out.mkdir();(out/'plan.json').write_text(json.dumps(p,indent=2)+'\n')
    print('Retained all 24 joins; applied two local path repairs.')


if __name__=='__main__':run()
