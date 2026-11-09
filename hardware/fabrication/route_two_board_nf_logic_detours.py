"""Author the screened TBP57 startup-control routing candidate."""
import json
import shutil
import uuid
from pathlib import Path
from shapely.geometry import Point, LineString
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
BASE=STAGING/'two-board-power-nf-logic-routes-native-01'
CAP=STAGING/'two-board-power-routing-inputs-nf-logic-routes-01/capture.json'
from hardware.fabrication.route_nf_surface import shape

PLAN=STAGING/'two-board-nf-logic-detour-plan-01/plan.json'
OUT=STAGING/'two-board-power-nf-logic-detours-01'


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
    for data in [c,p]:
        for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    assert p['expected_closed_connections']==len(p['joins']) and p['joins']
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    codes={str(n[2]):int(n[1]) for n in children(board,'net')}
    uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBP57:'+sha(PLAN)+':'+s))
    for i,r in enumerate(p['routes']):
        r['segment_uuids']=[]
        for j,(start,end) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
            u=uid(f'track:{i}:{j}');r['segment_uuids'].append(u)
            board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),r['width_mm']],[a('layer'),r['layer']],[a('net'),codes[r['net']]],[a('uuid'),u]])
    for i,v in enumerate(p['vias']):
        v['uuid']=uid(f'via:{i}')
        board.append([a('via'),[a('at'),*v['position_mm']],[a('size'),v['size_mm']],[a('drill'),v['drill_mm']],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
    affected={l:[] for l in c['copper_layers']}
    for r in p['routes']:affected[r['layer']].append(LineString(r['path_mm']).buffer(.8))
    for v in p['vias']:
        for l in affected:affected[l].append(Point(v['position_mm']).buffer(1.))
    zmap={z['uuid']:z for z in c['zones']};refill=[]
    for z in children(board,'zone'):
        u=str(first(z,'uuid')[1]);row=zmap[u];g=shape(row['authored_outline'])
        if any(g.intersects(x) for x in affected[row['layer']]):
            z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refill.append(u)
    OUT.mkdir();sources=[Path(__file__),CAP,PLAN,REPO/'hardware/fabrication/plan_two_board_startup_controls.py',REPO/'hardware/fabrication/route_nf_surface.py']
    for src in BASE.rglob('*'):
        if not src.is_file():continue
        rel=src.relative_to(BASE)
        if rel.parts[0] in ['libraries','symbols'] or len(rel.parts)==1 and (src.suffix=='.kicad_sch' or src.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json']):
            target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target);sources.append(src)
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    path=OUT/'power_protection.kicad_sch';sch=read_sexpr(path.read_text());first(first(sch,'title_block'),'rev')[1]='TBP57-CANDIDATE';path.write_text(sexpr(sch)+'\n')
    result=dict(p,source_sha256={str(f.relative_to(REPO)):sha(f) for f in sources},refilled_existing_zones=refill,
        added_tracks=sum(len(r['segment_uuids']) for r in p['routes']),added_vias=len(p['vias']),
        previous_opens=c['native_uncapped_opens'],expected_opens=c['native_uncapped_opens']-len(p['joins']),
        all_existing_authored_copper_preserved=True,startup_functionally_verified=False,fabrication_released=False)
    (OUT/'nf-logic-detour-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['added_tracks','added_vias','expected_closed_connections','expected_opens','refilled_existing_zones']}))


if __name__=='__main__':run()
