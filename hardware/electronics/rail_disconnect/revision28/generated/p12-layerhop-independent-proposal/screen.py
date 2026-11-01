from pathlib import Path
import sys,json,hashlib,math
from shapely.geometry import Point,LineString,box
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.power_distribution.p03.route import coded
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.focused import legal_line,inside,rect_edges
from hardware.electronics.rail_disconnect.routing.check import point_segment,segment_distance
R=Path('/private/tmp/afx-e28-p12-layerhop');S=Path('/Users/axelmckrnna/dev/rmx-publish/hardware/electronics/rail_disconnect/revision28/generated/strict-centering-clear-work');raw=(S/'rail_disconnect.kicad_pcb').read_bytes();assert hashlib.sha256(raw).hexdigest()=='db0d9dbe65bfb0aa06e8fd9abfbd95ec9c4ec740925d538e7efc718888fa914f'
t=coded(read_sexpr(raw.decode()));r=Router(t);names={str(n[1]):str(n[2]).lstrip('/') for n in children(t,'net')};point=(13.35,10.8);need=.520001;rows=[]
for g in r.geometry:
 if g['net'] in ['P12_OV_OK','BULK_BODY_NOVIA']:continue
 if g['kind']=='line':distance=point_segment(point,g['start'],g['end'])-g['width']/2
 elif g['kind']=='via':distance=math.dist(point,g['xy'])-g['radius']
 else:distance=math.hypot(*(max(abs(point[i]-g['xy'][i])-g['size'][i]/2,0) for i in (0,1)))
 if distance<need:rows.append(dict(geometry=g,distance_to_copper=distance,required=.520001))
# Bind each control blocker to its exact original track UUID/object.
for row in rows:
 g=row['geometry']
 if g['kind']=='line':
  hits=[]
  for n in children(t,'segment'):
   if names[str(first(n,'net')[1])]!=g['net'] or str(first(n,'layer')[1])!=('F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu')[g['layers'][0]]:continue
   a0=tuple(float(v)-100 for v in first(n,'start')[1:3]);b0=tuple(float(v)-100 for v in first(n,'end')[1:3])
   if a0==tuple(g['start']) and b0==tuple(g['end']) and float(first(n,'width')[1])==g['width']:hits.append(n)
  assert len(hits)==1
  row['uuid']=str(first(hits[0],'uuid')[1]);row['source_object']=sexpr(hits[0])
print('blockers',len(rows))
for x in rows:print(x)
report=dict(source=str(S),source_pcb_sha256=hashlib.sha256(raw).hexdigest(),proposed_via=point,via_diameter_mm=.6,drill_mm=.3,blockers=rows,
 all_blockers_are_only_allowed_control_segments=all(x['geometry']['kind']=='line' and x['geometry']['net'] in ['E28_MASTER_ENABLE','P19_OV_OK_SCHMITT','V5_REG_OV_OK_SCHMITT'] for x in rows),physical_qualified=False)
(R/'screen.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['all_blockers_are_only_allowed_control_segments']
for x in rows:
 n=next(n for n in children(t,'segment') if str(first(n,'uuid')[1])==x['uuid']);t.remove(n)
r=Router(t);start=(14,10.6);end=point
print('Bstemlegal',legal_line(r,'P12_OV_OK',5,start,end,.2));assert legal_line(r,'P12_OV_OK',5,start,end,.2)
r.path('P12_OV_OK',5,[start,end],.2);r.via('P12_OV_OK',point)
(R/'candidate0-oldformat.kicad_pcb').write_text(sexpr(t)+'\n')
