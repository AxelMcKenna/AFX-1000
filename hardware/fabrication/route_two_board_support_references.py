"""Repair four support-route reference gaps without changing vias or planes."""
import json
import shutil
import uuid
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_nf_surface import shape
BASE=STAGING/'two-board-power-digital-return-native-03'
CAP=STAGING/'two-board-power-routing-inputs-2210-digital-return-03/capture.json'
DIAG=STAGING/'two-board-digital-return-plan-01/retained-reference-diagnosis.json'
OUT=STAGING/'two-board-power-support-references-01'
PATHS=[
    [[135.06,121.275],[135.56,121.275],[135.66,120.475]],
    [[138.05,124.8],[137.6,125.1],[137.05,124.8]],
    [[138.05,124.8],[138.05,124.2],[137.25,124.2]],
    [[138.81,125.5875],[138.01,126.3875],[137.95,127.3],[138.01,128.0875]],
]


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text());diag=json.loads(DIAG.read_text())
    for name,digest in cap['source_sha256'].items():
        path=Path(name);assert sha(path if path.is_absolute() else REPO/path)==digest
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    codes={str(n[2]):int(n[1]) for n in children(board,'net')}
    objects={o['uuid']:o for o in cap['objects']}
    retired=set();routes=[];checks=[]
    for index,(rec,path) in enumerate(zip(diag['gaps'][:4],PATHS)):
        old=rec['route'];net=old['net'];layer=old['layer'];width=old['width_mm']
        assert all(abs(a-b)<1e-6 for p,q in [(path[0],old['path_mm'][0]),(path[-1],old['path_mm'][-1])] for a,b in zip(p,q))
        for u,(start,end) in zip(old['segment_uuids'],zip(old['path_mm'],old['path_mm'][1:])):
            o=objects[u]
            assert o['kind']=='PCB_TRACK' and o['net']==net and list(o['layers'])==[layer] and o['width_mm']==width
            assert all(abs(a-b)<1e-6 for p,q in [(o['position_mm'],start),(o['end_mm'],end)] for a,b in zip(p,q))
            retired.add(u)
        copper=LineString(path).buffer(width/2)
        clearances=[]
        for o in cap['objects']:
            if o['net']!=net and o['layers'].get(layer):
                distance=copper.distance(shape(o['layers'][layer]));assert distance>=.21-1e-7,(index,o['uuid'],distance)
                clearances.append(distance)
            drill=o.get('drill_mm',0);radius=(max(drill) if isinstance(drill,list) else drill)/2
            if radius and o['net']!=net:assert copper.distance(Point(o['position_mm']))-radius>=.15-1e-7
        owner='E_U17' if net!='PWR_5V_DIG_SRC' else None
        fields=[z for z in cap['zones'] if z['net']=='PWR_AGND' and z['layer']==rec['reference_layer']
                and (owner is None or z['uuid']=='f4ced2b6-1129-5f08-9964-81793db22150')]
        reference=unary_union([shape(z['polygons']) for z in fields]);projection=copper
        for o in cap['objects']:
            if o['net']==net and o['kind']=='PCB_VIA':
                projection=projection.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
        missing=projection.difference(reference.buffer(.0015)).area
        assert missing<1e-6,(index,missing)
        ids=[]
        for j,(start,end) in enumerate(zip(path,path[1:])):
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPSUPPORTREF01:'+sha(CAP)+f':{index}:{j}'));ids.append(uid)
            board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),width],
                          [a('layer'),layer],[a('net'),codes[net]],[a('uuid'),uid]])
        routes.append(dict(label=rec['label']+f' reference repair {index+1}',net=net,layer=layer,width_mm=width,
                           path_mm=path,segment_uuids=ids,owner=owner,reference_layer=rec['reference_layer'],
                           previous_route=old,reference_zone_uuids=[z['uuid'] for z in fields]))
        checks.append(dict(label=routes[-1]['label'],old_missing_mm2=rec['missing_mm2'],
                           new_missing_mm2=missing,minimum_foreign_copper_clearance_mm=min(clearances),
                           length_mm=LineString(path).length))
    assert len(retired)==6 and sum(len(r['segment_uuids']) for r in routes)==9
    board[:]=[n for n in board if not(isinstance(n,list) and n and n[0]=='segment' and str(first(n,'uuid')[1]) in retired)]
    OUT.mkdir();sources=[]
    for path in BASE.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(BASE)
        if rel.parts[0] in ['libraries','symbols'] or len(rel.parts)==1 and (path.suffix=='.kicad_sch' or path.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json']):
            dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);sources.append(path)
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    sch=OUT/'power_protection.kicad_sch';tree=read_sexpr(sch.read_text());first(first(tree,'title_block'),'rev')[1]='TBP47-CANDIDATE';sch.write_text(sexpr(tree)+'\n')
    sources=[Path(__file__),CAP,DIAG,REPO/'hardware/fabrication/route_nf_surface.py',*sources]
    report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},retired_objects=sorted(retired),
                routes=routes,geometry_preflight=checks,added_tracks=9,retired_tracks=6,added_vias=0,
                modified_zones=0,moved_footprints=0,expected_closed_connections=0,
                native_validation_pending=True,fabrication_released=False)
    (OUT/'support-reference-routing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(repaired_paths=4,added_tracks=9,retired_tracks=6,modified_zones=0)))


if __name__=='__main__':run()
