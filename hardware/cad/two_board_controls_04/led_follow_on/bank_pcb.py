"""One reusable bank-emitter board, instantiated four times at the panel."""
import json,math
from pathlib import Path
from shapely.geometry import box,MultiPoint
from shapely.ops import unary_union
from hardware.cad.two_board_controls_04.pcb import HEADER,prop,rect
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
R=Path(__file__).resolve().parent
pts=[(-6+2.8*math.cos(a*math.pi/24),y+2.8*math.sin(a*math.pi/24)) for y in [-6,-1] for a in range(48)]
poly=unary_union([box(-6,-2.1,1.6,2.1),MultiPoint(pts).convex_hull]);outline=[[round(x,6),round(y,6)] for x,y in list(poly.exterior.coords)[:-1]]
lines=[HEADER,'(net 1 "LED_ANODE_5V")','(net 2 "BANK_CATHODE")','(footprint "TBH05:KPT1608" (layer "F.Cu") (at 50 50) (attr smd)',prop('Reference','D1',0,0),prop('Value','KPT-1608CGCK',0,0),rect(-.65,-1.4,.65,1.4),rect(-.4,-.8,.4,.8,'F.Fab'),'(pad "1" smd rect (at 0 -.825) (size .8 .8) (layers "F.Cu" "F.Paste" "F.Mask") (net 2 "BANK_CATHODE"))','(pad "2" smd rect (at 0 .825) (size .8 .8) (layers "F.Cu" "F.Paste" "F.Mask") (net 1 "LED_ANODE_5V")))']
for i,(sgn,net,name) in enumerate([(-1,2,'BANK_CATHODE'),(1,1,'LED_ANODE_5V')],1):
 y=sgn*.85
 lines +=[f'(footprint "TBH05:BankWirePad" (layer "F.Cu") (at 47.5 {50+y}) (attr through_hole)',prop('Reference',f'W{i}',0,0),prop('Value',name,0,0),rect(-.85,-.85,.85,.85),f'(pad "1" thru_hole circle (at 0 0) (size 1.3 1.3) (drill .7) (layers "*.Cu" "*.Mask") (net {net} "{name}")))',f'(segment (start 50 {50+sgn*.825}) (end 47.5 {50+y}) (width .25) (layer "F.Cu") (net {net}))']
for i,y in enumerate([-6,-1],1):lines +=[f'(footprint "TBH05:M2" (layer "F.Cu") (at 44 {50+y}) (attr board_only exclude_from_pos_files exclude_from_bom)',prop('Reference',f'H{i}',0,0),prop('Value','M2',0,0),'(fp_circle (center 0 0) (end 2.3 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))','(pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))']
for a,b in zip(outline,outline[1:]+outline[:1]):lines.append(f'(gr_line (start {50+a[0]} {50+a[1]}) (end {50+b[0]} {50+b[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))')
lines.append(')');(R/'bank.kicad_pcb').write_text('\n'.join(lines)+'\n');(R/'bank.kicad_pro').write_text('{}\n')
for f in children(read_sexpr((R/'bank.kicad_pcb').read_text()),'footprint'):
 name=f[1].split(':')[1];f[1]=name;first(f,'at')[1:]=[0,0]
 for pad in children(f,'pad'):pad[:]=[p for p in pad if not(isinstance(p,list) and p and p[0]=='net')]
 (R/'TBH05.pretty'/(name+'.kicad_mod')).write_text(sexpr(f)+'\n')
(R/'bank-board-data.scad').write_text('tbh05_bank_outline = '+json.dumps(outline)+';\n')
(R/'bank-contract.json').write_text(json.dumps(dict(instances=[dict(center=[x,103],channel=65+i) for i,x in enumerate([82,101,120,139])],outline=outline,z=[39.6,41.2],mpn='KPT-1608CGCK',fabrication_released=False),indent=2)+'\n')
