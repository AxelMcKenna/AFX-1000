import sys,json,copy,math
from pathlib import Path
from shapely.geometry import Point,LineString
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.focused import legal_line
R=Path('/private/tmp/afx-u11-restoration');t=read_sexpr((R/'reconstructed-candidate0.kicad_pcb').read_text());names={str(n[1]):str(n[2]).lstrip('/') for n in children(t,'net')};removed=[]
fp=next(f for f in children(t,'footprint') if any(p[1]=='Reference' and p[2]=='U11' for p in children(f,'property')))
a=next(p for p in children(fp,'pad') if p[1]=='4');b=next(p for p in children(fp,'pad') if p[1]=='5');an=copy.deepcopy(first(a,'net'));bn=copy.deepcopy(first(b,'net'));a[a.index(first(a,'net'))]=bn;b[b.index(first(b,'net'))]=an
for n in list(children(t,'segment')):
 net=names[str(first(n,'net')[1])];layer=str(first(n,'layer')[1]);start=tuple(float(x)-100 for x in first(n,'start')[1:3]);end=tuple(float(x)-100 for x in first(n,'end')[1:3]);width=float(first(n,'width')[1]);why=None
 if net=='N12_OV_OK_SCHMITT' and layer=='F.Cu':why='replaceold/candidate N12F afterANDswap'
 if net=='P12_OV_OK_SCHMITT' and layer=='F.Cu' and max(math.dist(start,(8.6375,14)),math.dist(end,(8.6375,14)))<.05:why='removeold upperP12padstub afterANDswap'
 if net in ['P12_OV_OK_SCHMITT','N19_OV_OK'] and Point(7.5,14.075).distance(LineString([start,end]))<.520001+width/2:why='explicit ordinarycontrol withdrawal aroundNEWbarrel'
 if net=='P19_OV_OK_SCHMITT' and layer=='In3.Cu' and ((start,end) in [((8,13.625),(7.875,13.625)),((7.875,13.625),(7.875,13.375))]):why='replace2segment ordinaryP19corner withclear diagonal'
 if why:t.remove(n);removed.append(dict(reason=why,object=sexpr(n)))
for n in children(t,'via'):
 if names[str(first(n,'net')[1])]=='N12_OV_OK_SCHMITT' and math.dist(tuple(float(x)-100 for x in first(n,'at')[1:3]),(7.3,13.975))<1e-6:first(n,'at')[1:3]=read_sexpr('(at 107.5 114.075)')[1:3]
r=Router(t)
routes=[('P19_OV_OK_SCHMITT',3,[(8,13.625),(7.875,13.375)]),
 ('N12_OV_OK_SCHMITT',0,[(8.6375,14),(7.5,14.075)]),
 ('P12_OV_OK_SCHMITT',0,[(8.6375,14.65),(7.6,14.7),(7.4,14.6875),(6.75,14.6)]),
 ('P12_OV_OK_SCHMITT',5,[(9.95,13.75),(9.3,13.75),(8.7,14.5),(7.6,14.7),(7.4,14.6875),(6.75,14.6)]),
 ('N19_OV_OK',5,[(9.95,13.25),(8,13.25),(7.6,13.45),(7.4,13.45),(7.2,13.5),(7.06875,13.625),(6.95,13.8),(6.375,13.8)])]
results=[]
for net,layer,points in routes:
 good=all(legal_line(r,net,layer,p,q,.2) for p,q in zip(points,points[1:]))
 
 if not good:
  from hardware.electronics.rail_disconnect.revision28.focused import inside,rect_edges
  from hardware.electronics.rail_disconnect.routing.check import point_segment,segment_distance
  for g in r.geometry:
   if g['net']==net or layer not in g['layers']:continue
   for p0,p1 in zip(points,points[1:]):
    if g['kind']=='line':dd=segment_distance(p0,p1,g['start'],g['end'])-g['width']/2
    elif g['kind']=='via':dd=point_segment(g['xy'],p0,p1)-g['radius']
    elif inside(p0,g) or inside(p1,g):dd=0
    else:dd=min(segment_distance(p0,p1,c,d) for c,d in rect_edges(g))
    if dd<.300001:print('BLOCK',dd,g,flush=True)
 print(net,layer,good,flush=True);results.append(dict(net=net,layer=layer,points=points,exact_line_clearance_good=good))
 if good:r.path(net,layer,points,.2)
(R/'variant3-geometry.json').write_text(json.dumps(dict(new_proposed_N12_barrel=[7.5,14.075],extra_ordinary_control_removed=removed,new_routes=results,no_original_via_moved=True,actual_minimum_clearance_mm=.2,search_extra20um_not_a_board_rule=True,physical_qualified=False),indent=2)+'\n')
(R/'variant3-oldformat.kicad_pcb').write_text(sexpr(t)+'\n')
