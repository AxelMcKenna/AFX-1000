"""Improve U23 feedback/boot placement and route bounded local power branches.

No long power-net search: each branch has explicit endpoints, width and length
limit. The return planes, output network and full power-stage checks remain open.
"""
import copy
import json
import math
import shutil
import uuid
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import Point, LineString, box
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication.repack_two_board_buck_input import rotate_footprint
from hardware.fabrication.route_two_board_power_local_v2 import MountScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-buck-cell-native-01'
CAP=STAGING/'two-board-power-routing-inputs-2551-buck-cell/capture.json'
OUT=STAGING/'two-board-power-buck-local-01'
PLACEMENT=STAGING/'two-board-placement-05/capture.json'
MOVES={'P_R220':([294.07,131],-90),'P_R221':([296.27,131],180),
       'N_U28':([311.75,133.0],0),'N_C67':([310.30,131.90],0)}
BOOT='P_C221'; TEMPLATE='P_C230'; BOOT_XY=[292.35,128.4]


def position(f):return list(map(float,first(f,'at')[1:3]))
def angle(f):
    p=first(f,'at');return float(p[3]) if len(p)>3 else 0


def transform_object(o,oldxy,newxy,rotation):
    n=copy.deepcopy(o);p=Point(o['position_mm'])
    n['position_mm']=list(translate(rotate(p,-rotation,origin=oldxy),newxy[0]-oldxy[0],newxy[1]-oldxy[1]).coords[0])
    n['orientation_degrees']=(o['orientation_degrees']+rotation)%360
    for layer,ps in o['layers'].items():
        if not ps:continue
        g=translate(rotate(routing.shape(ps),-rotation,origin=oldxy),newxy[0]-oldxy[0],newxy[1]-oldxy[1])
        polygons=[g] if g.geom_type=='Polygon' else list(g.geoms)
        n['layers'][layer]=[dict(outer=list(p.exterior.coords),holes=[list(h.coords) for h in p.interiors]) for p in polygons]
    return n


def mechanical_check(fps,moving,placement):
    records={r['id']:r for r in placement['parts']};obstacles={'F':[],'B':[]}
    for ref,f in fps.items():
        for side in ['F','B']:
            try:obstacles[side].append((ref,box(*courtyard(f,side+'.CrtYd'))))
            except AssertionError:pass
        r=records.get(ref)
        if r and ref not in moving:
            assert first(f,'layer')[1][0]==r['side'],ref
            delta=angle(f)-r['angle'];x,y=position(f)
            def moved_box(b):return translate(rotate(box(*b),-delta,origin=(0,0)),x,y)
            obstacles[r['side']].append((ref,moved_box(r['body_relative_xy'])))
            if r['tails_relative_xy']:
                assert r['side']=='F'
                obstacles['B'].extend((ref,moved_box(b)) for b in r['tails_relative_xy'])
            for e in r['additional_planar_reserves']:obstacles[e['side']].append((ref,moved_box(e['bounds'])))
    contexts=[c for c in placement['context'] if not c['id'].startswith('inlet_')]
    allocation=STAGING/'assembly-layout-04/allocation.json'
    for name,x,y,z,dx,dy,t,*_ in json.loads(allocation.read_text())['additional_panel_PCBS']:
        contexts.append(dict(id=name,xy=[x,y,x+dx,y+dy],z=[z,z+t]))
    for ref in moving:
        f=fps[ref];side=first(f,'layer')[1][0];g=box(*courtyard(f,side+'.CrtYd'))
        hits=[other for other,h in obstacles[side] if other!=ref and g.buffer(.3,join_style=2).intersection(h).area>=1e-8]
        assert not hits,(ref,hits)
        r=records[TEMPLATE if ref==BOOT else ref];h=r['height_mm'];z0=placement['power_Z']
        z=[z0-.2+1.44,z0+.2+1.76+h] if side=='F' else [z0-.2-h,z0+.2]
        assert z[0]>=3.05 and z[1]<=43.35
        for c in contexts:
            if min(z[1]+.25,c['z'][1])>max(z[0]-.25,c['z'][0]):
                assert g.buffer(.25,join_style=2).intersection(box(*c['xy'])).area<1e-8,(ref,c['id'])


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text());placement=json.loads(PLACEMENT.read_text())
    for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    fps={prop(f,'Reference')[2]:f for f in children(board,'footprint')};oldfps=copy.deepcopy(fps)
    objects={o['uuid']:o for o in cap['objects']};moving=set(MOVES)|{BOOT}
    for o in objects.values():
        if o.get('ref') in moving and o.get('group'):
            assert all(objects[u].get('ref')==o['ref'] for u in cap['all_groups'][o['group']]),o['ref']
    for ref,(target,rotation) in MOVES.items():fps[ref]=rotate_footprint(fps[ref],target,rotation)
    # Existing 0402 pad geometry and exact MPN are reused; preserve C221's
    # reference, pad UUIDs, net assignments and schematic instance path.
    boot=rotate_footprint(fps[TEMPLATE],BOOT_XY,0)
    prop(boot,'Reference')[2]=BOOT
    first(boot,'uuid')[:]=first(oldfps[BOOT],'uuid')
    boot[:]=[n for n in boot if not(isinstance(n,list) and n and n[0]=='path')]
    boot.extend(copy.deepcopy(children(oldfps[BOOT],'path')))
    oldpads={str(p[1]):p for p in children(oldfps[BOOT],'pad')}
    for p in children(boot,'pad'):
        original=oldpads[str(p[1])]
        first(p,'uuid')[:]=first(original,'uuid');first(p,'net')[:]=first(original,'net')
    fps[BOOT]=boot
    mechanical_check(fps,moving,placement)
    newobjects=[]
    for o in cap['objects']:
        ref=o.get('ref')
        if ref in MOVES:
            target,rotation=MOVES[ref];n=transform_object(o,position(oldfps[ref]),target,rotation)
        elif ref==BOOT:
            t=next(p for p in cap['objects'] if p.get('ref')==TEMPLATE and p.get('pin')==o['pin'])
            n=transform_object(t,position(oldfps[TEMPLATE]),BOOT_XY,0)
            for key in ['ref','uuid','net','group']:n[key]=o[key]
        else:n=o
        newobjects.append(n)
    cap=copy.deepcopy(cap);cap['objects']=newobjects
    # Exact captured copper polygons screen the moved/replaced pads before routes.
    geometries=[(o,l,routing.shape(ps)) for o in newobjects for l,ps in o['layers'].items() if ps]
    trees={l:([(o,g) for o,k,g in geometries if k==l],STRtree([g for o,k,g in geometries if k==l])) for l in cap['copper_layers']}
    holes=[]
    for o in newobjects:
        d=o.get('drill_mm',0);r=max(d)/2 if isinstance(d,list) else d/2
        if r:holes.append((o['position_mm'],r))
    outline=routing.shape(cap['outline']).buffer(-.5)
    for o,l,g in geometries:
        if o.get('ref') not in moving:continue
        assert outline.covers(g)
        rows,tree=trees[l]
        for i in tree.query(g.buffer(.211)):
            other,h=rows[int(i)]
            if other.get('ref')!=o['ref'] and other['net']!=o['net']:
                assert g.distance(h)>=.21-1e-7,(o['ref'],o['pin'],other.get('ref'),other.get('pin'))
        assert all(g.distance(Point(p))-r>=.15 for p,r in holes),(o['ref'],'drill')
    for i,f in enumerate(board):
        if isinstance(f,list) and f and f[0]=='footprint' and prop(f,'Reference')[2] in moving:
            board[i]=fps[prop(f,'Reference')[2]]
    codes={str(n[2]):int(n[1]) for n in children(board,'net')};routes=[];deferred=[];added=[]
    def pad(ref,pin):
        return next(o for o in newobjects if o.get('ref')==ref and o.get('pin')==pin and o['layers'].get('F.Cu'))
    def connect(label,left,right,width,limit,forced=None):
        p,q=pad(*left),pad(*right);assert p['net']==q['net']
        routing.SIGNAL_LAYERS=('F.Cu',);routing.WIDTH=width;screen=MountScreen(cap)
        # Screen prior additions at their actual widths (Screen's default added
        # geometry assumes one width and cannot represent these mixed branches).
        candidates=[forced] if forced else list(routing.candidate_paths(p['position_mm'],q['position_mm']))
        good=[]
        for points in candidates:
            points=[v for i,v in enumerate(points) if not i or v!=points[i-1]]
            if len(points)<2:continue
            line=LineString(points)
            if line.length>limit or not screen.legal(p['net'],'F.Cu',points):continue
            if any(net!=p['net'] and line.distance(g)<width/2+w/2+.21-1e-7 for net,w,g in added):continue
            good.append((line.length,points))
        if not good and label in ['BOOT','BOOT_RETURN']:
            # Local fine-grid escape only; the same strict length bound applies.
            screen.added=[(net,'F.Cu',g.buffer(max(0,(w-width)/2))) for net,w,g in added]
            points=screen.grid_path(p['net'],'F.Cu',p['position_mm'],q['position_mm'],budget=8000)
            if points and LineString(points).length<=limit:
                good.append((LineString(points).length,points))
        if not good:
            deferred.append(dict(label=label,left=left,right=right,width_mm=width,maximum_length_mm=limit));return
        length,points=min(good,key=lambda row:row[0]);ids=[]
        for start,end in zip(points,points[1:]):
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBPBUCKLOCAL01:{sha(CAP)}:{label}:{start}:{end}'))
            board.append([a('segment'),[a('start'),*start],[a('end'),*end],[a('width'),width],
                          [a('layer'),'F.Cu'],[a('net'),codes[p['net']]],[a('uuid'),uid]])
            ids.append(uid)
        added.append((p['net'],width,LineString(points)))
        routes.append(dict(label=label,left=left,right=right,net=p['net'],width_mm=width,path_mm=points,
                           length_mm=length,maximum_length_mm=limit,segment_uuids=ids))
        print('Routed',label,round(length,3),'mm',flush=True)
    for capref,vin,gnd in [('P_C230','8','9'),('P_C231','12','11')]:
        connect(capref+' VIN',(capref,'1'),('P_U23',vin),.35,2.5)
        connect(capref+' PGND',(capref,'2'),('P_U23',gnd),.35,2.5)
    for bulk,hf in [('P_C222','P_C230'),('P_C223','P_C231')]:
        for pin in ['1','2']:connect(bulk+'.'+pin,(bulk,pin),(hf,pin),.45,3)
    connect('BOOT',(BOOT,'1'),('P_U23','14'),.2,3.5)
    connect('BOOT_RETURN',(BOOT,'2'),('P_U23','13'),.2,3.5)
    connect('BP5',('P_C220','1'),('P_U23','6'),.25,5)
    connect('BP5_AGND',('P_C220','2'),('P_U23','5'),.25,5)
    connect('FB_BOTTOM',('P_R221','1'),('P_U23','4'),.2,4)
    connect('FB_TOP',('P_R220','2'),('P_R221','1'),.2,3.5)
    connect('FB_AGND',('P_R221','2'),('P_C220','2'),.25,5)
    # A short .4mm neck leaves the package before widening to 1mm. The spine
    # is separate from the boot-return pin, which is internally common to SW.
    p=pad('P_U23','10');q=pad('P_L23','1');neck=[295,124.5]
    # Both are one declared branch with per-section widths; use a temporary
    # synthetic same-net anchor only for the bounded construction helper.
    anchor=dict(q,ref='_SW_ANCHOR',pin='1',position_mm=neck)
    newobjects.append(anchor)
    connect('SW_NECK',('P_U23','10'),('_SW_ANCHOR','1'),.4,2.5,forced=[p['position_mm'],neck])
    connect('SW_SPINE',('_SW_ANCHOR','1'),('P_L23','1'),1.0,5,forced=[neck,q['position_mm']])
    newobjects.remove(anchor)
    assert {'BOOT','BOOT_RETURN','FB_BOTTOM','FB_TOP','SW_NECK','SW_SPINE'}<={r['label'] for r in routes},deferred
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('plots','*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','buck-cell-audit.json','README.md'))
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    path=OUT/'P_power_p03.kicad_sch';sheet=read_sexpr(path.read_text())
    symbol=next(s for s in children(sheet,'symbol') if prop(s,'Reference')[2]==BOOT)
    old_value=prop(symbol,'Value')[2];old_fp=prop(symbol,'Footprint')[2]
    prop(symbol,'Value')[2]=prop(boot,'Value')[2];prop(symbol,'Footprint')[2]=boot[1]
    prop(symbol,'Datasheet')[2]='https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005X7R1H104K050BB'
    path.write_text(sexpr(sheet)+'\n')
    path=OUT/'expected-circuit.json';data=json.loads(path.read_text());data[BOOT]['value']=prop(boot,'Value')[2];data[BOOT]['footprint']=boot[1];path.write_text(json.dumps(data,indent=2)+'\n')
    path=OUT/'power_protection.kicad_sch';root=read_sexpr(path.read_text());first(first(root,'title_block'),'rev')[1]='TBP12';path.write_text(sexpr(root)+'\n')
    inputs=[Path(__file__),CAP,PLACEMENT,BASE/'power_protection.kicad_pcb',BASE/'buck-cell-audit.json',
            BASE/'P_power_p03.kicad_sch',BASE/'expected-circuit.json',STAGING/'assembly-layout-04/allocation.json',
            *[REPO/'hardware/fabrication'/n for n in ['route_nf_surface.py','route_two_board_power_local_v2.py','repack_two_board_buck_input.py']]]
    report=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},
        moves=[dict(ref=r,old_xy=position(oldfps[r]),new_xy=p,rotation_added_degrees=rotation) for r,(p,rotation) in MOVES.items()],
        bootstrap_replacement=dict(ref=BOOT,template=TEMPLATE,old_value=old_value,new_value=prop(boot,'Value')[2],
                                   old_footprint=old_fp,new_footprint=str(boot[1]),old_xy=position(oldfps[BOOT]),new_xy=BOOT_XY,
                                   rating='100nF +/-10%, 50V, X7R, 0402',pins_and_nets_unchanged=True,
                                   supplier_url='https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005X7R1H104K050BB',
                                   controller_url='https://www.ti.com/lit/ds/symlink/tps543620.pdf',
                                   basis='TI section 8.2.1.2.7 specifies 0.1uF ceramic rated at least 10V. Existing 50V 0402 MPN reused for a closer boot loop.',
                                   complete_manufacturing_process_and_effective_capacitance_accepted=False),
        logic_bypass_source_relative_offset_mm=[-1.45,-1.1],routes=routes,deferred=deferred,
        added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=0,
        existing_tracks_and_vias_unchanged=True,power_return_planes_and_output_network_complete=False,
        switching_thermal_noise_and_current_qualified=False,native_validation_pending=True,fabrication_released=False)
    (OUT/'buck-local-routing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),deferred=deferred,segments=report['added_segments'])))


if __name__=='__main__':run()
