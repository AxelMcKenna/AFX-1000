"""Five shaped 0.6mm indicator boards on existing button-holder mounting holes."""
import json,math,heapq,csv
from pathlib import Path
from shapely.geometry import Point,LineString,MultiPoint,box
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.cad.two_board_controls_04.pcb import HEADER,prop,rect
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
R=Path(__file__).resolve().parent;REPO=R.parents[3]
SPECS={'vertical':[[0,-7.5],[0,7.5]],'horizontal':[[ -10,0],[10,0]],'scene':[[-11.5,0],[11.5,0]],'pad':[[4,-8],[0,7.5]],'pad1':[[-4,7.5],[4,7.5]],'vertical_top':[[0,-7.5],[0,7.5]]}
def route(free,start,end):
 step=.2;pf=prep(free)
 def point(k):return(k[0]*step,k[1]*step)
 def near(p):
  a,b=[round(v/step) for v in p];opts=[]
  for i in range(a-2,a+3):
   for j in range(b-2,b+3):
    q=point((i,j))
    if free.covers(LineString([p,q])):opts.append((math.dist(p,q),(i,j)))
  assert opts,('endpoint',p);return min(opts)[1]
 src,dst=near(start),near(end);cost={src:0};prev={};queue=[(0,src)]
 while queue:
  _,u=heapq.heappop(queue)
  if u==dst:break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   v=(u[0]+dx,u[1]+dy);g=cost[u]+math.hypot(dx,dy)
   if g>=cost.get(v,1e99) or not pf.covers(Point(point(v))):continue
   if not free.covers(LineString([point(u),point(v)])):continue
   cost[v]=g;prev[v]=u;heapq.heappush(queue,(g+math.dist(v,dst),v))
 assert dst in cost,('unroutable',start,end)
 path=[dst]
 while path[-1]!=src:path.append(prev[path[-1]])
 pts=[start]+[point(k) for k in reversed(path)]+[end]
 # Visibility simplification is constrained by the same manufacturing keepouts.
 out=[pts[0]];i=0
 while i<len(pts)-1:
  j=len(pts)-1
  while j>i+1 and not free.covers(LineString([pts[i],pts[j]])):j-=1
  out.append(pts[j]);i=j
 assert free.covers(LineString(out));return out

def main():
 contracts=[];lib=R/'TBH07.pretty';lib.mkdir(exist_ok=True);seen=set()
 for name,mounts in SPECS.items():
  post=(min if name=="vertical_top" else max)(mounts,key=lambda p:(p[1],p[0]))
  horizontal=all(p[1]==0 for p in mounts)
  wires=[[post[0],post[1]-3.3],[post[0],post[1]+3.3]] if horizontal else [[post[0]+3.3,post[1]],[post[0]-3.3,post[1]]]
  geom=[MultiPoint(mounts+[[4.8,0]]).convex_hull.buffer(2.5,quad_segs=12),LineString(wires).buffer(1.3,quad_segs=12)]
  # The horizontal variants take a U-shaped bridge around the moving stem.
  if horizontal:geom +=[LineString([mounts[0],[mounts[0][0]+1,-4.8],[mounts[1][0]-1,-4.8],mounts[1]]).buffer(1.1,quad_segs=12)]
  poly=unary_union(geom).difference(Point(0,0).buffer(3.2,quad_segs=48))
  if name=='horizontal':poly=poly.intersection(box(-12.1,-20,20,20))
  assert poly.geom_type=='Polygon'
  outer=[list(p) for p in list(poly.exterior.coords)[:-1]];holes=[[list(p) for p in list(r.coords)[:-1]] for r in poly.interiors]
  base=poly.buffer(-.625)
  for p in mounts:base=base.difference(Point(*p).buffer(1.575,quad_segs=24))
  # LED cathode via to back copper, anode directly on front.
  vk=(6,-.825);ledk=(4.8,-.825);leda=(4.8,.825)
  back=base.difference(Point(*wires[1]).buffer(.975,quad_segs=24));pk=route(back,vk,wires[0])
  front=base.difference(Point(*wires[0]).buffer(.975,quad_segs=24)).difference(LineString([ledk,vk]).buffer(.45)).difference(box(4.4,-1.225,5.2,-.425).buffer(.325)).difference(Point(*vk).buffer(.65))
  pa=route(front,leda,wires[1]);lines=[HEADER.replace('(thickness 1.6)','(thickness .6)'),'(net 1 "LED_K")','(net 2 "LED_A")']
  def g(p):return[p[0]+50,p[1]+50]
  def seg(p,q,n,layer):
   p,q=g(p),g(q);lines.append(f'(segment (start {p[0]} {p[1]}) (end {q[0]} {q[1]}) (width .25) (layer "{layer}") (net {n}))')
  lines +=['(footprint "TBH07:KPT1608" (layer "F.Cu") (at 54.8 50) (attr smd)',prop('Reference','D1',0,0),prop('Value','KPT-1608CGCK',0,0),rect(-.65,-1.4,.65,1.4),rect(-.4,-.8,.4,.8,'F.Fab'),'(pad "1" smd rect (at 0 -.825) (size .8 .8) (layers "F.Cu" "F.Paste" "F.Mask") (net 1 "LED_K"))','(pad "2" smd rect (at 0 .825) (size .8 .8) (layers "F.Cu" "F.Paste" "F.Mask") (net 2 "LED_A")))']
  for i,p in enumerate(wires,1):
   x,y=g(p);net='LED_K' if i==1 else 'LED_A';lines +=[f'(footprint "TBH07:Wire" (layer "F.Cu") (at {x} {y}) (attr through_hole)',prop('Reference',f'W{i}',0,0),prop('Value',net,0,0),rect(-.95,-.95,.95,.95),f'(pad "1" thru_hole circle (at 0 0) (size 1.3 1.3) (drill .7) (layers "*.Cu" "*.Mask") (net {i} "{net}")))']
  for i,p in enumerate(mounts,1):
   x,y=g(p);lines +=[f'(footprint "TBH07:M2" (layer "F.Cu") (at {x} {y}) (attr board_only exclude_from_pos_files exclude_from_bom)',prop('Reference',f'H{i}',0,0),prop('Value','Existing holder mount',0,0),'(fp_circle (center 0 0) (end 2.3 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))','(pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))']
  seg(ledk,vk,1,'F.Cu');v=g(vk);lines.append(f'(via (at {v[0]} {v[1]}) (size .65) (drill .3) (layers "F.Cu" "B.Cu") (net 1))')
  for path,n,layer in [(pk,1,'B.Cu'),(pa,2,'F.Cu')]:
   for p,q in zip(path,path[1:]):seg(p,q,n,layer)
  for loop in [outer]+holes:
   for p,q in zip(loop,loop[1:]+loop[:1]):
    p,q=g(p),g(q);lines.append(f'(gr_line (start {p[0]} {p[1]}) (end {q[0]} {q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))')
  lines.append(')');(R/(name+'.kicad_pcb')).write_text('\n'.join(lines)+'\n');(R/(name+'.kicad_pro')).write_text('{}\n')
  for fp in children(read_sexpr((R/(name+'.kicad_pcb')).read_text()),'footprint'):
   fn=fp[1].split(':')[1]
   if fn in seen:continue
   seen.add(fn);fp[1]=fn;first(fp,'at')[1:]=[0,0]
   for pad in children(fp,'pad'):pad[:]=[q for q in pad if not(isinstance(q,list) and q and q[0]=='net')]
   (lib/(fn+'.kicad_mod')).write_text(sexpr(fp)+'\n')
  contracts.append(dict(name=name,outline=outer,cutouts=holes,mounts=mounts,wires=wires,thickness=.6,led_center=[4.8,0],led='KPT-1608CGCK'))
  print(name,'routed',flush=True)
 channel={r['Function']:int(r['Logical_channel']) for r in csv.DictReader((REPO/'hardware/electronics/led_driver/generated/channel-map.csv').open())};buttons=json.loads((REPO/'hardware/cad/two_board_print_01/capture.json').read_text())['buttons'];instances=[]
 for b in buttons:
  if b[0] not in channel or channel[b[0]]>24:continue
  name='vertical_top' if b[0]=='quantize' else next(k for k,v in SPECS.items() if v==b[8]);instances.append(dict(id=b[0],design=name,channel=channel[b[0]],pose=b[5:8]))
 assert len(instances)==25
 (R/'contract.json').write_text(json.dumps(dict(boards=contracts,instances=instances,scope='Exact green emitter fit population; final colors and optical acceptance pending'),indent=2)+'\n')
 (R/'board-data.scad').write_text('tbh07_boards='+json.dumps([[b['outline'],b['cutouts'],b['mounts'],b['wires']] for b in contracts])+';\ntbh07_instances='+json.dumps([[i['id'],list(SPECS).index(i['design']),*i['pose']] for i in instances])+';\n')
 (R/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "TBH07") (type "KiCad") (uri "${KIPRJMOD}/TBH07.pretty") (options "") (descr "Button emitters")))\n')
if __name__=='__main__':main()
