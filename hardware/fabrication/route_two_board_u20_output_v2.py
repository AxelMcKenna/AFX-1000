"""Connect the fixed U20 output bank with paired through vias and PGND returns."""
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

BASE=STAGING/'two-board-power-u20-local-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2486-u20-local/capture.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
OUT=STAGING/'two-board-power-u20-output-02'
MOVES={}


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
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPU20OUT02:'+sha(CAP)+':'+label))
    def legal(net,layer,points,width):
        line=LineString(points)
        if any(line.distance(routing.shape(z['authored_outline']))<=2 for z in cap['zones']):return False
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
        # This no-zone screen is used only after excluding every zone envelope.
        assert all(Point(xy).distance(routing.shape(z['authored_outline']))>2 for z in cap['zones'])
        remote_cap=dict(cap,zones=[])
        routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2;screen=ViaScreen(remote_cap)
        screen.vias=[(v['net'],v['position_mm']) for v in vias]
        assert screen.via_legal(net,xy),(label,xy,'via')
        assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21 for n,l,w,g in added)
        u=uid(label);board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        vias.append(dict(uuid=u,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for l in cap['copper_layers']:added.append((net,l,.6,Point(xy)))
    out=pad('P_C208','1')['net'];gnd=pad('P_C208','2')['net']
    connect('front-output',out,'F.Cu',pad('P_C208','1')['position_mm'],pad('P_L20','2')['position_mm'],1,6,forced=[[176.025,120.85],[176.025,125.14],[177.5,125.14]])
    for pin,net in [('1',out),('2',gnd)]:
        for layer,left,right in [('B.Cu','P_C206','P_C207'),('F.Cu','P_C208','P_C209')]:
            connect(left+'-'+right+'.'+pin,net,layer,pad(left,pin)['position_mm'],pad(right,pin)['position_mm'],1,4)
    for i,x in enumerate([175.5,176.5]):
        xy=[x,122.6];via(out,xy,'output-via-'+str(i))
        for l,r in [('F.Cu','P_C208'),('B.Cu','P_C206')]:
            if i==0 and l=='F.Cu':continue  # Front trunk crosses the paired-via bus.
            connect('output-escape-'+str(i)+l,out,l,pad(r,'1')['position_mm'] if i==0 else [175.5,122.6],
                    [176.025,122.6] if i==0 else xy,.6,3)
    for i,x in enumerate([178.5,179.5]):
        xy=[x,122.6];via(gnd,xy,'ground-via-'+str(i))
        for l,r in [('F.Cu','P_C208'),('B.Cu','P_C206')]:
            connect('ground-escape-'+str(i)+l,gnd,l,pad(r,'2')['position_mm'] if i==0 else [178.5,122.6],
                    [178.975,122.6] if i==0 else xy,.6,3)
    for i,x in enumerate([179.5,180.5]):
        xy=[x,133.8];via(gnd,xy,'regulator-ground-via-'+str(i))
        connect('return-bank-'+str(i),gnd,'B.Cu',pad('P_C207','2')['position_mm'] if i==0 else [179.5,133.8],xy,1,12)
        connect('return-PGND-'+str(i),gnd,'F.Cu',xy,pad('P_U20','9')['position_mm'] if i==0 else [179.5,133.8],.4,4)
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','*-audit.json','plots','rejected-source-net-status.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP19';p.write_text(sexpr(root)+'\n')
    inputs=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'u20-local-audit.json',STAGING/'assembly-layout-04/allocation.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_two_board_power_layer_detours.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        moves=[dict(ref=r,old_xy=position(oldfps[r]),new_xy=p,rotation_added_degrees=rot) for r,(p,rot) in MOVES.items()],
        routes=routes,vias=vias,added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        existing_copper_unchanged=True,schematic_pin_net_map_unchanged=True,
        output_bank_fully_returned_to_regulator=True,effective_capacitance_and_power_stage_qualified=False,
        unchanged_existing_zones=True,new_copper_at_least_2mm_from_existing_zones=True,
        current_capacity_thermal_and_return_impedance_qualified=False,
        native_validation_pending=True,fabrication_released=False)
    (OUT/'u20-output-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),tracks=result['added_segments'],vias=len(vias))))

if __name__=='__main__':run()
