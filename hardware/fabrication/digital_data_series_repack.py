"""Place R3015 near the buffer and reuse the long path after the resistor.

Retains every unrelated component and copper object. Native flips/orientations
are imported from source-bound templates; emitted routing requires native QA.
"""
import copy,itertools,json,math,time,uuid
from pathlib import Path
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import translate
from shapely.strtree import STRtree
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v2 as search
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_continuous_escape_options_v3 import escape_options
from hardware.fabrication.audit_candidate import sha,geometry_delta
from hardware.fabrication.digital_core_layout import pad_box
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
ROOT=Path(__file__).resolve().parent
SRC='/LED/DATA_5V_SRC';DATA='/LED/DATA_5V'

def polys(g):return [dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]

def run():
    cp=ROOT/'staging/digital-eight-serial-inputs-49/capture.json';cap=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
    pcb=next(Path(p) for p in cap['source_sha256'] if p.endswith('.kicad_pcb'));original=read_sexpr(pcb.read_text());board=copy.deepcopy(original)
    tp=ROOT/'staging/digital-data-series-templates-01/templates.json';templates=json.loads(tp.read_text());assert all(sha(Path(p))==h for p,h in templates['source_sha256'].items())
    assert all(sha(tp.parent/r['file'])==r['sha256'] for r in templates['templates'])
    byid={o['uuid']:o for o in cap['objects']}
    keep={'d34b4002-d43f-5361-bc02-56efb6390b56','3b693fe4-d5a4-55d2-ba57-cafd41d1ad62'}
    remove={'a35ab001-7b4f-53c4-8dda-68c074214151'}
    all_src={o['uuid'] for o in cap['objects'] if o['net']==SRC and o['kind']!='PAD'};assert len(all_src)==21 and keep|remove<=all_src
    reassign=all_src-keep-remove;assert len(reassign)==18
    removed=[];changed=[]
    for tag in ('segment','via'):
        for node in list(children(board,tag)):
            ident=first(node,'uuid')[1]
            if ident in remove:board.remove(node);removed.append(node)
            elif ident in reassign:changed.append(copy.deepcopy(node));assert first(node,'net')[1]==SRC;first(node,'net')[1]=DATA
    oldfp=next(f for f in children(board,'footprint') if any(p[1:3]==['Reference','R3015'] for p in children(f,'property')))
    c=copy.deepcopy(cap);c['objects']=[o for o in c['objects'] if o['uuid'] not in remove and o.get('ref')!='R3015']
    for o in c['objects']:
        if o['uuid'] in reassign:o['net']=DATA
    surface.WIDTH=layers.WIDTH=raster.WIDTH=search.WIDTH=.2;surface.MARGIN=.01
    surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu');search.LAYERS=('In5.Cu',)
    initial_screen=DigitalViaScreen(c,signal_layers=surface.SIGNAL_LAYERS)
    fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(board,'footprint')}
    sides={r:first(f,'layer')[1][0] for r,f in fps.items()}
    courts={r:box(*courtyard(f,sides[r]+'.CrtYd')) for r,f in fps.items() if r!='R3015'}
    profile=Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)])
    mounts=[box(x-3.6,y-3.6,x+3.6,y+3.6) for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]]
    tht={r:[box(*pad_box(f,p,.5)) for p in children(f,'pad') if p[2]=='thru_hole'] for r,f in fps.items() if r!='R3015'}
    geometries={side:[(o['net'],surface.shape(o['layers'][side+'.Cu'])) for o in c['objects'] if o['layers'].get(side+'.Cu')] for side in ['F','B']}
    trees={side:STRtree([g for n,g in rows]) for side,rows in geometries.items()}
    drilled=[(Point(o['position_mm']),max(o.get('drill_mm',[0,0]))/2) for o in c['objects'] if any(o.get('drill_mm',[0,0]))]
    drilled += [(Point(o['position_mm']),float(first(next(v for v in children(original,'via') if first(v,'uuid')[1]==o['uuid']),'drill')[1])/2) for o in c['objects'] if o['kind']=='PCB_VIA']
    source_via=byid['3b693fe4-d5a4-55d2-ba57-cafd41d1ad62']['position_mm']
    poses=[];tried=0;counts=dict(mechanical=0,pad_clear=0,source_path=0,short=0)
    for template in templates['templates']:
        fp=read_sexpr((tp.parent/template['file']).read_text());side=template['side'];court=box(*courtyard(fp,side+'.CrtYd'))
        for x,y in itertools.product([62+i*.25 for i in range(53)],[17+i*.25 for i in range(37)]):
            tried+=1;cc=translate(court,x,y)
            if not profile.covers(cc) or cc.distance(profile.boundary)<.5-1e-8 or any(cc.distance(m)<.15-1e-8 for m in mounts):continue
            if any(cc.distance(g)<.3-1e-8 for r,g in courts.items() if sides[r]==side):continue
            if any(cc.intersection(g).area>1e-10 for r,ps in tht.items() if sides[r]!=side for g in ps):continue
            counts["mechanical"]+=1
            pads=[];legal=True
            for p in template['pads']:
                g=translate(surface.shape(p['polygons']),x,y);net=p['net']
                if any(other!=net and g.distance(obstacle)<.21-1e-8 for i in trees[side].query(g.buffer(.22)) for other,obstacle in [geometries[side][int(i)]]):legal=False;break
                if any(point.distance(g)-radius<.16-1e-8 for point,radius in drilled):legal=False;break
                pads.append(dict(uuid=p['uuid'],ref='R3015',pin=p['pin'],net=net,kind='PAD',position_mm=[p['position_mm'][0]+x,p['position_mm'][1]+y],drill_mm=[0,0],layers={side+'.Cu':polys(g)},group=None))
            if not legal:continue
            counts["pad_clear"]+=1
            print("Pad-clear pose",side,template["angle"],x,y,flush=True)
            pin1=next(p for p in pads if p['pin']=='1');pin2=next(p for p in pads if p['pin']=='2')
            # A legal footprint may need a second via to cross the header column.
            placed=copy.deepcopy(fp);first(placed,'at')[1:3]=[x,y]
            poses.append(dict(side=side,angle=template['angle'],x=x,y=y,template=template['file'],footprint=placed,pads=pads,score=math.dist(pin1['position_mm'],source_via)+.25*math.dist(pin2['position_mm'],[65,18.4])))
    poses.sort(key=lambda p:p['score']);print('Screened',tried,'poses;',len(poses),'legal short-source candidates',counts,flush=True)
    assert poses,'No legal short-source resistor placement'
    attempts=[];selected=None;deadline=time.monotonic()+240
    for pose in poses[:32]:
        if time.monotonic()>deadline:break
        work=copy.deepcopy(c);work['objects']+=pose['pads'];screen=DigitalViaScreen(work,signal_layers=surface.SIGNAL_LAYERS)
        face=pose['side']+'.Cu'
        pin1=next(p for p in pose['pads'] if p['pin']=='1')
        source_portals=escape_options(screen,SRC,{(face,tuple(pin1['position_mm']))},'R3015-input',min(deadline,time.monotonic()+12))
        source_ends=[dict(point=source_via,layers=['In5.Cu'],runs=[],vias=[],cost=0.,group='retained-driver-via')]
        source_route=search.route_multi(screen,SRC,source_portals,{'In5.Cu':source_ends},min(deadline,time.monotonic()+20),max_visits=1500000) if source_portals else None
        if source_route is None:
            attempts.append(dict(side=pose['side'],angle=pose['angle'],position_mm=[pose['x'],pose['y']],source_portals=len(source_portals),source_connected=False));print('No source path',attempts[-1],flush=True);continue
        source_lead=sum(LineString(p).length for _,p in source_route['runs'])
        print('Source route',pose['angle'],'lead',source_lead,'portals',source_route['portals'],flush=True)
        if source_lead+1.363958>18:
            attempts.append(dict(side=pose['side'],angle=pose['angle'],position_mm=[pose['x'],pose['y']],source_connected=True,source_lead_mm=source_lead,source_too_long=True));continue
        assert all(screen.legal(SRC,l,p) for l,p in source_route['runs']) and all(screen.via_legal(SRC,p) for p in source_route['vias'])
        screen.added += [(SRC,l,LineString(p)) for l,p in source_route['runs']]
        screen.new_vias += [(SRC,tuple(p)) for p in source_route['vias']]
        bridge=[[30.175,11.0],[31.825,11.0]];assert screen.legal(DATA,'F.Cu',bridge);screen.added.append((DATA,'F.Cu',LineString(bridge)))
        pin2=next(p for p in pose['pads'] if p['pin']=='2')
        portals=escape_options(screen,DATA,{(face,tuple(pin2['position_mm']))},'R3015-output',min(deadline,time.monotonic()+10))
        endpoints=[]
        for o in work['objects']:
            if o['net']==DATA and o['layers'].get('In5.Cu'):
                for p in [o['position_mm']]+([o['end_mm']] if 'end_mm' in o else []):endpoints.append(dict(point=p,layers=['In5.Cu'],runs=[],vias=[],cost=0.,group='retained-data-route'))
        result=search.route_multi(screen,DATA,portals,{'In5.Cu':endpoints},min(deadline,time.monotonic()+12),max_visits=500000) if portals else None
        attempts.append(dict(side=pose['side'],angle=pose['angle'],position_mm=[pose['x'],pose['y']],source_lead_mm=source_lead,output_portals=len(portals),output_connected=bool(result)))
        print('Pose',attempts[-1],flush=True)
        if result is None:continue
        assert all(screen.legal(DATA,l,p) for l,p in result['runs']) and all(screen.via_legal(DATA,p) for p in result['vias'])
        selected=(pose,source_route,result,bridge);break
    assert selected,'No complete data reconnection at the screened poses'
    pose,source_route,result,bridge=selected;board[board.index(oldfp)]=pose['footprint'];routes=[]
    def append(net,runs,vias):
        for face,path in runs:
            for p,q in zip(path,path[1:]):
                if math.dist(p,q)<1e-7:continue
                uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:data-series:{sha(cp)}:{net}:{face}:{p}:{q}'))
                board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),face],[a('net'),net],[a('uuid'),uid]])
        for p in vias:
            uid=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:data-series-via:{sha(cp)}:{net}:{p}'))
            board.append([a('via'),[a('at'),*p],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),net],[a('uuid'),uid]])
        routes.append(dict(net=net,runs=runs,new_vias_mm=vias,planar_length_mm=sum(LineString(p).length for _,p in runs)))
    append(SRC,source_route['runs'],source_route['vias'])
    append(DATA,[('F.Cu',bridge)]+result['runs'],result['vias'])
    out=ROOT/'staging/digital-data-series-repack-01';out.mkdir(exist_ok=False);dest=out/pcb.name;dest.write_text(sexpr(board)+'\n')
    inputs=[cp,pcb,tp,Path(__file__),tp.parent/pose['template']]+[ROOT/p for p in ['digital_core_layout.py','digital_via_spacing_v2.py','digital_continuous_escape_options_v3.py','digital_visibility_escape.py','digital_native_spacing_search_v2.py','nf_pin_escape_routes.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','route_nf_surface.py']]
    recipe=dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),component_move=dict(ref='R3015',before_mm=[31,11],before_side='F',after_mm=[pose['x'],pose['y']],after_side=pose['side'],after_angle=pose['angle'],template=pose['template']),removed_objects=removed,reassigned_objects_before=changed,reassigned_uuids=sorted(reassign),reassigned_from=SRC,reassigned_to=DATA,retained_driver_escape_uuids=sorted(keep),routes=routes,geometry_delta=geometry_delta(original,board),placement_candidates_screened=tried,legal_short_source_candidates=len(poses),attempts=attempts,native_checks_pending=True,source_damping_and_interface_timing_qualified=False,fabrication_released=False)
    (out/'construction.json').write_text(json.dumps(recipe,indent=2)+'\n');print('Repacked R3015:',recipe['component_move'],flush=True)
if __name__=='__main__':run()
