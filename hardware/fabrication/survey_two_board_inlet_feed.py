"""Capture inlet-feed gaps and outline-only path lower bounds before power routing."""
import heapq,json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape


def shortest_inside(region,start,end):
    assert region.geom_type=='Polygon' and region.is_valid
    if not region.covers(Point(start)) or not region.covers(Point(end)):return None
    vertices=[start,end,*[list(p) for p in region.exterior.coords[:-1]]]
    for ring in region.interiors:vertices.extend(list(p) for p in ring.coords[:-1])
    graph=[[] for _ in vertices]
    for i,p in enumerate(vertices):
        for j in range(i):
            q=vertices[j]
            if region.buffer(1e-8).covers(LineString([p,q])):
                d=math.dist(p,q);graph[i].append((j,d));graph[j].append((i,d))
    dist={0:0};prev={};queue=[(0,0)]
    while queue:
        d,i=heapq.heappop(queue)
        if d!=dist[i]:continue
        if i==1:break
        for j,weight in graph[i]:
            trial=d+weight
            if trial<dist.get(j,float('inf')):dist[j]=trial;prev[j]=i;heapq.heappush(queue,(trial,j))
    if 1 not in dist:return None
    indices=[1]
    while indices[-1]!=0:indices.append(prev[indices[-1]])
    path=[vertices[i] for i in reversed(indices)];line=LineString(path)
    assert region.buffer(1e-8).covers(line) and abs(line.length-dist[1])<1e-6
    return dict(length_mm=line.length,path_mm=path)


def run():
    cap_path=STAGING/'two-board-power-routing-inputs-2383-fast-ov-return-02/capture.json'
    board=STAGING/'two-board-power-fast-ov-return-native-02'
    status_path=STAGING/'two-board-fabrication-status-32/status.json'
    cap=json.loads(cap_path.read_text());status=json.loads(status_path.read_text())
    for d in [cap,status]:
        for p,h in d['source_sha256'].items():assert sha(REPO/p)==h,p
    assert status['power_project']==str((board/'power_protection.kicad_pro').relative_to(REPO))
    objs={o['uuid']:o for o in cap['objects']}
    def pad(ref,pin):return next(o for o in objs.values() if o.get('ref')==ref and o.get('pin')==pin)
    checked=[('I_J1','1'),('I_J1','2'),('I_F1','1'),('I_F1','2'),('P_D101','1'),('P_D101','2'),('P_Q101','1'),('P_U101','8')]
    terminals=[]
    for ref,pin in checked:
        o=pad(ref,pin);group=cap['all_groups'][o['group']]
        terminals.append(dict(ref=ref,pin=pin,net=o['net'],position_mm=o['position_mm'],group=o['group'],group_object_count=len(group),connected_pads=sorted([objs[u]['ref'],objs[u]['pin']] for u in group if objs[u]['kind']=='PAD')))
    assert pad('I_J1','1')['group']==pad('I_F1','1')['group']
    for ref,pin in [('I_J1','2'),('I_F1','2'),('P_D101','1'),('P_D101','2')]:assert len(cap['all_groups'][pad(ref,pin)['group']])==1
    inlet_group=cap['all_groups'][pad('I_J1','1')['group']]
    retained=[objs[u] for u in inlet_group if objs[u]['kind']=='PCB_TRACK']
    assert len(retained)==4
    retained_summary=[dict(uuid=o['uuid'],layer=next(iter(o['layers'])),width_mm=o['width_mm'],length_mm=math.dist(o['position_mm'],o['end_mm'])) for o in retained]
    outline=shape(cap['outline']);lower_bounds=[]
    for name,source,destination in [('fused-feed',('I_F1','2'),('P_Q101','1')),('return',('I_J1','2'),('P_U101','8'))]:
        p,q=pad(*source)['position_mm'],pad(*destination)['position_mm']
        for width in [0,2,4,5,6,8]:
            # Mitred erosion conservatively models the copper edge clearance;
            # obstacles are deliberately omitted, so this is not a legal route.
            safe=outline.buffer(-(.5+width/2),join_style=2)
            result=shortest_inside(safe,p,q)
            lower_bounds.append(dict(path=name,width_mm=width,edge_clearance_mm=.5,straight_distance_mm=math.dist(p,q),outline_only_path=result,
                endpoint_or_corridor_unavailable_without_taper=result is None))
    sources=[Path(__file__),cap_path,status_path,board/'fast-ov-return-audit.json',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},terminal_connectivity=terminals,retained_jack_to_fuse_tracks=retained_summary,outline_only_lower_bounds=lower_bounds,
        pcb_modified=False,selected_routing=False,current_capacity_verified=False,thermal_verified=False,transient_verified=False,
        scope='Visibility-graph shortest paths in a mitred inset outline only. No existing copper, holes, planes, component bodies, layer changes, tapers, via arrays or harness envelopes are cleared. A missing wide-path result is not a proof that a tapered power route is impossible.',
        required_next_work=['Choose a coordinated feed/return corridor or a paired jumper with reviewed mechanical envelope; compare the long C-shaped PCB path with a short physical jumper.',
            'Route the disconnected fused feed, jack return and both TVS pads; preserve the intentional local AUX return topology.',
            'Qualify the retained 1.2mm fuse-pad escape and all other bottlenecks using accepted copper thickness, maximum state/startup current, fuse behavior and allowable voltage/temperature rise.',
            'Implement source protection and shared-return layout for the complete unit; a reference-plane projection check does not establish current capacity.'],fabrication_released=False)
    out=STAGING/'two-board-inlet-feed-survey-01';out.mkdir(exist_ok=False)
    (out/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(retained_tracks=retained_summary,outline_lower_bounds=lower_bounds),indent=2))

if __name__=='__main__':run()
