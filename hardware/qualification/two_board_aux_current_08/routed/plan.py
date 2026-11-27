"""Route isolated added power-cell nets; no accepted board mutation."""
import json,math,heapq,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import Polygon,Point,LineString,box
from shapely.affinity import rotate,translate,scale
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,children,first
HERE=Path(__file__).resolve().parent;PLACE=HERE.parent/'placement'
def shape(xs):return unary_union([Polygon(x['outer'],x.get('holes',[])) for x in xs])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def astar(start,end,obstacles,reference,width,margin=4,step=.1):
    # Obstacles already include required centerline radius; exact segment test on every edge.
    clear=prep(obstacles);ref=prep(reference);region=box(min(start[0],end[0])-margin,min(start[1],end[1])-margin,max(start[0],end[0])+margin,max(start[1],end[1])+margin)
    def legal(a,b):
        line=LineString([a,b]);return not clear.intersects(line) and ref.covers(line.buffer(width/2)) and region.covers(line)
    if legal(start,end):return [start,end],0
    origin=[min(start[0],end[0])-margin,min(start[1],end[1])-margin]
    pt=lambda n:[origin[0]+n[0]*step,origin[1]+n[1]*step]
    near=lambda p:[(round((p[0]-origin[0])/step)+dx,round((p[1]-origin[1])/step)+dy) for dx in range(-2,3) for dy in range(-2,3)]
    starts=[n for n in near(start) if legal(start,pt(n))];ends={n for n in near(end) if legal(pt(n),end)}
    if not starts or not ends:return None,0
    queue=[];distance={};parent={}
    for n in starts:
        d=math.dist(start,pt(n));distance[n]=d;parent[n]=None;heapq.heappush(queue,(d+math.dist(pt(n),end),d,n))
    count=0
    while queue and count<60000:
        _,cost,n=heapq.heappop(queue)
        if cost!=distance.get(n):continue
        count+=1
        if n in ends:
            nodes=[];v=n
            while v is not None:nodes.append(pt(v));v=parent[v]
            points=[start]+nodes[::-1]+[end]
            # Safe line-of-sight reduction preserves exact clearance/reference checks.
            result=[points[0]];i=0
            while i<len(points)-1:
                j=len(points)-1
                while j>i+1 and not legal(points[i],points[j]):j-=1
                result.append(points[j]);i=j
            return result,count
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nn=(n[0]+dx,n[1]+dy);v=pt(nn);d=cost+step*math.hypot(dx,dy)
            if d>=distance.get(nn,1e100) or not legal(pt(n),v):continue
            distance[nn]=d;parent[nn]=n;heapq.heappush(queue,(d+math.dist(v,end),d,nn))
    return None,count

def run(root):
    stage=root/'hardware/fabrication/staging';cp=stage/'two-board-power-routing-inputs-aux-local-distribution-03/capture.json';bp=stage/'two-board-power-aux-local-distribution-native-03/power_protection.kicad_pcb';cap=json.loads(cp.read_text());assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(bp) for k,v in cap['source_sha256'].items())
    proposal=json.loads((PLACE/'individual-placement.json').read_text());poses={p['ref']:p for g in proposal['groups'].values() for p in g['chosen']['parts']}
    overrides={'P_R901':([196.7,147.1],90),'P_R900':([199.6,147.7],0)}
    for ref,(xy,angle) in overrides.items():poses[ref].update(at_mm=xy,rotation_deg=angle,kicad_orientation_degrees_after_left_right_flip=(angle+180)%360)
    proposal['routed_feedback_pose_overrides']=overrides;(HERE/'placement.json').write_text(json.dumps(proposal,indent=2)+'\n')
    points={}
    for ref,p in poses.items():
        for pin,(x,y) in proposal['footprints'][ref]['pads'].items():
            x=-x if p['layer']=='B.Cu' else x;angle=math.radians(p['rotation_deg']);points[ref,pin]=[p['at_mm'][0]+x*math.cos(angle)+y*math.sin(angle),p['at_mm'][1]-x*math.sin(angle)+y*math.cos(angle)]
    netpath=HERE.parent/'held_rail/native-03/candidate-netlist.xml';xml=ET.parse(netpath);nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
    copper={layer:[] for layer in cap['copper_layers']};objects=[]
    for o in cap['objects']:
        for l,polys in o['layers'].items():copper[l].append((o['net'],shape(polys),o['uuid']))
    for ref,p in poses.items():
        lib,name=p['footprint'].split(':');fp=PLACE/'AUX_READY.pretty'/f'{name}.kicad_mod' if lib=='AUX_READY' else HERE.parent/'held_rail/authored/libraries'/f'{lib}.pretty'/f'{name}.kicad_mod'
        for pad in children(read_sexpr(fp.read_text()),'pad'):
            at=first(pad,'at');x,y=map(float,at[1:3]);w,h=map(float,first(pad,'size')[1:3]);g=translate(box(-w/2,-h/2,w/2,h/2),x,y);g=scale(g,xfact=-1 if p['layer']=='B.Cu' else 1,yfact=1,origin=(0,0));g=translate(rotate(g,-p['rotation_deg'],origin=(0,0)),*p['at_mm']);copper[p['layer']].append((nets.get((ref,pad[1]),'NC:'+ref+':'+pad[1]),g,ref+'.'+pad[1]))
    main=next(z for z in cap['zones'] if z['uuid']=='4b63f119-2e71-5d61-96f6-8b78a1f5c6cb');reference=shape(main['polygons']);routes=[];fail=[]
    # First establish the buck's local signal routes, then return paths to the existing anchored via.
    pairs=[('P_C900','1','P_U900','2'),('P_U900','2','P_U900','3'),('P_U900','9','P_L900','1'),('P_L900','2','P_C901','1'),('P_C901','1','P_U900','10'),('P_C901','1','P_U900','8'),('P_U900','5','P_R900','2'),('P_U900','5','P_R901','1'),('P_R900','1','P_C901','1')]
    for ar,ap,br,bp0 in pairs:
        a=(ar,ap);b=(br,bp0);assert nets[a]==nets[b];net=nets[a];width=.25 if 'P_U900' in [ar,br] else .3
        blocked=unary_union([g.buffer(.2+width/2+.002) for n,g,u in copper['B.Cu'] if n!=net])
        path,nodes=astar(points[a],points[b],blocked,reference,width)
        r=dict(net=net,source=f'{ar}.{ap}',target=f'{br}.{bp0}',layer='B.Cu',width_mm=width,search_nodes=nodes)
        if path:
            g=LineString(path).buffer(width/2);r.update(path_mm=path,length_mm=LineString(path).length,reference_uncovered_mm2=g.difference(reference).area);routes.append(r);copper['B.Cu'].append((net,g,'new-route-'+str(len(routes))))
        else:fail.append(r)
    # Place ordinary 0.6/0.3 through vias outside every pad, with all-layer and filled-zone checks.
    vias=[]
    forbidden_vias=unary_union([g.buffer(.502) for l in copper for n,g,u in copper[l] if n!='PWR_AGND']+[shape(o['layers'].get(l,[])).buffer(.402) for o in cap['objects'] if o['kind']=='PAD' for l in o['layers']]+[g.buffer(.402) for n,g,u in copper['B.Cu'] if n=='PWR_AGND' and '.' in u]+[shape(z['polygons']).buffer(.502) for z in cap['zones'] if z['net']!='PWR_AGND'])
    for name,ideal in [('ic_return',[191.5,147.5]),('input_return',[193,140.9]),('output_return',[199.3,153.075])]:
        candidates=sorted((math.dist([ideal[0]+dx*.1,ideal[1]+dy*.1],ideal),[ideal[0]+dx*.1,ideal[1]+dy*.1]) for dx in range(-15,16) for dy in range(-15,16))
        pos=next((p for _,p in candidates if not forbidden_vias.intersects(Point(p)) and reference.covers(Point(p).buffer(.35))),None)
        assert pos is not None,('no legal ground via',name)
        v=dict(name=name,net='PWR_AGND',position_mm=pos,size_mm=.6,drill_mm=.3);vias.append(v)
        for l in copper:copper[l].append(('PWR_AGND',Point(pos).buffer(.3),'new-via-'+name))
    via_by={v['name']:v for v in vias}
    for ref,pin,dest in [('P_U900','1','ic_return'),('P_U900','11','ic_return'),('P_U900','4','ic_return'),('P_U900','6','ic_return'),('P_C900','2','input_return'),('P_C901','2','output_return'),('P_R901','2','AGND6')]:
        net=nets[ref,pin];assert net=='PWR_AGND';width=.25 if ref=='P_U900' else .3;blocked=unary_union([g.buffer(.2+width/2+.002) for n,g,u in copper['B.Cu'] if n!=net]);target=points['P_U900','6'] if dest=='AGND6' else via_by[dest]['position_mm'];path,nodes=astar(points[ref,pin],target,blocked,reference,width,margin=6)
        r=dict(net=net,source=f'{ref}.{pin}',target_ground_node=dest,layer='B.Cu',width_mm=width,search_nodes=nodes)
        if path:
            g=LineString(path).buffer(width/2);r.update(path_mm=path,length_mm=LineString(path).length,reference_uncovered_mm2=g.difference(reference).area);routes.append(r);copper['B.Cu'].append((net,g,'new-route-'+str(len(routes))))
        else:fail.append(r)
    out=dict(source_sha256={'baseline_pcb':sha(bp),'baseline_capture':sha(cp),'placement_baseline':sha(PLACE/'individual-placement.json'),'placement':sha(HERE/'placement.json'),'native_poses':sha(PLACE/'native/native-poses.json'),'netlist':sha(netpath)},pad_centers_mm={r+'.'+p:xy for (r,p),xy in points.items()},routes=routes,failures=fail,new_vias=vias,new_zones=[],existing_pad_net_changes=[],qualified=False,scope='Isolated new buck local-cell routes; no existing supply cutover',reference_zone_uuid=main['uuid'])
    (HERE/'plan.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'routes':len(routes),'failures':len(fail),'segments':sum(len(r['path_mm'])-1 for r in routes)}))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
