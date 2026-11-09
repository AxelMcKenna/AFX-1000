"""Route fixed U20 configuration, feedback trim and dedicated output sense."""
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

BASE=STAGING/'two-board-power-u20-output-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2478-u20-output/capture.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
OUT=STAGING/'two-board-power-u20-control-01'
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
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPU20CONTROL01:'+sha(CAP)+':'+label))
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
        # Reject every existing zone envelope before using the no-zone screen.
        assert all(Point(xy).distance(routing.shape(z['authored_outline']))>2 for z in cap['zones'])
        routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2;screen=ViaScreen(dict(cap,zones=[]))
        screen.vias=[(v['net'],v['position_mm']) for v in vias]
        assert screen.via_legal(net,xy),(label,xy,'via')
        assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21 for n,l,w,g in added)
        u=uid(label);board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        vias.append(dict(uuid=u,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for l in cap['copper_layers']:added.append((net,l,.6,Point(xy)))
    sense=pad('P_R200','1')['net'];gnd=pad('P_C200','2')['net']
    xy=[174.5,145.5];via(sense,xy,'sense-via')
    tap=[173.75,123.7];via(sense,tap,'sense-tap-via')
    connect('output-sense-tap',sense,'B.Cu',pad('P_C207','1')['position_mm'],tap,.2,3)
    connect('output-sense-In2',sense,'In2.Cu',tap,xy,.2,26,
        forced=[tap,[173,123.7],[173,145.5],xy])
    connect('output-sense-back',sense,'B.Cu',xy,pad('P_R200','1')['position_mm'],.2,3)
    trim=pad('P_R200','2')['net'];xy=[177.8,142.5];via(trim,xy,'feedback-trim-via')
    connect('feedback-trim-front',trim,'F.Cu',pad('P_R206','1')['position_mm'],xy,.2,2)
    connect('feedback-trim-back',trim,'B.Cu',xy,pad('P_R200','2')['position_mm'],.2,2)
    for label,pin,res,xy in [('FSEL','1','P_R202',[176,138.55]),('MODE','2','P_R203',[177,138.55])]:
        net=pad(res,'1')['net'];via(net,xy,label+'-via')
        connect(label+'-front',net,'F.Cu',pad('P_U20',pin)['position_mm'],xy,.2,2)
        connect(label+'-back',net,'B.Cu',xy,pad(res,'1')['position_mm'],.2,4,
                forced=([xy,[176,140.7],pad(res,'1')['position_mm']] if label=='FSEL' else None))
    quiet=[182.8,141.1];modeground=[175.3,139.3]
    via(gnd,quiet,'quiet-return-via');via(gnd,modeground,'MODE-ground-via')
    connect('quiet-return-front',gnd,'F.Cu',quiet,pad('P_C200','2')['position_mm'],.25,2)
    connect('FSEL-return-back',gnd,'B.Cu',pad('P_R202','2')['position_mm'],quiet,.25,6)
    connect('MODE-return-back',gnd,'B.Cu',pad('P_R203','2')['position_mm'],modeground,.25,4.2)
    connect('configuration-return-In1',gnd,'In1.Cu',modeground,quiet,.25,8)
    # Dedicated sense must avoid the projection of switching copper on ANY layer.
    switching=[g for o,l,g in geometries if any(n in o['net'] for n in ['P03_D_SW','P03_D_BOOT'])]
    sense_shapes=[line.buffer(w/2) for net,l,w,line in added if net==sense]
    projected_gap=min(g.distance(h) for g in sense_shapes for h in switching)
    assert projected_gap>=1.0,(projected_gap,'sense versus switch/boot projection')
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP20';p.write_text(sexpr(root)+'\n')
    inputs=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'u20-output-audit.json',STAGING/'assembly-layout-04/allocation.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_two_board_power_layer_detours.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        moves=[dict(ref=r,old_xy=position(oldfps[r]),new_xy=p,rotation_added_degrees=rot) for r,(p,rot) in MOVES.items()],
        routes=routes,vias=vias,added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        existing_copper_unchanged=True,schematic_pin_net_map_unchanged=True,
        output_sense_feedback_trim_and_configuration_connected=True,
        minimum_projected_sense_to_switching_copper_mm=projected_gap,
        quiet_to_PGND_connection_pending=True,unchanged_existing_zones=True,
        effective_capacitance_and_power_stage_qualified=False,
        native_validation_pending=True,fabrication_released=False)
    (OUT/'u20-control-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),tracks=result['added_segments'],vias=len(vias))))

if __name__=='__main__':run()
