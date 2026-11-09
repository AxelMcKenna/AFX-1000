"""Author a paired multilayer inlet corridor for native and current-path review."""
import copy,json,math,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,box
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-fast-ov-return-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2383-fast-ov-return-02/capture.json'
OUT=STAGING/'two-board-power-inlet-corridor-01'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for p,h in cap['source_sha256'].items():assert sha(REPO/p)==h,p
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    codes={str(n[2]):int(n[1]) for n in children(board,'net')}
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPINLET01:'+sha(CAP)+':'+label))
    routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(dict(cap,zones=[]));changed=set();vias=[]
    dc='PWR_DC_IN';gnd='PWR_AGND'
    source_sites=[[189.95,112.75],[191.5,112.8],[192.1,112.8],[189.5,114.8]]
    inlet_sites=[[x,y] for x in [280.5,281.2,281.9,282.6] for y in [20.8,21.5,22.2]]
    for label,sites in [('fuse-feed',inlet_sites),('source-bank',source_sites)]:
        for i,p in enumerate(sites):
            assert screen.via_legal(dc,p),(label,p)
            u=uid(label+str(i));screen.vias.append((dc,p))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[dc]],[a('uuid'),u]])
            vias.append(dict(uuid=u,label=label,net=dc,position_mm=p,size_mm=.6,drill_mm=.3))
            for z in cap['zones']:
                if Point(p).distance(routing.shape(z['authored_outline']))<.61:changed.add(z['uuid'])
    edge=routing.shape(cap['outline']).buffer(-.51,join_style=2)
    mounts=[(o['ref'],Point(o['position_mm']),max(3.6,max(o['drill_mm'])/2+.5)) for o in cap['objects'] if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    assert len(mounts)==15
    common=unary_union([box(8.5,30.5,284,39.5),box(17,30.5,26.5,123),box(17,109,194.1,123)])
    power=unary_union([common,box(274.5,18,284,39.5)])
    ground=unary_union([common,box(281,4.5,292,39.5),box(190,109,200.8,128)])
    newzones=[]
    def prepared(net,layer,g):
        g=g.intersection(edge)
        for ref,p,r in mounts:g=g.difference(p.buffer(r+.31,quad_segs=32))
        for z in cap['zones']:
            if z['layer']==layer:
                old=routing.shape(z['authored_outline'])
                # Avoid overlap with any old zone; retain its authored scope.
                g=g.difference(old.buffer(.21,join_style=2))
        g=g.simplify(.00001,preserve_topology=True)
        assert g.is_valid and g.geom_type=='Polygon',(layer,g.geom_type)
        assert edge.buffer(1e-8).covers(g)
        assert all(g.distance(p)>=r+.30-1e-6 for ref,p,r in mounts)
        return g
    def poly_nodes(g):
        rings=[g.exterior,*g.interiors]
        return [[a('polygon'),[a('pts'),*[[a('xy'),round(x,6),round(y,6)] for x,y in ring.coords[:-1]]]] for ring in rings]
    for label,net,layer,g in [('feed-inner2',dc,'In2.Cu',power),('feed-inner3',dc,'In3.Cu',power),('return-inner4',gnd,'In4.Cu',ground),('return-inner5',gnd,'In5.Cu',ground),('fuse-pad-to-bank',dc,'F.Cu',box(277.3,20.1,283.2,23.5))]:
        g=prepared(net,layer,g);u=uid(label)
        board.append([a('zone'),[a('net'),codes[net]],[a('net_name'),net],[a('layer'),layer],[a('uuid'),u],
            [a('hatch'),a('edge'),.5],[a('connect_pads'),a('yes'),[a('clearance'),.2]],
            [a('min_thickness'),.25],[a('filled_areas_thickness'),a('no')],
            [a('fill'),a('yes'),[a('thermal_gap'),.25],[a('thermal_bridge_width'),.5],[a('island_removal_mode'),0]],*poly_nodes(g)])
        newzones.append(dict(uuid=u,label=label,net=net,layer=layer,outer_mm=list(g.exterior.coords)[:-1],holes_mm=[list(r.coords)[:-1] for r in g.interiors],authored_area_mm2=g.area))
        # Adjacent fills stay unchanged unless their native clearance geometry changes.
        for z in cap['zones']:
            if z['layer']==layer and g.distance(routing.shape(z['authored_outline']))<.211:changed.add(z['uuid'])
    old_source='85d2f33d-203c-5c6d-8918-7fecc35747b8'
    z=next(z for z in children(board,'zone') if str(first(z,'uuid')[1])==old_source)
    old_ring=copy.deepcopy(first(z,'polygon'))
    expanded=box(189.15,112.4,194.1,114.89)
    z[:]=[n for n in z if not(isinstance(n,list) and n and n[0] in ['polygon','filled_polygon'])]
    z.extend(poly_nodes(expanded));changed.add(old_source)
    for q in cap['zones']:
        if q['layer']=='F.Cu' and expanded.distance(routing.shape(q['authored_outline']))<.211:changed.add(q['uuid'])
    for z in children(board,'zone'):
        if str(first(z,'uuid')[1]) in changed:z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','*-review.json','rejected-source-net-status.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';sch=read_sexpr(p.read_text());first(first(sch,'title_block'),'rev')[1]='TBP33';p.write_text(sexpr(sch)+'\n')
    paths=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'fast-ov-return-audit.json',STAGING/'two-board-inlet-feed-survey-01/review.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_power_layer_detours.py','route_two_board_power_local_v2.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},vias=vias,new_zones=newzones,changed_existing_zone_fills=sorted(changed),
        expanded_source_zone=dict(uuid=old_source,old_polygon=old_ring,new_outer_mm=list(expanded.exterior.coords)[:-1]),
        moved_footprints=[],retired_tracks=[],retired_vias=[],added_tracks=0,added_vias=len(vias),circuit_unchanged=True,
        source_bank_total_intended_vias=5,paired_power_layers=['In2.Cu','In3.Cu'],paired_return_layers=['In4.Cu','In5.Cu'],
        native_validation_pending=True,independent_topology_audit_pending=True,current_capacity_and_thermal_verified=False,stack_accepted=False,fabrication_released=False)
    (OUT/'inlet-corridor-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(vias=len(vias),zones=len(newzones),changed_zones=sorted(changed))))

if __name__=='__main__':run()
