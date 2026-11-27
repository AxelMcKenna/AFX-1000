"""Generate explicit, fully broken-out selector PCBs; no circuit substitutions."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
HEADER='''(kicad_pcb (version 20240108) (generator pcbnew)
(general (thickness 1.6)) (paper "A4")
(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user))
(setup (pad_to_mask_clearance 0)) (net 0 "")'''
def prop(k,v,x,y,layer='F.Fab'):
 return f'(property "{k}" "{v}" (at {x} {y}) (layer "{layer}") (effects (font (size .7 .7) (thickness .1))))'
def rect(x1,y1,x2,y2,layer='F.CrtYd'):
 return f'(fp_rect (start {x1} {y1}) (end {x2} {y2}) (stroke (width .05) (type solid)) (fill none) (layer "{layer}"))'
def main():
 boards=[]
 for name,mpn,xs in [('settings','JS202011CQN',[-2.5,0,2.5]),('release','JS203011SCQN',[-4,-2,2,4])]:
  smd=name=='release';n=len(xs)*2;lines=[HEADER]+[f'(net {i} "SW_PIN_{i}")' for i in range(1,n+1)]
  lines += [f'(footprint "TBH04:{mpn}" (layer "F.Cu") (at 50 50) (attr '+('smd' if smd else 'through_hole')+')',prop('Reference','SW1',0,0),prop('Value',mpn,0,0),rect(-6.9 if smd else -4.9,-4.3 if smd else -2.6,6.9 if smd else 4.9,4.3 if smd else 2.6),rect(-6.5 if smd else -4.5,-1.8,6.5 if smd else 4.5,1.8,'F.Fab')]
  padmap=[]
  for row,sgn in enumerate([1,-1]):
   for col,x in enumerate(xs):
    i=row*len(xs)+col+1;y=sgn*(2.75 if smd else 1.65)
    shape='smd rect' if smd else 'thru_hole circle';size='1.2 2.5' if smd else '1.5 1.5';drill='' if smd else '(drill .9)';layers='"F.Cu" "F.Paste" "F.Mask"' if smd else '"*.Cu" "*.Mask"'
    lines.append(f'(pad "{i}" {shape} (at {x} {y}) (size {size}) {drill} (layers {layers}) (net {i} "SW_PIN_{i}"))');padmap.append((i,x,y,sgn*5.5))
  lines+=[')']
  for i,x,y,wy in padmap:
   lines += [f'(footprint "TBH04:WirePad" (layer "F.Cu") (at {50+x} {50+wy}) (attr through_hole)',prop('Reference',f'W{i}',0,0),prop('Value',f'SW_PIN_{i}',0,0),rect(-.95,-.95,.95,.95),f'(pad "1" thru_hole circle (at 0 0) (size 1.5 1.5) (drill .8) (layers "*.Cu" "*.Mask") (net {i} "SW_PIN_{i}")))',f'(segment (start {50+x} {50+y}) (end {50+x} {50+wy}) (width .3) (layer "F.Cu") (net {i}))']
  for i,y in enumerate([-9.5,9.5],1):lines += [f'(footprint "TBH04:M2" (layer "F.Cu") (at 50 {50+y}) (attr board_only exclude_from_pos_files exclude_from_bom)',prop('Reference',f'H{i}',0,0),prop('Value','M2',0,0),'(fp_circle (center 0 0) (end 2.3 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))','(pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))']
  for a,b in zip([(42,38.5),(58,38.5),(58,61.5),(42,61.5)],[(58,38.5),(58,61.5),(42,61.5),(42,38.5)]):lines += [f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))']
  lines+=[')'];(R/(name+'.kicad_pcb')).write_text('\n'.join(lines)+'\n')
  boards.append(dict(name=name,mpn=mpn,size_mm=[16,23,1.6],mounts_from_center_mm=[[0,-9.5],[0,9.5]],pins=[dict(switch_pin=i,wire_pad=f'W{i}.1',xy=[x,y],wire_xy=[x,wy]) for i,x,y,wy in padmap]))
 (R/'selector-contract.json').write_text(json.dumps(dict(scope='Explicit selector breakout candidates; all poles retained; no electrical net ties',boards=boards,manufacturer_source='reference/ck-js.pdf p4 (C&K 22 Sep 2022); current official 2026 drawing text agrees with these nominal patterns',fabrication_released=False),indent=2)+'\n')
if __name__=='__main__':main()

# Keep portable local libraries in the same regeneration workflow.
if __name__=='__main__':
 from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
 lib=R/'TBH04.pretty';lib.mkdir(exist_ok=True)
 for n in ['settings','release']:
  tree=read_sexpr((R/(n+'.kicad_pcb')).read_text())
  for fp in children(tree,'footprint'):
   name=fp[1].split(':')[1];fp[1]=name;first(fp,'at')[1:]=[0,0]
   for pad in children(fp,'pad'):pad[:]=[p for p in pad if not(isinstance(p,list) and p and p[0]=='net')]
   (lib/(name+'.kicad_mod')).write_text(sexpr(fp)+'\n')
  (R/(n+'.kicad_pro')).write_text('{}\n')
 (R/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "TBH04")(type "KiCad")(uri "${KIPRJMOD}/TBH04.pretty")(options "")(descr "Explicit TBH04 selector breakouts")))\n')
