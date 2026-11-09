"""Coordinated U23 MODE escape repair and local enable/pull-down routing.

Foreign filled planes are explicitly marked for native refill; their saved fill
is removed, never accepted as valid after changing through vias.
"""
import copy,json,math,shutil,uuid
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position,transform_object,mechanical_check
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing
BASE=STAGING/'two-board-power-buck-input-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2511-buck-input/capture.json'
OUT=STAGING/'two-board-power-buck-enable-01'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
MOVE=[301.5,130.6]
MODE_XY=[294.5,129.05]
EN_XY=[295.3,127.525]

def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for n,h in cap['source_sha256'].items():assert sha(REPO/n)==h,n
    control=json.loads((BASE/'buck-control-routing.json').read_text())
    removed={u for r in control['routes'] if r['label'] in ['MODE-front','MODE-back'] for u in r['segment_uuids']}
    removed.update(v['uuid'] for v in control['vias'] if v['net'].endswith('/P03_A_MODE'))
    assert len(removed)==4
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    oldfps={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(oldfps)
    fps['P_R225']=rotate_footprint(fps['P_R225'],MOVE,-90)
    mechanical_check(fps,{'P_R225'},json.loads(PLACEMENT.read_text()))
    for o in cap['objects']:
        if o.get('ref')=='P_R225':assert cap['all_groups'][o['group']]==[o['uuid']]
    cap=copy.deepcopy(cap)
    cap['objects']=[transform_object(o,position(oldfps['P_R225']),MOVE,-90) if o.get('ref')=='P_R225' else o for o in cap['objects'] if o['uuid'] not in removed]
    planes=cap['zones'];assert len(planes)==2 and all(not z['keepout'] and z['polygons'] for z in planes)
    # These two authored zones will be refilled. Ordinary copper remains an
    # immutable obstacle; future keepouts must be handled before using this tool.
    cap['zones']=[]
    routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(cap)
    for o in cap['objects']:
        if o.get('ref')!='P_R225':continue
        for l,ps in o['layers'].items():
            if not ps:continue
            g=routing.shape(ps)
            assert routing.shape(cap['outline']).buffer(-.5).covers(g)
            assert all(g.distance(pt)>r+.01 for _,pt,r in screen.mounts)
            for other in cap['objects']:
                if other.get('ref')=='P_R225' or other['net']==o['net'] or not other['layers'].get(l):continue
                assert g.distance(routing.shape(other['layers'][l]))>=.21,(o['pin'],other.get('ref'))
    board[:]=[n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(first(n,'uuid')[1]) in removed)]
    for i,n in enumerate(board):
        if isinstance(n,list) and n and n[0]=='footprint' and prop(n,'Reference')[2]=='P_R225':board[i]=fps['P_R225']
    removed_fill=0
    for z in children(board,'zone'):
        removed_fill+=len(children(z,'filled_polygon'))
        z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    assert removed_fill==2
    codes={str(n[2]):int(n[1]) for n in children(board,'net')};routes=[];vias=[];refill=[]
    pad=lambda r,p:next(o for o in cap['objects'] if o.get('ref')==r and o.get('pin')==p)
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPENABLE01:'+sha(CAP)+':'+label))
    def route(label,net,layer,points,limit):
        assert LineString(points).length<=limit
        assert screen.legal(net,layer,points),(label,points)
        ids=[]
        for i,(p,q) in enumerate(zip(points,points[1:])):
            u=uid(label+str(i));ids.append(u)
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),u]])
        screen.added.append((net,layer,LineString(points)))
        routes.append(dict(label=label,net=net,layer=layer,width_mm=.2,path_mm=points,length_mm=LineString(points).length,maximum_length_mm=limit,segment_uuids=ids))
    def via(label,net,xy):
        assert screen.via_legal(net,xy),(label,xy)
        u=uid(label)
        board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        vias.append(dict(uuid=u,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for z in planes:
            if z['net']!=net and routing.shape(z['polygons']).distance(Point(xy))<.51:
                refill.append(dict(via_uuid=u,zone_uuid=z['uuid'],layer=z['layer'],net=z['net'],required_clearance_mm=.2))
        screen.vias.append((net,xy))
        for l in cap['copper_layers']:screen.added.append((net,l,Point(xy).buffer(.2)))
    mode=pad('P_U23','2')['net'];en=pad('P_U23','7')['net'];gnd=pad('P_R225','2')['net']
    via('MODE-relocated',mode,MODE_XY)
    route('MODE-front',mode,'F.Cu',[pad('P_U23','2')['position_mm'],MODE_XY],1)
    route('MODE-back',mode,'B.Cu',[MODE_XY,pad('P_R223','1')['position_mm']],3.2)
    via('EN-escape',en,EN_XY)
    route('EN-front',en,'F.Cu',[pad('P_U23','7')['position_mm'],[295.625,127.2],EN_XY],1.1)
    route('EN-back',en,'B.Cu',[EN_XY,[295.3,130.1],[299.6,130.1],pad('P_R225','1')['position_mm']],8.2)
    route('EN-feed',en,'B.Cu',[pad('P_R224','2')['position_mm'],[301.6,129.5875],pad('P_R225','1')['position_mm']],7.5)
    route('EN-pulldown-return',gnd,'B.Cu',[pad('P_R225','2')['position_mm'],[300.8125,132.2],[299.25,132.2]],4)
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md','local-plane-fill.json','native-zone-export.*'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';t=read_sexpr(p.read_text());first(first(t,'title_block'),'rev')[1]='TBP17';p.write_text(sexpr(t)+'\n')
    inputs=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'buck-control-routing.json',BASE/'buck-input-audit.json',STAGING/'assembly-layout-04/allocation.json',*[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_two_board_power_layer_detours.py','route_two_board_power_local_v2.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        moves=[dict(ref='P_R225',old_xy=position(oldfps['P_R225']),new_xy=MOVE,rotation_added_degrees=-90)],
        removed_copper_uuids=sorted(removed),removed_tracks=3,removed_vias=1,
        routes=routes,vias=vias,added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        explicit_foreign_plane_refill_sites=refill,removed_stale_filled_polygons=removed_fill,
        previous_connection_preservation_pending=True,native_plane_refill_pending=True,native_validation_pending=True,
        complete_enable_electrical_qualification=False,fabrication_released=False)
    (OUT/'buck-enable-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(segments=result['added_segments'],vias=len(vias),refill_sites=len(refill))))

if __name__=='__main__':run()
