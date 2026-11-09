"""Move inherited via drills away from SMD lands, reconnecting every contact."""
import json
import math
import shutil
import uuid
from pathlib import Path
from shapely.geometry import LineString, Point
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

BASE=STAGING/'two-board-power-routed-native-07'
CAP=STAGING/'two-board-power-routing-inputs-2554/capture.json'
OUT=STAGING/'two-board-power-via-repair-01'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text())
    for name,h in cap['source_sha256'].items():assert sha(Path(name))==h,name
    routing.SIGNAL_LAYERS=tuple(cap['copper_layers']);routing.WIDTH=.2
    screen=ViaScreen(cap);objects={o['uuid']:o for o in cap['objects']}
    shapes={u:{l:routing.shape(ps) for l,ps in o['layers'].items() if ps} for u,o in objects.items()}
    smd=[(o,g) for u,o in objects.items() if o['kind']=='PAD' and not any(o['drill_mm'])
        for l,g in shapes[u].items() if l in ['F.Cu','B.Cu']]
    targets=[]
    for u,o in objects.items():
        if o['kind']!='PCB_VIA':continue
        gap,pad=min(((Point(o['position_mm']).distance(g)-o['drill_mm']/2,p) for p,g in smd),key=lambda r:r[0])
        if gap<.15:targets.append((u,gap,pad))
    assert len(targets)==10
    tree=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());count=len(tree)
    old_nonvias=sexpr([n for n in tree if not (isinstance(n,list) and n and n[0]=='via')])
    nodes={str(first(v,'uuid')[1]):v for v in children(tree,'via')};codes={str(n[2]):int(n[1]) for n in children(tree,'net')}
    digest=sha(CAP);moves=[];deferred=[]
    for uid,gap,pad in sorted(targets):
        o=objects[uid];net=o['net'];origin=tuple(o['position_mm'])
        assert o['width_mm']==.6 and o['drill_mm']==.3 and o['via_type']==4
        contacts={};contact_objects=[]
        for layer,via_shape in shapes[uid].items():
            for other,p in objects.items():
                if other==uid or p['net']!=net or layer not in shapes[other]:continue
                if via_shape.distance(shapes[other][layer])>1e-5:continue
                if p['kind']=='PCB_TRACK':
                    line=LineString([p['position_mm'],p['end_mm']]);point=line.interpolate(line.project(Point(origin)))
                    xy=tuple(round(v,6) for v in point.coords[0])
                elif p['kind'] in ['PAD','PCB_VIA']:xy=tuple(p['position_mm'])
                else:raise AssertionError(p['kind'])
                contacts.setdefault(layer,set()).add(xy);contact_objects.append(dict(uuid=other,layer=layer,anchor_mm=xy))
        assert len(contacts)>=2
        # Exclude only the drill being moved; other old drill sites remain
        # conservative obstacles even after earlier relocations in this pass.
        oldholes=screen.holes
        screen.holes=[(p,r) for p,r in oldholes if not (tuple(p)==origin and r==.15)]
        assert len(screen.holes)==len(oldholes)-1
        sites=sorted((math.dist(origin,(ix/4,iy/4)),(ix/4,iy/4))
            for ix in range(math.floor((origin[0]-2.5)*4),math.ceil((origin[0]+2.5)*4)+1)
            for iy in range(math.floor((origin[1]-2.5)*4),math.ceil((origin[1]+2.5)*4)+1))
        best=None
        for distance,xy in sites:
            if distance>2.5 or not screen.via_legal(net,xy):continue
            paths=[];total=0
            for layer,points in contacts.items():
                for point in sorted(points):
                    result=screen.simple(net,layer,point,xy,3.5)
                    if not result:break
                    total+=result[0];paths.append((layer,result[1]))
                else:continue
                break
            else:
                # Prefer the smallest displacement, then short reconnects.
                best=(distance,total,xy,paths);break
        screen.holes=oldholes
        if best is None:
            deferred.append(dict(uuid=uid,net=net,old_position_mm=origin,old_drill_to_SMD_mm=gap,nearest_SMD=[pad['ref'],pad['pin']]))
            print('Deferred via',uid,net,flush=True);continue
        distance,total,xy,paths=best;first(nodes[uid],'at')[1:3]=list(xy);declared=[]
        for layer,path in paths:
            ids=[]
            for p,q in zip(path,path[1:]):
                ident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'AFX:TBVR01:{digest}:{uid}:{layer}:{p}:{q}'))
                tree.append([a('segment'),[a('start'),*p],[a('end'),*q],[a('width'),.2],[a('layer'),layer],[a('net'),codes[net]],[a('uuid'),ident]])
                ids.append(ident)
            declared.append(dict(layer=layer,path_mm=path,segment_uuids=ids));screen.added.append((net,layer,LineString(path)))
        screen.vias.append((net,xy))
        for layer in routing.SIGNAL_LAYERS:screen.added.append((net,layer,Point(xy).buffer(.2)))
        moves.append(dict(uuid=uid,net=net,old_position_mm=origin,new_position_mm=xy,displacement_mm=distance,
            old_drill_to_SMD_mm=gap,nearest_old_SMD=[pad['ref'],pad['pin']],old_contact_objects=contact_objects,
            paths=declared,total_reconnect_length_mm=total))
        print('Moved via',uid,net,round(distance,3),'mm; contacts',len(contact_objects),flush=True)
    assert moves and sexpr([n for n in tree[:count] if not (isinstance(n,list) and n and n[0]=='via')])==old_nonvias
    shutil.copytree(STAGING/'two-board-power-integration-10',OUT)
    dest=OUT/'power_protection.kicad_pcb';dest.write_text(sexpr(tree)+'\n')
    inputs=[Path(__file__),CAP,BASE/'power_protection.kicad_pcb',BASE/'additive-audit.json',BASE/'retained-via-clearance.json',
        *[REPO/'hardware/fabrication'/n for n in ['route_two_board_power_layer_detours.py','route_two_board_power_local_v2.py','route_two_board_power_local.py','route_nf_surface.py']]]
    data=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs},candidate_PCB_sha256=sha(dest),
        original_via_in_SMD_count=len(targets),relocations=moves,deferred=deferred,
        added_segments=sum(len(p['segment_uuids']) for r in moves for p in r['paths']),added_vias=0,
        maximum_via_displacement_mm=2.5,maximum_individual_reconnect_length_mm=3.5,
        component_placement_and_existing_tracks_unchanged=True,native_validation_pending=True,
        loaded_noise_timing_and_assembly_process_qualified=False,fabrication_released=False)
    (OUT/'via-repair.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(moved=len(moves),deferred=len(deferred),segments=data['added_segments'])))


if __name__=='__main__':run()
