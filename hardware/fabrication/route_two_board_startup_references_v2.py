"""Coordinate startup PG reroutes and local adjacent-reference extensions."""
import json,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
BASE=STAGING/'two-board-power-support-references-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2210-support-references-01/capture.json'
PLAN=STAGING/'two-board-startup-reference-plan-02/routes.json'
QUIET=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json'
OUT=STAGING/'two-board-power-startup-references-02'


def polys(g):
    parts=[g] if g.geom_type=='Polygon' else list(g.geoms)
    return [dict(outer=list(p.exterior.coords)[:-1],holes=[list(h.coords)[:-1] for h in p.interiors]) for p in parts]


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text());qs=json.loads(QUIET.read_text())['quiet_ground_islands']
    for d in [c,p]:
        for name,h in d['source_sha256'].items():
            f=Path(name);assert sha(f if f.is_absolute() else REPO/f)==h,name
    old={o['uuid']:o for o in c['objects']};retire=set(p['retired_objects'])
    assert len(retire)==10 and all(old[u]['kind'] in ['PCB_TRACK','PCB_VIA'] for u in retire)
    assert sum(old[u]['kind']=='PCB_VIA' for u in retire)==1
    objects=[o for o in c['objects'] if o['uuid'] not in retire]
    routing.SIGNAL_LAYERS=tuple(c['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(dict(c,objects=objects,zones=[]));routes=p['routes'];vias=p['vias']
    # All new tracks are checked on their actual copper layer. Inner ground
    # fills are intentionally refilled around the one In6 signal route.
    for r in routes:
        line=LineString(r['path_mm']);assert screen.legal(r['net'],r['layer'],r['path_mm']),r['label']
        screen.added.append((r['net'],r['layer'],line))
    for v in vias:
        assert screen.via_legal(v['net'],v['position_mm']),v
        screen.vias.append((v['net'],v['position_mm']))
    uid=lambda text:str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPSTARTUPREF02:'+sha(CAP)+':'+text))
    for i,v in enumerate(vias):
        v['uuid']=uid(f'via:{i}');v['size_mm']=.6;v['drill_mm']=.3
        objects.append(dict(uuid=v['uuid'],net=v['net'],kind='PCB_VIA',position_mm=v['position_mm'],width_mm=.6,drill_mm=.3,
                            layers={l:polys(Point(v['position_mm']).buffer(.3,quad_segs=64)) for l in c['copper_layers']}))
    zs={z['uuid']:z for z in c['zones']};regions={u:shape(z['authored_outline']) for u,z in zs.items()}
    owned={q['ref']:{v['uuid'] for v in [q['star_via'],*q['control_vias'],*q['extra_quiet_vias']]} for q in qs}
    qzones={q['ref']:{zs[u]['layer']:u for u in q['zone_uuids']} for q in qs}
    ext={}
    for r in p['reference_extensions']:
        u=qzones[r['owner']][r['layer']]
        ext.setdefault(u,[]).append(LineString(r['path_mm']).buffer(p['extension_radius_mm'],quad_segs=64))
    clipped={}
    for u,parts in ext.items():
        owner=next(q['ref'] for q in qs if u in q['zone_uuids']);g=unary_union(parts);layer=zs[u]['layer']
        for o in objects:
            if o['layers'].get(layer) and (o['net']!='PWR_AGND' or o['uuid'] not in owned[owner]):
                g=g.difference(shape(o['layers'][layer]).buffer(.215,quad_segs=64))
        clipped[u]=g
    for u,g in clipped.items():
        for v,h in clipped.items():
            if v!=u and zs[u]['layer']==zs[v]['layer']:
                assert g.distance(h)>=.215-1e-6,('Overlapping proposed reference owners',u,v)
    for u,z in zs.items():
        if z['net']!='PWR_AGND':continue
        g=regions[u]
        if u in clipped:g=unary_union([g,clipped[u]])
        for v,extension in clipped.items():
            if v!=u and zs[v]['layer']==z['layer']:g=g.difference(extension.buffer(.215,quad_segs=64))
        regions[u]=g
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());codes={str(n[2]):int(n[1]) for n in children(board,'net')}
    board[:]=[n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in retire)]
    for i,r in enumerate(routes):
        r['segment_uuids']=[]
        for j,(start,end) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
            ident=uid(f'track:{i}:{j}');r['segment_uuids'].append(ident)
            board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),r['width_mm']],
                          [a('layer'),r['layer']],[a('net'),codes[r['net']]],[a('uuid'),ident]])
    for v in vias:
        board.append([a('via'),[a('at'),*v['position_mm']],[a('size'),.6],[a('drill'),.3],
                      [a('layers'),'F.Cu','B.Cu'],[a('net'),codes[v['net']]],[a('uuid'),v['uuid']]])
    affected={l:[] for l in c['copper_layers']}
    for u in retire:
        for l,ps in old[u]['layers'].items():
            if ps:affected[l].append(shape(ps).buffer(.7))
    for v in vias:
        for l in c['copper_layers']:affected[l].append(Point(v['position_mm']).buffer(1.))
    for r in routes:affected[r['layer']].append(LineString(r['path_mm']).buffer(.7))
    diagnosis_path=STAGING/'two-board-startup-refill-diagnosis-01/geometry-comparison.json'
    diagnosis=json.loads(diagnosis_path.read_text())
    extra_refill={row['uuid'] for row in diagnosis['changes']}
    assert extra_refill=={'787e0385-5c4c-5b8f-9a2a-017054f7da0e','cfbe2e9d-6fef-5185-a803-f1564fa418df'}
    assert all(row['boundary_hausdorff_mm']<=2e-6 for row in diagnosis['changes'])
    edited=[];refilled=[]
    for z in children(board,'zone'):
        u=str(first(z,'uuid')[1]);changed=regions[u].symmetric_difference(shape(zs[u]['authored_outline'])).area>1e-7
        g=regions[u].simplify(.00001,preserve_topology=True)
        if changed:
            assert g.geom_type=='Polygon' and g.is_valid,(u,g.geom_type,[x.area for x in getattr(g,'geoms',[])])
            z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='polygon')]
            z.extend([[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in [g.exterior,*g.interiors]])
            edited.append(dict(uuid=u,layer=zs[u]['layer'],outer_mm=list(g.exterior.coords),holes_mm=[list(h.coords) for h in g.interiors]))
        if changed or u in extra_refill or any(g.intersects(item) for item in affected[zs[u]['layer']]):
            z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')];refilled.append(u)
    OUT.mkdir();sources=[]
    for path in BASE.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(BASE)
        if rel.parts[0] in ['libraries','symbols'] or len(rel.parts)==1 and (path.suffix=='.kicad_sch' or path.name in ['power_protection.kicad_pcb','power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table','sym-lib-table','expected-circuit.json','symbol-paths.json']):
            dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);sources.append(path)
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    sch=OUT/'power_protection.kicad_sch';tree=read_sexpr(sch.read_text());first(first(tree,'title_block'),'rev')[1]='TBP48-CANDIDATE';sch.write_text(sexpr(tree)+'\n')
    sources=[Path(__file__),CAP,PLAN,QUIET,diagnosis_path,STAGING/'two-board-startup-refill-diagnosis-01/native-comparison.json',*[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_layer_detours.py','route_two_board_power_local_v2.py','route_two_board_power_local.py']],*sources]
    report=dict(source_sha256={str(f.relative_to(REPO)):sha(f) for f in sources},retired_objects=sorted(retire),routes=routes,vias=vias,
                reference_extensions=p['reference_extensions'],additional_native_refill_zones=sorted(extra_refill),edited_zone_outlines=edited,refilled_existing_zones=refilled,
                added_tracks=sum(len(r['segment_uuids']) for r in routes),added_vias=2,expected_closed_connections=0,
                native_validation_pending=True,reference_and_quiet_topology_pending=True,fabrication_released=False)
    (OUT/'startup-reference-routing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(tracks=report['added_tracks'],vias=2,retired=len(retire),edited_zones=len(edited),refilled=len(refilled))))


if __name__=='__main__':run()
