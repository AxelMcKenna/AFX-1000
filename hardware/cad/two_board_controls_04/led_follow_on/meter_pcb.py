"""Two routed 20-channel emitter boards with source-derived apertures and wire pads."""
import json,math,csv,hashlib
from pathlib import Path
from shapely.geometry import box,MultiPoint
from shapely.ops import unary_union
from hardware.cad.two_board_controls_04.pcb import HEADER,prop,rect
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
R=Path(__file__).resolve().parent;REPO=R.parents[3]
def track(a,b,net,width=.25):return f'(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {width}) (layer "F.Cu") (net {net}))'
def main():
 boardrows=[];shapes=[]
 for idx,name in enumerate(['meter_input','meter_output']):
  cy=21.25+14*idx;sgn=-1 if idx==0 else 1;mx=[43.9,100.9];my=cy+sgn*6.5
  geom=[box(40.9,cy-3.75,103.9,cy+3.75)]
  for x in mx:
   pts=[(x+2.8*math.cos(a*math.pi/24),y+2.8*math.sin(a*math.pi/24)) for y in [my,cy+sgn*2.8] for a in range(48)]
   geom.append(MultiPoint(pts).convex_hull)
  poly=unary_union(geom);outline=[[round(x,6),round(y,6)] for x,y in list(poly.exterior.coords)[:-1]];shapes.append([[x,y-cy] for x,y in outline]);lines=[HEADER,'(net 1 "LED_ANODE_5V")']
  lines +=[f'(net {i+2} "{name}_{i}")' for i in range(20)]
  parts=[]
  for i in range(20):
   x=43.9+3*i
   # One selected green optical-fit population; footprints accept separately verified colors.
   lines +=[f'(footprint "TBH05:KPT1608" (layer "F.Cu") (at {x} {cy}) (attr smd)',prop('Reference',f'D{i+1}',0,0),prop('Value','KPT-1608CGCK',0,0),rect(-.65,-1.4,.65,1.4),rect(-.4,-.8,.4,.8,'F.Fab'),f'(pad "1" smd rect (at 0 -.825) (size .8 .8) (layers "F.Cu" "F.Paste" "F.Mask") (net {i+2} "{name}_{i}"))','(pad "2" smd rect (at 0 .825) (size .8 .8) (layers "F.Cu" "F.Paste" "F.Mask") (net 1 "LED_ANODE_5V")))']
   lines +=[f'(footprint "TBH05:WirePad" (layer "F.Cu") (at {x} {cy-2.4}) (attr through_hole)',prop('Reference',f'W{i+1}',0,0),prop('Value',f'{name}_{i}',0,0),rect(-.95,-.95,.95,.95),f'(pad "1" thru_hole circle (at 0 0) (size 1.5 1.5) (drill .8) (layers "*.Cu" "*.Mask") (net {i+2} "{name}_{i}")))',track((x,cy-.825),(x,cy-2.4),i+2),track((x,cy+.825),(x,cy+2.45),1)]
   parts.append(dict(ref=f'D{i+1}',mpn='KPT-1608CGCK',center=[x,cy],logical_channel=25+20*idx+i))
  x=72.4;y=cy+2.45
  lines +=[f'(footprint "TBH05:WirePad" (layer "F.Cu") (at {x} {y}) (attr through_hole)',prop('Reference','WA',0,0),prop('Value','LED_ANODE_5V',0,0),rect(-.95,-.95,.95,.95),'(pad "1" thru_hole circle (at 0 0) (size 1.5 1.5) (drill .8) (layers "*.Cu" "*.Mask") (net 1 "LED_ANODE_5V")))',track((43.9,y),(100.9,y),1,.4)]
  for i,x in enumerate(mx,1):lines +=[f'(footprint "TBH05:M2" (layer "F.Cu") (at {x} {my}) (attr board_only exclude_from_pos_files exclude_from_bom)',prop('Reference',f'H{i}',0,0),prop('Value','M2',0,0),'(fp_circle (center 0 0) (end 2.3 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))','(pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))']
  for a,b in zip(outline,outline[1:]+outline[:1]):lines.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))')
  lines.append(')');(R/(name+'.kicad_pcb')).write_text('\n'.join(lines)+'\n');(R/(name+'.kicad_pro')).write_text('{}\n');boardrows.append(dict(name=name,outline=outline,z=[39.3,40.9],mounts=[[x,my] for x in mx],parts=parts))
  lib=R/'TBH05.pretty';lib.mkdir(exist_ok=True)
  for fp in children(read_sexpr((R/(name+'.kicad_pcb')).read_text()),'footprint'):
   fn=fp[1].split(':')[1];fp[1]=fn;first(fp,'at')[1:]=[0,0]
   for pad in children(fp,'pad'):pad[:]=[p for p in pad if not(isinstance(p,list) and p and p[0]=='net')]
   (lib/(fn+'.kicad_mod')).write_text(sexpr(fp)+'\n')
 (R/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "TBH05")(type "KiCad")(uri "${KIPRJMOD}/TBH05.pretty")(options "")(descr "Meter emitter board")))\n')
 (R/'meter-board-data.scad').write_text('tbh05_meter_outlines = '+json.dumps(shapes)+';\n')
 (R/'meter-contract.json').write_text(json.dumps(dict(boards=boardrows,population='Green optical-fit candidate; final meter color progression and optical brightness not qualified',fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':main()
