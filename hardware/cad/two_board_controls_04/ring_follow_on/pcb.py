"""Eight common-anode RGB emitters, 24 branch resistors, three existing sinks."""
import math,json
from pathlib import Path
from hardware.cad.two_board_controls_04.pcb import HEADER,prop,rect
R=Path(__file__).resolve().parent
C=(244,78)
def xy(a,x,y):
 a=math.radians(a);return (round(C[0]+x*math.cos(a)-y*math.sin(a),6),round(C[1]+x*math.sin(a)+y*math.cos(a),6))
def main():
 nets={1:'ANODE_5V',2:'RING_RED_93',3:'RING_GREEN_94',4:'RING_BLUE_95'}
 for i in range(8):
  for j in range(3):nets[5+i*3+j]=f'BRANCH_{i}_{j}'
 lines=[HEADER]+[f'(net {n} "{v}")' for n,v in nets.items()];parts=[]
 def seg(a,b,n,layer='F.Cu',w=.25):lines.append(f'(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {w}) (layer "{layer}") (net {n}))')
 def via(p,n):lines.append(f'(via (at {p[0]} {p[1]}) (size .65) (drill .3) (layers "F.Cu" "B.Cu") (net {n}))')
 # Closed sink/supply buses with every branch at an explicit vertex.
 buses={1:[],2:[],3:[],4:[]};radii={1:26.5,2:19,3:20,4:21}
 for i in range(8):
  a=i*45;x,y=xy(a,24,0)
  # KiCad positive footprint rotation is counter-clockwise in screen coordinates.
  lines.extend([f'(footprint "TBH06:RGB1616" (layer "F.Cu") (at {x} {y} {-a}) (attr smd)',prop('Reference',f'D{i+1}',0,0),prop('Value','APTF1616LSEEZGKQBKC',0,0),rect(-1.55,-1,1.55,1),rect(-.8,-.8,.8,.8,'F.Fab')])
  for pin,px,py,n in [(1,.875,.5,1),(2,-.875,.5,5+i*3),(3,-.875,-.5,6+i*3),(4,.875,-.5,7+i*3)]:lines.append(f'(pad "{pin}" smd rect (at {px} {py} {-a}) (size .85 .5) (layers "F.Cu" "F.Paste" "F.Mask") (net {n} "{nets[n]}"))')
  lines.append(')');parts.append(dict(kind='led',center=[x,y],angle=a))
  for j,(rx,ry,pinxy) in enumerate([(-1.5,3,(-.875,.5)),(-1.5,-3,(-.875,-.5)),(1.5,-5.5,(.875,-.5))]):
   n=5+i*3+j;bus=2+j;ref=f'R{i*3+j+1}';x,y=xy(a,24+rx,ry);sgn=1 if ry>0 else -1
   lines.extend([f'(footprint "TBH06:R0603" (layer "F.Cu") (at {x} {y} {-a}) (attr smd)',prop('Reference',ref,0,0),prop('Value','RC0603FR-071KP',0,0),rect(-.725,-1.475,.725,1.475),rect(-.4,-.8,.4,.8,'F.Fab')])
   for pin,dy,nn in [(1,-.825,n if sgn>0 else bus),(2,.825,bus if sgn>0 else n)]:lines.append(f'(pad "{pin}" smd roundrect (at 0 {dy} {-a}) (size .95 .8) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio .25) (net {nn} "{nets[nn]}"))')
   lines.append(')');parts.append(dict(kind='resistor',center=[x,y],angle=a))
   start=xy(a,24+pinxy[0],pinxy[1]);bend=xy(a,24+rx,pinxy[1]);end=xy(a,24+rx,ry-sgn*.825);seg(start,bend,n);seg(bend,end,n)
   q=(24+rx,ry+sgn*.825);theta=a+math.degrees(math.atan2(q[1],q[0]));p=xy(theta,radii[bus],0);seg(xy(a,*q),p,bus);via(p,bus);buses[bus].append((theta%360,p))
  p0=xy(a,24+.875,.5);p1=xy(a,25.5,.5);p2=xy(a,25.5,3);theta=a+math.degrees(math.atan2(3,25.5));p3=xy(theta,radii[1],0);seg(p0,p1,1);seg(p1,p2,1);seg(p2,p3,1);via(p3,1);buses[1].append((theta%360,p3))
 for n,rr in radii.items():
  # Four direct solder wires at staggered angles/radii, one per bus.
  theta={1:10,2:15,3:27,4:19}[n];wr={1:26.5,2:19,3:20,4:21}[n];p=xy(theta,wr,0);q=xy(theta,rr,0);seg(p,q,n,"B.Cu");buses[n].append((theta,q));lines.extend([f'(footprint "TBH06:Wire" (layer "F.Cu") (at {p[0]} {p[1]}) (attr through_hole)',prop('Reference',f'W{n}',0,0),prop('Value',nets[n],0,0),rect(-.95,-.95,.95,.95),f'(pad "1" thru_hole circle (at 0 0) (size 1.3 1.3) (drill .7) (layers "*.Cu" "*.Mask") (net {n} "{nets[n]}")))'])
  vertices=sorted(buses[n]+[(a,xy(a,rr,0)) for a in range(0,360,3)]);vertices=[p for _,p in vertices]
  for p,q in zip(vertices,vertices[1:]+vertices[:1]):seg(p,q,n,'B.Cu',.25)
 mounts=[]
 for i,a in enumerate([22.5,157.5,286],1):
  x,y=xy(a,28.5,0);mounts.append([x,y]);lines.extend([f'(footprint "TBH06:M2" (layer "F.Cu") (at {x} {y}) (attr board_only exclude_from_pos_files exclude_from_bom)',prop('Reference',f'H{i}',0,0),prop('Value','M2',0,0),'(fp_circle (center 0 0) (end 2.3 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))','(pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))'])
 from shapely.geometry import Point
 from shapely.ops import unary_union
 poly=unary_union([Point(*C).buffer(29.5,quad_segs=48)]+[Point(*p).buffer(2.8,quad_segs=12) for p in mounts])
 outline=[[round(x,6),round(y,6)] for x,y in list(poly.exterior.coords)[:-1]]
 for p,q in zip(outline,outline[1:]+outline[:1]):lines.append(f'(gr_line (start {p[0]} {p[1]}) (end {q[0]} {q[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))')
 (R/'board-data.scad').write_text('tbh06_outline='+json.dumps([[x-C[0],y-C[1]] for x,y in outline])+';\n')
 for radius in [17.8]:lines.append(f'(gr_circle (center 244 78) (end {244+radius} 78) (stroke (width .05) (type default)) (fill none) (layer "Edge.Cuts"))')
 lines.append(')');(R/'ring.kicad_pcb').write_text('\n'.join(lines)+'\n');(R/'ring.kicad_pro').write_text('{}\n');(R/'contract.json').write_text(json.dumps(dict(mounts=mounts,parts=parts,emitter='APTF1616LSEEZGKQBKC',resistor='RC0603FR-071KP',branch_ohms=1000,top_z=40.9,channels=[93,94,95],optical_acceptance=False),indent=2)+'\n')
 from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
 lib=R/'TBH06.pretty';lib.mkdir(exist_ok=True);seen=set()
 for fp in children(read_sexpr((R/'ring.kicad_pcb').read_text()),'footprint'):
  fn=fp[1].split(':')[1]
  if fn in seen:continue
  seen.add(fn);fp[1]=fn;first(fp,'at')[1:]=[0,0]
  for pad in children(fp,'pad'):pad[:]=[q for q in pad if not(isinstance(q,list) and q and q[0]=='net')]
  (lib/(fn+'.kicad_mod')).write_text(sexpr(fp)+'\n')
 (R/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "TBH06") (type "KiCad") (uri "${KIPRJMOD}/TBH06.pretty") (options "") (descr "RGB ring")))\n')
if __name__=='__main__':main()
