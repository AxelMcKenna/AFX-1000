"""Escape AUX power-good, restore feedback reference and link its input capacitor."""
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
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-aux-ground-native-02'
CAP=STAGING/'two-board-power-routing-inputs-2447-aux-ground-02/capture.json'
OUT=STAGING/'two-board-power-aux-pg-01'
FB='/P_power_supply/AUX_FB'
PG='PWR_POWER_RUN'

def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(REPO/name)==h,name
    load=STAGING/'two-board-aux-load-review-01/review.json'
    for name,h in json.loads(load.read_text())['source_sha256'].items():assert sha(REPO/name)==h,name
    board=read_sexpr((BASE/'power_protection.kicad_pcb').read_text())
    oldxy=[190.6,133.6];newxy=[190.3,133.4]
    retired=[o for o in cap['objects'] if o['net']==FB and (o['position_mm']==oldxy or o.get('end_mm')==oldxy)]
    assert len(retired)==4 and sum(o['kind']=='PCB_VIA' for o in retired)==1
    retired_ids={o['uuid'] for o in retired}
    board[:]=[n for n in board if not (isinstance(n,list) and n and n[0] in ['via','segment'] and str(first(n,'uuid')[1]) in retired_ids)]
    objects=[o for o in cap['objects'] if o['uuid'] not in retired_ids]
    # All affected AUX zones are refilled natively below. Ordinary copper is
    # screened now; existing zones outside this explicitly allowed set are
    # kept clear of new foreign copper and independently verified unchanged.
    zone_labels={z['uuid']:z['label'] for z in json.loads((BASE/'aux-ground-routing.json').read_text())['zones']}
    refilled={u for u,label in zone_labels.items() if label in ['AUX-output-return','AUX-feedback-guard','AUX-thermal-reference']}
    assert len(refilled)==3
    for z in children(board,'zone'):
        if str(first(z,'uuid')[1]) in refilled:z[:]=[n for n in z if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
    geometry=[(o,l,routing.shape(ps)) for o in objects for l,ps in o['layers'].items() if ps]
    trees={l:([(o,g) for o,k,g in geometry if k==l],STRtree([g for o,k,g in geometry if k==l])) for l in cap['copper_layers']}
    outline=routing.shape(cap['outline']).buffer(-.5)
    mounts=[(o['position_mm'],max(3.6,max(o['drill_mm'])/2+.5)) for o in objects if o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
    codes={str(n[2]):int(n[1]) for n in children(board,'net')}
    routes=[];vias=[];added=[]
    routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(dict(cap,objects=objects,zones=[]))
    def pad(ref,pin):return next(o for o in objects if o.get('ref')==ref and o.get('pin')==pin)
    def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBPAUXPG01:'+sha(CAP)+':'+label))
    def legal(net,layer,path,width):
        line=LineString(path)
        if not outline.buffer(-width/2-.01).covers(line):return False
        for z in cap['zones']:
            if z['uuid'] not in refilled and z['layer']==layer and z['net']!=net and line.distance(routing.shape(z['authored_outline']))<width/2+.21:return False
        rows,tree=trees[layer]
        for i in tree.query(line.buffer(width/2+.211)):
            o,g=rows[int(i)]
            if o['net']!=net and line.distance(g)<width/2+.21-1e-7:return False
        if any(n!=net and l==layer and line.distance(g)<width/2+w/2+.21-1e-7 for n,l,w,g in added):return False
        return all(line.distance(Point(p))>=r+width/2+.01 for p,r in mounts)
    def route(label,net,layer,start,end,width,limit,forced=None):
        good=[]
        for path in [forced] if forced else routing.candidate_paths(start,end):
            path=[p for i,p in enumerate(path) if not i or list(p)!=list(path[i-1])]
            if len(path)<2:continue
            length=LineString(path).length
            if length<=limit and legal(net,layer,path,width):good.append((length,path))
        assert good,(label,'no bounded route')
        length,path=min(good,key=lambda x:x[0]);ids=[]
        for i,(p,q) in enumerate(zip(path,path[1:])):
            ident=uid(label+str(i));ids.append(ident)
            board.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),width],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),ident]])
        added.append((net,layer,width,LineString(path)))
        routes.append(dict(label=label,net=net,layer=layer,width_mm=width,path_mm=path,length_mm=length,maximum_length_mm=limit,segment_uuids=ids))
        print(label,round(length,4),flush=True)
    def via(label,net,xy):
        assert all(z['uuid'] in refilled or Point(xy).distance(routing.shape(z['authored_outline']))>.61 for z in cap['zones']),label
        screen.vias=[(v['net'],v['position_mm']) for v in vias]
        assert screen.via_legal(net,xy),(label,'native-copper/via screen')
        assert all(n==net or Point(xy).distance(g)>=.3+w/2+.21 for n,l,w,g in added),(label,'new-copper screen')
        ident=uid(label)
        board.append([a('via'),[a('at'),*xy],[a('size'),.6],[a('drill'),.3],[a('layers'),'F.Cu','B.Cu'],[a('net'),codes[net]],[a('uuid'),ident]])
        vias.append(dict(uuid=ident,label=label,net=net,position_mm=xy,size_mm=.6,drill_mm=.3))
        for layer in cap['copper_layers']:added.append((net,layer,.6,Point(xy)))
    via('relocated-FB',FB,newxy)
    route('FB-pin-renewal',FB,'F.Cu',[190.175,133.05],newxy,.2,1)
    route('FB-divider-renewal',FB,'B.Cu',[187.7,135.9],newxy,.2,4)
    route('FB-trim-renewal',FB,'B.Cu',newxy,[192.0875,132],.2,3)
    via('PG-escape',PG,[190.5,134.5])
    route('PG-pin-front',PG,'F.Cu',pad('P_U102','3')['position_mm'],[190.5,134.5],.2,3,
          forced=[pad('P_U102','3')['position_mm'],[190.825,133],[191.05,133.6],[190.5,134.5]])
    via('SHDN-escape',PG,[197.5,125.5])
    route('PG-to-SHDN-In4',PG,'In4.Cu',[190.5,134.5],[197.5,125.5],.2,16)
    route('SHDN-pin-front',PG,'F.Cu',[197.5,125.5],pad('P_U101','12')['position_mm'],.2,2,
          forced=[[197.5,125.5],[197.75,125.25],pad('P_U101','12')['position_mm']])
    vin=pad('P_C102','1')['net']
    route('AUX-input-capacitor-feed',vin,'B.Cu',pad('P_C102','1')['position_mm'],[188.95,125.3],.4,9)
    shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.log','drc.*','erc.*','netlist.xml','review.json','circuit-audit.json','plots','*-audit.json','rejected-source-net-status.json','README.md'))
    # Correct the substituted part's datasheet in each active representation.
    correct='https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf'
    edits=[]
    def fix(node,where):
        field=next((p for p in children(node,'property') if p[1]=='Datasheet'),None)
        old=None if field is None else field[2]
        if field is None:
            assert where in ['embedded E_U42 symbol','local library E_U42 symbol']
            field=copy.deepcopy(prop(node,'Value'));field[1]='Datasheet'
            first(field,'effects').append([a('hide'),a('yes')]);node.append(field)
        else:assert 'aup3g17' in old,(where,old)
        field[2]=correct;edits.append(dict(location=where,old=old,new=correct))
    fp=next(f for f in children(board,'footprint') if prop(f,'Reference')[2]=='E_U42')
    assert prop(fp,'Value')[2]=='SN74LVC3G17DCUR'
    fix(fp,'PCB E_U42')
    (OUT/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
    schpath=next(OUT.glob('E_*.kicad_sch'));sch=read_sexpr(schpath.read_text())
    symbol=next(s for s in children(sch,'symbol') if prop(s,'Reference')[2]=='E_U42')
    libid=first(symbol,'lib_id')[1];fix(symbol,'schematic E_U42')
    embedded=next(s for s in children(first(sch,'lib_symbols'),'symbol') if s[1]==libid)
    fix(embedded,'embedded E_U42 symbol');schpath.write_text(sexpr(sch)+'\n')
    libpath=OUT/'symbols'/(libid.split(':')[0]+'.kicad_sym');lib=read_sexpr(libpath.read_text())
    sym=next(s for s in children(lib,'symbol') if s[1]==libid.split(':')[1]);fix(sym,'local library E_U42 symbol')
    libpath.write_text(sexpr(lib)+'\n')
    p=OUT/'power_protection.kicad_sch';root=read_sexpr(p.read_text());first(first(root,'title_block'),'rev')[1]='TBP26';p.write_text(sexpr(root)+'\n')
    paths=[Path(__file__),CAP,load,BASE/'power_protection.kicad_pcb',BASE/'aux-ground-audit.json',BASE/'netlist.xml',
           REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        retired_objects=retired,relocated_FB_via=dict(old_xy=oldxy,new_xy=newxy,distance_mm=math.dist(oldxy,newxy)),
        routes=routes,vias=vias,metadata_edits=edits,refilled_zone_uuids=sorted(refilled),
        added_segments=sum(len(r['segment_uuids']) for r in routes),added_vias=len(vias),
        retired_segments=3,retired_vias=1,component_poses_and_values_unchanged=True,
        complete_pin_net_map_unchanged=True,native_validation_pending=True,
        input_capacitor_connected_to_local_AUX_cell=True,upstream_VIN_source_routing_complete=False,
        local_PG_to_eFuse_SHDN_connected=True,whole_RUN_net_connected=False,
        ground_return_and_FB_reference_revalidation_pending=True,
        actual_AUX_current_startup_thermal_qualified=False,fabrication_released=False)
    (OUT/'aux-pg-routing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(tracks=result['added_segments'],vias=len(vias),removed_tracks=3,removed_vias=1)))

if __name__=='__main__':run()
