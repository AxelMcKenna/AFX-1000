"""Source-bound button ground daisychain and first physical routing candidate."""
from pathlib import Path
import json, math, hashlib, heapq
from collections import Counter
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from shapely.prepared import prep
import numpy as np
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
BASE=HERE.parent

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
contract=read(BASE/'r11_distribution/reference/panel-contract.json')
contacts=read(BASE/'r10_interfaces/button-contact-contract.json')
assert [3,4] in contacts['always_connected_pairs']
schedule=read(REPO/'hardware/cad/a11/generated/control-schedule.json')
buttons={b[0]:b for b in schedule['buttons']}
old=read(BASE/'r11_distribution/ground-topology.json')
interfaces={r['reference']:r for r in read(BASE/'r7/interface-manifest.json')['interfaces']}
capture=read(REPO/'hardware/cad/two_board_print_01/capture.json')
endpoints={}
# Looking at underside, screen-right is local -X and screen-up is local +Y.
# OMRON logo top is +localY. This is an explicit assembly orientation condition.
for name,b in buttons.items():
    for pin,(x,y) in {'1':(-3.25,2.25),'2':(3.25,2.25),'3':(-3.25,-2.25),'4':(3.25,-2.25)}.items():
        a=math.radians(b[7]);endpoints['button_'+name+':'+pin]=[b[5]+x*math.cos(a)-y*math.sin(a),b[6]+x*math.sin(a)+y*math.cos(a),31.6]
for root in old['groups']:
    ref,pin=root.split(':');pad=next(p for p in interfaces[ref]['pads'] if p['pin']==pin)
    assert pad['net']=='LINK_AGND';endpoints[root]=pad['xy']+[27.04]
endpoints.update({'settings:W2.1':[307,32.5,34.0],'release:W3.1':[318,59.5,34.0],
                  'GROUND_SCENE:IN':[297.5,42,29.5], 'GROUND_SCENE:OUT_A':[322.5,41.3,29.5], 'GROUND_SCENE:OUT_B':[322.5,42.7,29.5]})
edges=[];chains={}
for root,leaves in sorted(old['groups'].items()):
    remaining=[r['receiver'] for r in leaves if r['receiver'].startswith('button_')]
    up=root;order=[]
    while remaining:
        name=min(remaining,key=lambda n:math.dist(endpoints[up][:2],endpoints[n+':3'][:2]))
        remaining.remove(name);order.append(name)
        edges.append({'from':up,'to':name+':3','root':root,'wire':'Alpha5853 26AWG 7/34'})
        up=name+':4'
    chains[root]=order
    if root=='D_J2003:1':
        edges += [{'from':up,'to':'GROUND_SCENE:IN','root':root,'wire':'Alpha5853 26AWG 7/34'},
                  {'from':'GROUND_SCENE:OUT_A','to':'settings:W2.1','root':root,'wire':'Alpha5853 26AWG 7/34'},
                  {'from':'GROUND_SCENE:OUT_B','to':'release:W3.1','root':root,'wire':'Alpha5853 26AWG 7/34'}]
assert len(edges)==32 and set(Counter(v for e in edges for v in (e['from'],e['to'])).values())=={1}

# Planar routing obstacles are deliberately conservative at the chosen plane.
# Native source checks, not this planner, determine whether a route is clear.
def obstacles(plane):
    fixed=[]
    for ref,xy,z in capture['component_envelopes']:
        if z[0] < plane+.8 and z[1] > plane-.8: fixed.append(box(*xy).buffer(.85))
    for item in capture['context']:
        if not item['id'].startswith(('switch_', 'holder_')) and item['z'][0]<plane+.8 and item['z'][1]>plane-.8:
            fixed.append(box(*item['xy']).buffer(.85))
    for x,y in capture['lid_fasteners']: fixed.append(Point(x,y).buffer(4.4))
    fixed += [box(300,63,334,110),box(260,64,270,75),box(297.5,38.9,322.5,45.1).buffer(.8)]
    return fixed
previous=[]

def route(a,b,obstacles):
    obstacle=unary_union(obstacles); prepared=prep(obstacle)
    def clear(p,q):return not prepared.intersects(LineString([p,q]))
    if clear(a,b):return [a,b]
    def grid(p):
        candidates=[(round(p[0])+dx,round(p[1])+dy) for dx in range(-3,4) for dy in range(-3,4)]
        options=[q for q in candidates if clear(p,q)]
        if not options:raise ValueError(('blocked endpoint',p))
        return min(options,key=lambda q:math.dist(p,q))
    start,goal=grid(a),grid(b)
    todo=[(math.dist(start,goal),0,start)];cost={start:0};parent={}
    while todo:
        _,g,p=heapq.heappop(todo)
        if g!=cost[p]:continue
        if p==goal:break
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            q=(p[0]+dx,p[1]+dy)
            if not (12<=q[0]<=330 and 9<=q[1]<=183) or not clear(p,q):continue
            ng=g+math.hypot(dx,dy)
            if ng<cost.get(q,1e9):cost[q]=ng;parent[q]=p;heapq.heappush(todo,(ng+math.dist(q,goal),ng,q))
    else:raise ValueError(('no path',a,b))
    path=[goal]
    while path[-1]!=start:path.append(parent[path[-1]])
    path=[a]+list(reversed(path))+[b]
    out=[path[0]];i=0
    while i<len(path)-1:
        j=len(path)-1
        while j>i+1 and not clear(path[i],path[j]):j-=1
        out.append(path[j]);i=j
    return [list(p) for i,p in enumerate(out) if i==0 or p!=out[i-1]]

for i,e in enumerate(edges):
    a,b=endpoints[e['from']],endpoints[e['to']]
    guards=[Point(endpoints[k][:2]).buffer(1.3) for k in {v for edge in edges for v in (edge['from'],edge['to'])} if k not in (e['from'],e['to'])]
    aa,bb=a[:2],b[:2]
    if e['from'].startswith('GROUND_SCENE:'):aa=[a[0]+1.3,a[1]]
    if e['to'].startswith('GROUND_SCENE:'):bb=[b[0]-1.3,b[1]]
    for plane in (29.5,28.0,31.0):
        try:p=route(aa,bb,obstacles(plane)+[line.buffer(1.3) for z,line in previous if abs(z-plane)<1.3]+guards)
        except ValueError:continue
        break
    else:raise ValueError(('all routing layers blocked',e['from'],e['to']))
    pts=[a]+[[*xy,plane] for xy in p]+[b]
    pts=[p for j,p in enumerate(pts) if j==0 or p!=pts[j-1]]
    e.update(id='G'+str(i+1).zfill(2),plane_z_mm=plane,points_mm=pts,polyline_length_mm=sum(math.dist(x,y) for x,y in zip(pts,pts[1:])))
    previous.append((plane,LineString(p)))

sources=[Path(__file__),BASE/'r11_distribution/ground-topology.json',BASE/'r11_distribution/reference/panel-contract.json',BASE/'r10_interfaces/button-contact-contract.json',BASE/'r7/interface-manifest.json',REPO/'hardware/cad/a11/generated/control-schedule.json',REPO/'hardware/cad/two_board_print_01/capture.json',REPO/'hardware/cad/two_board_controls_04/selector-contract.json',REPO/'hardware/cad/a11/controls.scad',REPO/'hardware/cad/a11/generated/button-fixture.scad',BASE/'r11_distribution/reference/alpha5853.pdf']
out={'source_sha256':{str(p.relative_to(REPO)):sha(p) for p in sources},'net':'LINK_AGND','chains':chains,'endpoints_mm':endpoints,'edges':edges,'internal_links':[[n+':3',n+':4'] for order in chains.values() for n in order], 'splices':[{'id':'GROUND_SCENE','hardware':'TE34130','insulation':'TE505872P034','center_mm':[310,42,29.5],'axis':'X','receiving_length_mm':25,'receiving_diameter_mm':6.2,'supplier_envelope_verified':False}], 'terminal_orientation':'Bottom-view logo top points +localY. Viewed from -Z with screen-up +localY, screen-right is -localX. Switch terminal1=(-3.25,+2.25),3=(-3.25,-2.25),4=(+3.25,-2.25); apply schedule rotation. Must confirm continuity and actual logo orientation before assembly.', 'wire_OD_supplier_max_mm':1.0922,'modeled_wire_radius_mm':.6,'routing_status':'Candidate sharp-polyline receiving paths; bend formation, wire-to-wire separation, strain support and opening service loops unqualified. Not a cut list.','fabrication_released':False}
(HERE/'ground-routes.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['// Generated first ground routing candidate; no fabrication release.','$fn=24;', 'module ground_segment(a,b){hull(){translate(a)sphere(r=.6);translate(b)sphere(r=.6);}}']
for e in edges:
    lines.append('module panel_ground_'+e['id']+'(){')
    for a,b in zip(e['points_mm'],e['points_mm'][1:]):lines.append('ground_segment('+json.dumps(a)+','+json.dumps(b)+');')
    lines.append('}')
for root,order in chains.items():
    name=root.replace(':','_')
    lines.append('module panel_ground_'+name+'(){'+''.join('panel_ground_'+e['id']+'();' for e in edges if e['root']==root)+'}')
obs=[[ref,xy,z] for ref,xy,z in capture['component_envelopes']+capture['tail_envelopes']] + [[c['id'],c['xy'],c['z']] for c in capture['context'] if not c['id'].startswith(('switch_', 'holder_'))]
lines.append('module panel_ground_allocations(){')
for ref,xy,z in obs:
    lines.append('translate('+json.dumps([xy[0],xy[1],z[0]])+')cube('+json.dumps([xy[2]-xy[0],xy[3]-xy[1],z[1]-z[0]])+'); // '+ref)
lines.append('}')
lines += ['module panel_ground_wires(){'+''.join('panel_ground_'+e['id']+'();' for e in edges)+'}', 'module panel_ground_splice(){translate([297.5,42,29.5])rotate([0,90,0])cylinder(d=6.2,h=25);}', 'module panel_ground_splice_ports(){for(p=[[297.5,42,29.5],[322.5,41.3,29.5],[322.5,42.7,29.5]])translate(p)sphere(r=.6);}']
(HERE/'routes.scad').write_text('\n'.join(lines)+'\n')
print(len(edges),'wires;',len(out['splices']),'splice; receiving route length',round(sum(e['polyline_length_mm'] for e in edges),1))
