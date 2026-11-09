"""Place eFuse ILIM/dVdT parts locally and route their short control/ground paths."""
import copy
import json
import math
import shutil
import uuid
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,prop,sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_buck_cell import position,angle,transform_object,mechanical_check
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-aux-pg-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2445-aux-pg/capture.json'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
OUT=STAGING/'two-board-power-input-controls-01'
MOVES={'P_C105':([195.5,127.2],270),'P_R107':([198.5,127.4],180)}

def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text());placement=json.loads(PLACEMENT.read_text())
    for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    oldfps={prop(f,'Reference')[2]:f for f in children(board,'footprint')};fps=copy.deepcopy(oldfps)
    for o in cap['objects']:
        if o.get('ref') in MOVES and o.get('pin'):assert cap['all_groups'][o['group']]==[o['uuid']]
    for ref,(p,r) in MOVES.items():fps[ref]=rotate_footprint(fps[ref],p,r)
    records={r['id']:r for r in placement['parts']}
    assert records['P_C204']['value']==records['P_C205']['value'] and records['P_C204']['height_mm']==records['P_C205']['height_mm']
    assert first(oldfps['P_C204'],'layer')[1]=='B.Cu' and angle(oldfps['P_C204'])==0
    for k in ['side','angle','body_relative_xy','courtyard_relative_xy','additional_planar_reserves','tails_relative_xy']:records['P_C204'][k]=copy.deepcopy(records['P_C205'][k])
    mechanical_check(fps,set(MOVES),placement)
    objects=[transform_object(o,position(oldfps[o['ref']]),*MOVES[o['ref']]) if o.get('ref') in MOVES else o for o in cap['objects']]
    cap=copy.deepcopy(cap);cap['objects']=objects
    geoms=[(o,l,routing.shape(ps)) for o in objects for l,ps in o['layers'].items() if ps]
    trees={l:([(o,g) for o,k,g in geoms if k==l],STRtree([g for o,k,g in geoms if k==l])) for l in cap['copper_layers']}
    holes=[]
    for o in objects:
        d=o.get('drill_mm',0);r=max(d)/2 if isinstance(d,list) else d/2
        if r:holes.append((o['position_mm'],r))
    outline=routing.shape(cap['outline']).buffer(-.5)
    mounts=[(o['position_mm'],max(3.6,max(o['drill_mm'])/2+.5)) for o in objects if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    for o,l,g in geoms:
        if o.get('ref') not in MOVES:continue
        assert outline.covers(g)
        rows,tree=trees[l]
        for i in tree.query(g.buffer(.211)):
            other,h=rows[int(i)]
            if other.get('ref')!=o['ref'] and other['net']!=o['net']:assert g.distance(h)>=.21-1e-7,(o['ref'],other.get('ref'))
        assert all(g.distance(Point(p))-r>=.15 for p,r in holes)
        assert all(g.distance(Point(p))>=r+.01 for p,r in mounts)
        assert all(z['layer']!=l or g.distance(routing.shape(z['authored_outline']))>.21 for z in cap['zones'])
    for i,f in enumerate(board):
        if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in MOVES:board[i]=fps[prop(f,'Reference')[2]]
    codes={str(n[2]):int(n[1]) for n in children(board,'net')};routes=[];added=[];vias=[]
    def pad(ref,pin):return next(o for o in objects if o.get('ref')==ref and o.get('pin')==pin)
    def xy(ref,pin):return pad(ref,pin)['position_mm']
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPINPUTCONTROL01:'+sha(CAP)+':'+label))
    def legal(net,layer,path,width):
        line=LineString(path)
        if any(z['layer']==layer and line.distance(routing.shape(z['authored_outline']))<width/2+.21 for z in cap['zones']):return False
        if not outline.buffer(-width/2-.01).covers(line):return False
        rows,tree=trees[layer]
        for i in tree.query(line.buffer(width/2+.211)):
            o,g=rows[int(i)]
            if o['net']!=net and line.distance(g)<width/2+.21-1e-7:return False
        if any(n!=net and l==layer and line.distance(g)<width/2+w/2+.21-1e-7 for n,l,w,g in added):return False
        return all(line.distance(Point(p))>=r+width/2+.01 for p,r in mounts)
    def route(label,net,start,end,width,limit,forced=None):
        good=[]
        for path in [forced] if forced else routing.candidate_paths(start,end):
            path=[p for i,p in enumerate(path) if not i or list(p)!=list(path[i-1])]
            if len(path)<2:continue
            length=LineString(path).length
            if length<=limit and legal(net,'F.Cu',path,width):good.append((length,path))
        assert good,(label,'no bounded route')
        length,path=min(good,key=lambda x:x[0]);ids=[]
        for i,(p,q) in enumerate(zip(path,path[1:])):
            u=uid(label+str(i));ids.append(u)
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),'F.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        added.append((net,'F.Cu',width,LineString(path)))
        routes.append(dict(label=label,net=net,layer='F.Cu',width_mm=width,path_mm=path,length_mm=length,maximum_length_mm=limit,segment_uuids=ids))
        print(label,round(length,4),flush=True)
    def via(label,xy):
        net='PWR_AGND'
        assert all(Point(xy).distance(routing.shape(z['authored_outline']))>.61 for z in cap['zones'])
        routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2;screen=ViaScreen(dict(cap,zones=[]));screen.vias=[(v['net'],v['position_mm']) for v in vias]
        assert screen.via_legal(net,xy),(label,'via clearance')
        assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21 for n,l,w,g in added),(label,'added copper')
        u=uid(label);board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),u]])
        vias.append(dict(uuid=u,label=label,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for l in cap['copper_layers']:added.append((net,l,.6,Point(xy)))
    assert pad('P_R107','1')['net']==pad('P_U101','10')['net']
    assert pad('P_C105','1')['net']==pad('P_U101','9')['net']
    assert all(pad(r,p)['net']=='PWR_AGND' for r,p in [('P_U101','8'),('P_U101','25'),('P_C105','2'),('P_R107','2')])
    route('dVdT-capacitor',pad('P_C105','1')['net'],xy('P_U101','9'),xy('P_C105','1'),.2,3,
          forced=[xy('P_U101','9'),[196.25,125.5],xy('P_C105','1')])
    route('ILIM-resistor',pad('P_R107','1')['net'],xy('P_U101','10'),xy('P_R107','1'),.2,4,
          forced=[xy('P_U101','10'),[196.75,126.2],xy('P_R107','1')])
    gnd='PWR_AGND'
    route('GND-pin-EP',gnd,xy('P_U101','8'),xy('P_U101','25'),.25,3,
          forced=[xy('P_U101','8'),[195.75,123.3],xy('P_U101','25')])
    route('timing-ground-return',gnd,xy('P_U101','8'),xy('P_C105','2'),.25,7,
          forced=[xy('P_U101','8'),[195.75,125.3],[194.3,125.3],[194.3,128.15],xy('P_C105','2')])
    route('ILIM-ground-return',gnd,xy('P_R107','2'),xy('P_C105','2'),.3,4)
    via('control-ground-left',[194,126.7]);via('control-ground-right',[198.7,129.7])
    route('left-ground-stitch',gnd,[194.3,126.7],[194,126.7],.3,.5)
    route('right-ground-stitch',gnd,xy('P_R107','2'),[198.7,129.7],.3,2)
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    p=OUT/'power_protection.kicad_sch';s=read_sexpr(p.read_text());first(first(s,'title_block'),'rev')[1]='TBP27';p.write_text(sexpr(s)+'\n')
    paths=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'aux-pg-audit.json',
        STAGING/'assembly-layout-04/allocation.json',STAGING/'two-board-power-u20-input-native-01/u20-input-audit.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_buck_cell.py','repack_two_board_buck_input.py','route_two_board_power_layer_detours.py','route_nf_surface.py']]]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        moves=[dict(ref=r,old_xy=position(oldfps[r]),new_xy=p,rotation_added_degrees=rot,
                    final_angle=angle(fps[r])) for r,(p,rot) in MOVES.items()],
        routes=routes,vias=vias,added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        existing_tracks_vias_and_zones_unchanged=True,all_pin_nets_values_packages_and_sides_unchanged=True,
        all_moved_numbered_pad_groups_were_isolated=True,mechanical_and_pad_clearance_screen=True,
        exact_passive_MPN_and_complete_tolerance_pending=True,
        ground_vias_are_reference_access_not_proven_thermal_paths=True,
        manufacturer_source='https://www.ti.com/lit/ds/symlink/tps2663.pdf',manufacturer_sections='9.6.1 and 9.6.2, SLVSE94G',
        native_validation_pending=True,full_input_protection_qualified=False,fabrication_released=False)
    (OUT/'input-controls-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(moved=len(MOVES),segments=result['added_segments'],vias=len(vias))))

if __name__=='__main__':run()
