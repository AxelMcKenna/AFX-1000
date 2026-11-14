"""Explicit 3.3V AS5600 I2C sensor; no OTP or local pullups."""
from pathlib import Path
import json,uuid
from hardware.electronics.common.flat_schematic import generate
R=Path(__file__).resolve().parent
SOURCE='https://www.infineon.com/assets/row/public/documents/30/49/infineon-as5600-datasheet-en.pdf'
def pin(n,name,kind,net,side='L'):return dict(number=str(n),name=name,kind=kind,net=net,side=side)
def component(ref,part,fp,pins,x,y,note='',source=''):return dict(ref=ref,part=part,footprint='RMX_TBH05:'+fp,pins=pins,x=x,y=y,note=note,source=source)
C=[component('U1','AS5600-ASOM','SOIC8_3.9x4.9_P1.27',[pin(1,'VDD5V','power_in','V3V3_IO'),pin(2,'VDD3V3','power_in','V3V3_IO'),pin(3,'OUT','output',None),pin(4,'GND','power_in','AGND'),pin(5,'PGO','input',None,'R'),pin(6,'SDA','bidirectional','SDA','R'),pin(7,'SCL','input','SCL','R'),pin(8,'DIR','input','AGND','R')],76.2,63.5,'3.3V only; supplies tied; DIR grounded; PGO left at internal pullup; OUT unused',SOURCE),component('C1','GRM188R71C104KA01D 100nF','C0603',[pin(1,'1','passive','AGND'),pin(2,'2','passive','V3V3_IO','R')],76.2,114.3,'100nF 16V X7R +/-10%; Murata sheet1.6x0.8x0.8mm nominal; reconfirm approval sheet before order','https://www.farnell.com/datasheets/2189124.pdf')]
for i,n in enumerate(['AGND','V3V3_IO','SCL','SDA'],1):C.append(component('W'+str(i),n+' wire','WirePad',[pin(1,n,'passive',n)],177.8,38.1+20.32*i,'Backside soldered wire, no connector substitution; matches signal D_J1010 pin'+str(i)))
generate(R,'TBH05','sensor',C,[(25.4,152.4,'3.3V I2C at0x36. NO OTP programming. System pullups required; no local pullups.'),(25.4,160.02,'20x18mm PCB. Sensor center(10,10); 1mm edge clamp keepout. Unreleased prototype.')],(254,177.8),[('V3V3_IO',25.4,139.7),('AGND',127,139.7)])
def uid(x):return str(uuid.uuid5(uuid.NAMESPACE_URL,'rmx:TBH05:'+x))
N={'AGND':1,'V3V3_IO':2,'SCL':3,'SDA':4}
def prop(k,v,x,y):return f'(property "{k}" "{v}" (at {x} {y}) (layer "F.Fab") (effects (font (size .6 .6) (thickness .1))))'
def rect(a,b,c,d,l='F.CrtYd'):return f'(fp_rect (start {a} {b}) (end {c} {d}) (stroke (width .05) (type solid)) (fill none) (layer "{l}"))'
def fp(ref,name,x,y,pads,box):
 c=next(c for c in C if c['ref']==ref);s=[f'(footprint "RMX_TBH05:{name}" (layer "F.Cu") (at {x} {y}) (path "/{uid("root")}/{uid(ref)}") (attr '+('through_hole' if name=='WirePad' else 'smd')+')',prop('Reference',ref,0,-3),prop('Value',c['part'],0,3),prop('Datasheet',c['source'],0,0),rect(*box)]
 for num,px,py,sx,sy,drill in pads:
  n=next(p['net']for p in c['pins']if p['number']==str(num));net=f'(net {N[n]} "/{n}")' if n else ''
  shape='thru_hole circle' if drill else 'smd rect';layers='"*.Cu" "*.Mask"'if drill else '"F.Cu" "F.Paste" "F.Mask"';s.append(f'(pad "{num}" {shape} (at {px} {py}) (size {sx} {sy}) '+(f'(drill {drill})'if drill else '')+f' (layers {layers}) {net})')
 s+=[')'];return '\n'.join(s)
header='''(kicad_pcb (version 20240108) (generator pcbnew) (general (thickness 1.6)) (paper "A4")
(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user)) (setup (pad_to_mask_clearance 0)) (net 0 "")'''
s=[header]+[f'(net {i} "/{n}")'for n,i in N.items()]
s+=[fp('U1','SOIC8_3.9x4.9_P1.27',10,10,[(i,(-2.475 if i<5 else 2.475),(-1.905+(i-1)*1.27 if i<5 else 1.905-(i-5)*1.27),1.55,.6,None)for i in range(1,9)],[-3.6,-2.7,3.6,2.7]),fp('C1','C0603',4.8,8.095,[(1,-.8,0,.9,.95,None),(2,.8,0,.9,.95,None)],[-1.4,-.73,1.4,.73])]
for i,x in enumerate([6,8.5,11,13.5],1):s+=[fp('W'+str(i),'WirePad',x,3.5,[(1,0,0,1.8,1.8,.8)],[-1,-1,1,1])]
def route(net,pts,w=.25):
 for a,b in zip(pts,pts[1:]):s.append(f'(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {w}) (layer "F.Cu") (net {N[net]}))')
route('V3V3_IO',[(8.5,3.5),(8.5,6),(6.5,6),(6.5,9.365),(7.525,9.365)])
route('V3V3_IO',[(5.6,8.095),(7.525,8.095)])
route('AGND',[(4,8.095),(4,9.2)])
route('AGND',[(7.525,11.905),(6.5,11.905),(6.5,13)])
route('AGND',[(12.475,8.095),(13.4,8.095),(13.4,7.4)])
route('SCL',[(12.475,9.365),(14.5,9.365),(14.5,5.5),(11,5.5),(11,3.5)])
route('SDA',[(12.475,10.635),(15.5,10.635),(15.5,4.5),(13.5,4.5),(13.5,3.5)])
for x,y in [(4,9.2),(6.5,13),(13.4,7.4)]:s.append(f'(via (at {x} {y}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net 1))')
for a,b in zip([(0,0),(20,0),(20,18),(0,18)],[(20,0),(20,18),(0,18),(0,0)]):s.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))')
s.append('(zone (net 1) (net_name "/AGND") (layer "B.Cu") (hatch edge .5) (connect_pads (clearance .25)) (min_thickness .25) (fill yes (thermal_gap .3) (thermal_bridge_width .3)) (polygon (pts (xy 1.1 1.1)(xy 18.9 1.1)(xy 18.9 16.9)(xy 1.1 16.9))))')
(R/'sensor.kicad_pcb').write_text('\n'.join(s+[')'])+'\n')
# Portable local footprints preserve explicitly reviewed coordinates.
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
lib=R/'RMX_TBH05.pretty';lib.mkdir(exist_ok=True)
for f in children(read_sexpr((R/'sensor.kicad_pcb').read_text()),'footprint'):
 name=f[1].split(':')[1];f[1]=name;first(f,'at')[1:]=[0,0];f[:]=[v for v in f if not(isinstance(v,list)and v and v[0]=='path')]
 for p in children(f,'pad'):p[:]=[v for v in p if not(isinstance(v,list)and v and v[0]=='net')]
 (lib/(name+'.kicad_mod')).write_text(sexpr(f)+'\n')
print('Generated sensor schematic and routed PCB candidate')

p=R/'sensor.kicad_pro';pro=json.loads(p.read_text());pro.setdefault('erc',{}).setdefault('rule_severities',{}).update({k:'error' for k in ['single_global_label','four_way_junction','simulation_model_issue','footprint_filter']});pro.setdefault('board',{}).setdefault('design_settings',{}).setdefault('rule_severities',{}).update({k:'error' for k in ['missing_courtyard','track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch','footprint_type_mismatch']});p.write_text(json.dumps(pro,indent=2)+'\n')
