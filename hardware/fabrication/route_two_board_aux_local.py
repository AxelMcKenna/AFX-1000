"""Regroup and route the local AUX regulator, capacitors and feedback divider."""
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

BASE=STAGING/'two-board-power-u23-quiet-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2462-u23-quiet/capture.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
OUT=STAGING/'two-board-power-aux-local-01'
SURVEY=STAGING/'two-board-aux-cell-survey-01/survey.json'
MOVES={'P_U102':([190.5,130],90),'P_C113':([187.8,124.1],-90),
       'P_C106':([190.5,135.5],0),'P_C107':([195.5,138.6],-90),
       'P_R109':([186.9,134],90),'P_R108':([188.7,129.5],0),
       'P_R130':([193,132],180),'P_C110':([190.175,125],180)}


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text());placement=json.loads(PLACEMENT.read_text())
    for d in [cap,json.loads(SURVEY.read_text())]:
        for name,h in d['source_sha256'].items():assert sha(REPO/name)==h,name
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    oldfps={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(oldfps)
    obj={o['uuid']:o for o in cap['objects']}
    for o in obj.values():
        if o.get('ref') in MOVES and o.get('pin'):assert cap['all_groups'][o['group']]==[o['uuid']]
    for ref,(p,r) in MOVES.items():fps[ref]=rotate_footprint(fps[ref],p,r)
    records={r['id']:r for r in placement['parts']}
    assert records['P_C204']['value']==records['P_C205']['value']
    assert records['P_C204']['height_mm']==records['P_C205']['height_mm']
    assert first(oldfps['P_C204'],'layer')[1]=='B.Cu' and angle(oldfps['P_C204'])==0
    for k in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']:
        records['P_C204'][k]=copy.deepcopy(records['P_C205'][k])
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
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPAUXLOCAL01:'+sha(CAP)+':'+label))
    def legal(net,layer,points,width):
        line=LineString(points)
        # Existing planes are on inner layers. Surface tracks do not change
        # their fill; an inner route must clear any foreign authored zone.
        if any(z['layer']==layer and z['net']!=net and line.distance(routing.shape(z['authored_outline']))<width/2+.21 for z in cap['zones']):return False
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
        # Via radius plus fill clearance is .5mm; .61mm keeps every existing
        # plane unchanged. A fresh native refill independently verifies this.
        assert all(Point(xy).distance(routing.shape(z['authored_outline']))>.61 for z in cap['zones'])
        routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2;screen=ViaScreen(dict(cap,zones=[]))
        screen.vias=[(v['net'],v['position_mm']) for v in vias]
        assert screen.via_legal(net,xy),(label,xy,'via')
        assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21 for n,l,w,g in added)
        u=uid(label);board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        vias.append(dict(uuid=u,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for l in cap['copper_layers']:added.append((net,l,.6,Point(xy)))
    vin=pad('P_U102','8')['net'];out=pad('P_U102','1')['net']
    gnd=pad('P_U102','4')['net'];fb=pad('P_U102','2')['net']
    trim=pad('P_R130','1')['net'];delay=pad('P_U102','7')['net']
    connect('input-cap-front',vin,'F.Cu',pad('P_C113','1')['position_mm'],pad('P_U102','8')['position_mm'],.4,4)
    connect('output-cap-front',out,'F.Cu',pad('P_U102','1')['position_mm'],pad('P_C106','1')['position_mm'],.4,4)
    connect('output-return-front',gnd,'F.Cu',pad('P_C106','2')['position_mm'],pad('P_U102','4')['position_mm'],.4,4)
    connect('delay-cap-front',delay,'F.Cu',pad('P_U102','7')['position_mm'],pad('P_C110','1')['position_mm'],.2,2.5)
    connect('GND-pin-to-EP',gnd,'F.Cu',pad('P_U102','4')['position_mm'],pad('P_U102','9')['position_mm'],.4,3)
    via(vin,[188.95,125.3],'EN-feed-via');via(vin,[191.475,126.65],'EN-pin-via')
    connect('EN-feed-front',vin,'F.Cu',pad('P_C113','1')['position_mm'],[188.95,125.3],.2,1.5)
    connect('EN-In4',vin,'In4.Cu',[188.95,125.3],[191.475,126.65],.2,4)
    connect('EN-front',vin,'F.Cu',[191.475,126.65],pad('P_U102','5')['position_mm'],.2,1.5)
    via(fb,[190.6,133.6],'FB-pin-via');via(fb,[187.7,135.9],'FB-resistor-via')
    connect('FB-pin-front',fb,'F.Cu',pad('P_U102','2')['position_mm'],[190.6,133.6],.2,2,
            forced=[pad('P_U102','2')['position_mm'],[190.175,133.05],[190.6,133.6]])
    connect('FB-resistor-front',fb,'F.Cu',pad('P_R109','1')['position_mm'],[187.7,135.9],.2,1.5)
    connect('FB-local-back',fb,'B.Cu',[187.7,135.9],[190.6,133.6],.2,5)
    connect('FB-trim-back',fb,'B.Cu',[190.6,133.6],pad('P_R130','2')['position_mm'],.2,3)
    connect('trim-back',trim,'B.Cu',pad('P_R108','2')['position_mm'],pad('P_R130','1')['position_mm'],.2,6)
    via(out,[188.3,137.2],'output-sense-via')
    connect('output-sense-front',out,'F.Cu',pad('P_C106','1')['position_mm'],[188.3,137.2],.25,2.5)
    connect('output-sense-back',out,'B.Cu',[188.3,137.2],pad('P_R108','1')['position_mm'],.2,10,
            forced=[[188.3,137.2],[187,137.2],[187,131],pad('P_R108','1')['position_mm']])
    connect('feedback-ground-front',gnd,'F.Cu',pad('P_R109','2')['position_mm'],pad('P_U102','9')['position_mm'],.25,7,
            forced=[pad('P_R109','2')['position_mm'],[188.2,132.5],[188.2,130],pad('P_U102','9')['position_mm']])
    connect('input-delay-ground-front',gnd,'F.Cu',pad('P_C113','2')['position_mm'],pad('P_C110','2')['position_mm'],.4,3)
    connect('input-ground-to-EP',gnd,'F.Cu',pad('P_C110','2')['position_mm'],pad('P_U102','9')['position_mm'],.4,12,
            forced=[pad('P_C110','2')['position_mm'],[192.7,124.175],[192.7,130],pad('P_U102','9')['position_mm']])
    connect('output-bypass-front',out,'F.Cu',pad('P_C106','1')['position_mm'],pad('P_C107','1')['position_mm'],.4,8,
            forced=[pad('P_C106','1')['position_mm'],[189.025,137.3],[193.2,137.3],pad('P_C107','1')['position_mm']])
    connect('output-bypass-return-front',gnd,'F.Cu',pad('P_C107','2')['position_mm'],pad('P_C106','2')['position_mm'],.4,7)
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP24';p.write_text(sexpr(root)+'\n')
    inputs=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'u23-quiet-audit.json',SURVEY,STAGING/'two-board-power-u20-input-native-01/u20-input-audit.json',STAGING/'assembly-layout-04/allocation.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_two_board_power_layer_detours.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        moves=[dict(ref=r,old_xy=position(oldfps[r]),new_xy=p,rotation_added_degrees=rot) for r,(p,rot) in MOVES.items()],
        routes=routes,vias=vias,added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        existing_copper_unchanged=True,schematic_pin_net_map_unchanged=True,
        local_AUX_connections_pending_native_verification=True,
        main_capacitors_same_side=True,thermal_vias_and_ground_regions_pending=True,
        survey_deviations="R108 moved above cell on back and R130 rotated 180deg to avoid feedback/trim crossover",
        existing_zone_refill_verification_pending=True,
        effective_capacitance_and_power_stage_qualified=False,
        native_validation_pending=True,fabrication_released=False)
    (OUT/'aux-local-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),tracks=result['added_segments'],vias=len(vias))))

if __name__=='__main__':run()
