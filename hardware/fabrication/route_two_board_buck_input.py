"""Regroup U23 bulk input capacitors and add bounded local input/ground planes."""
import copy
import json
import math
import shutil
import uuid
from pathlib import Path
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position, angle, transform_object, mechanical_check
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-buck-control-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2518-buck-control/capture.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
OUT=STAGING/'two-board-power-buck-input-01'
MOVES={'P_C224':([301.8,127.15],0),'P_C225':([300,122],0),'P_R40':([304.5,120.25],-90)}


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text());placement=json.loads(PLACEMENT.read_text())
    for name,h in cap['source_sha256'].items():assert sha(Path(name))==h,name
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    oldfps={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(oldfps)
    obj={o['uuid']:o for o in cap['objects']}
    for o in obj.values():
        if o.get('ref') in MOVES:assert cap['all_groups'][o['group']]==[o['uuid']]
    for ref,(p,r) in MOVES.items():fps[ref]=rotate_footprint(fps[ref],p,r)
    mechanical_check(fps,set(MOVES),placement)
    new=[]
    for o in obj.values():
        ref=o.get('ref')
        new.append(transform_object(o,position(oldfps[ref]),*MOVES[ref]) if ref in MOVES else o)
    cap=copy.deepcopy(cap);cap['objects']=new
    geometries=[(o,l,routing.shape(ps)) for o in new for l,ps in o['layers'].items() if ps]
    trees={l:([(o,g) for o,k,g in geometries if k==l],STRtree([g for o,k,g in geometries if k==l])) for l in cap['copper_layers']}
    holes=[]
    for o in new:
        d=o.get('drill_mm',0);r=max(d)/2 if isinstance(d,list) else d/2
        if r:holes.append((o['position_mm'],r))
    outline=routing.shape(cap['outline']).buffer(-.5)
    mounts=[(o['position_mm'],max(3.6,max(o['drill_mm'])/2+.5)) for o in new if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    for o,l,g in geometries:
        if o.get('ref') not in MOVES:continue
        assert outline.covers(g),(o['ref'],'edge')
        rows,tree=trees[l]
        for i in tree.query(g.buffer(.211)):
            other,h=rows[int(i)]
            if other.get('ref')!=o['ref'] and other['net']!=o['net']:assert g.distance(h)>=.21-1e-7,(o['ref'],other.get('ref'))
        assert all(g.distance(Point(p))-r>=.15 for p,r in holes)
        assert all(g.distance(Point(p))>=r+.01 for p,r in mounts)
    for i,f in enumerate(board):
        if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in MOVES:board[i]=fps[prop(f,'Reference')[2]]
    codes={str(n[2]):int(n[1]) for n in children(board,'net')};routes=[];added=[];vias=[]
    def pad(ref,pin):return next(o for o in new if o.get('ref')==ref and o.get('pin')==pin)
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPBUCKINPUT01:'+sha(CAP)+':'+label))
    def legal(net,layer,points,width):
        line=LineString(points)
        if not outline.buffer(-width/2-.01).covers(line):return False
        rows,tree=trees[layer]
        for i in tree.query(line.buffer(width/2+.211)):
            o,g=rows[int(i)]
            if o['net']!=net and line.distance(g)<width/2+.21-1e-7:return False
        if any(n!=net and l==layer and line.distance(g)<width/2+w/2+.21-1e-7 for n,l,w,g in added):return False
        if any(line.distance(Point(p))<r+width/2+.01 for p,r in mounts):return False
        return True
    def connect(label,net,layer,start,end,width,limit,forced=None):
        candidates=[forced] if forced else routing.candidate_paths(start,end)
        good=[]
        for points in candidates:
            points=[p for i,p in enumerate(points) if not i or list(p)!=list(points[i-1])]
            if len(points)<2:continue
            length=LineString(points).length
            if length<=limit and legal(net,layer,points,width):good.append((length,points))
        assert good,(label,'no bounded route')
        length,points=min(good,key=lambda v:v[0]);ids=[]
        for i,(p,q) in enumerate(zip(points,points[1:])):
            u=uid(label+':'+str(i));ids.append(u)
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),u]])
        added.append((net,layer,width,LineString(points)))
        routes.append(dict(label=label,net=net,layer=layer,width_mm=width,path_mm=points,length_mm=length,maximum_length_mm=limit,segment_uuids=ids))
        print(label,round(length,3),'mm',flush=True)
    def via(net,xy,label):
        routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2;screen=ViaScreen(cap)
        screen.vias=[(v['net'],v['position_mm']) for v in vias]
        assert screen.via_legal(net,xy),(label,xy,'via')
        assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21 for n,l,w,g in added)
        u=uid(label);board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        vias.append(dict(uuid=u,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for l in cap['copper_layers']:added.append((net,l,.6,Point(xy)))
    vin=pad('P_C224','1')['net'];gnd=pad('P_C224','2')['net']
    for label,net,points in [
        ('VIN-right',vin,[[298.3,126.4],[298.3,127.1]]),
        ('VIN-left',vin,[[289.7,127.9],[291.5,127.9]]),
        ('VIN-bulk',vin,[[299.1,123.9],[300,123.1]]),
        ('PGND-left',gnd,[[292,124.3],[293,124.3]]),
        ('PGND-C224',gnd,[[301.6,125.1],[301.6,125.9]]),
        ('PGND-C225',gnd,[[301.7,124],[302.5,124]])]:
        for i,xy in enumerate(points):via(net,xy,label+'-via-'+str(i))
    connect('VIN-right-front',vin,'F.Cu',pad('P_C230','1')['position_mm'],[298.3,126.4],.35,2)
    for l in ['F.Cu','B.Cu']:connect('VIN-right-bus-'+l,vin,l,[298.3,126.4],[298.3,127.1],.6,1)
    connect('VIN-C224-back',vin,'B.Cu',pad('P_C224','1')['position_mm'],[298.3,126.4],.8,3.2)
    connect('VIN-left-front',vin,'F.Cu',pad('P_C223','1')['position_mm'],[290.6,127.9],.35,2)
    for l in ['F.Cu','B.Cu']:connect('VIN-left-bus-'+l,vin,l,[289.7,127.9],[291.5,127.9],.6,2)
    connect('VIN-C225-back',vin,'B.Cu',pad('P_C225','1')['position_mm'],[300,123.1],.8,5)
    connect('VIN-bulk-bus',vin,'B.Cu',[299.1,123.9],[300,123.1],.6,1.3)
    connect('PGND-left-front',gnd,'F.Cu',[293,124.3],pad('P_U23','11')['position_mm'],.4,3)
    connect('PGND-left-bus',gnd,'F.Cu',[292,124.3],[293,124.3],.6,1.1)
    connect('PGND-C224-back',gnd,'B.Cu',pad('P_C224','2')['position_mm'],[301.6,125.9],.8,2.5)
    connect('PGND-C224-bus',gnd,'B.Cu',[301.6,125.1],[301.6,125.9],.6,1)
    connect('PGND-C225-back',gnd,'B.Cu',pad('P_C225','2')['position_mm'],[301.7,124],.8,2.2)
    connect('PGND-C225-bus',gnd,'B.Cu',[301.7,124],[302.5,124],.6,1)
    zones=[]
    for label,net,layer,box in [('local-PGND',gnd,'In1.Cu',[289,109,303.2,134.5]),
                              ('local-VIN',vin,'In3.Cu',[289,121,302.5,128.3])]:
        x0,y0,x1,y1=box;ring=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]];ident=uid(label)
        assert outline.covers(routing.Polygon(ring))
        assert all(routing.Polygon(ring).distance(Point(p))>=r+.3 for p,r in mounts)
        board.append([a('zone'),[a('net'),codes[net]],[a('net_name'),net],[a('layer'),layer],[a('uuid'),ident],
            [a('hatch'),a('edge'),.5],[a('connect_pads'),a('yes'),[a('clearance'),.2]],
            [a('min_thickness'),.25],[a('filled_areas_thickness'),a('no')],
            [a('fill'),a('yes'),[a('thermal_gap'),.25],[a('thermal_bridge_width'),.5],[a('island_removal_mode'),0]],
            [a('polygon'),[a('pts'),*[[a('xy'),*p] for p in ring]]]])
        zones.append(dict(uuid=ident,net=net,layer=layer,outline_mm=ring,clearance_mm=.2,minimum_thickness_mm=.25,solid_pad_connections=True))
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','buck-control-audit.json','rejected-source-net-status.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP16';p.write_text(sexpr(root)+'\n')
    inputs=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'buck-control-audit.json',STAGING/'assembly-layout-04/allocation.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_two_board_power_layer_detours.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        moves=[dict(ref=r,old_xy=position(oldfps[r]),new_xy=p,rotation_added_degrees=rot) for r,(p,rot) in MOVES.items()],
        routes=routes,vias=vias,zones=zones,added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        existing_copper_unchanged=True,schematic_pin_net_map_unchanged=True,
        native_plane_fill_pending=True,whole_board_planes_complete=False,effective_capacitance_and_power_stage_qualified=False,
        native_validation_pending=True,fabrication_released=False)
    (OUT/'buck-input-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),tracks=result['added_segments'],vias=len(vias))))

if __name__=='__main__':run()
