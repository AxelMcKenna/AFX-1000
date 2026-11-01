import json,sys,math,copy,hashlib
from pathlib import Path
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
from hardware.electronics.rail_disconnect.revision28.repair import Router
from hardware.electronics.rail_disconnect.revision28.focused import legal_line,legal_via
from hardware.electronics.rail_disconnect.routing.check import point_segment,segment_distance
D=Path('/private/tmp/afx-u11-independent');R=Path('/private/tmp/afx-u11-restoration')
d=json.load(open(D/'screen.json'));blob=(Path(d['source'])/'rail_disconnect.kicad_pcb').read_bytes();assert hashlib.sha256(blob).hexdigest()==d['source_pcb_sha256'];t=read_sexpr(blob.decode());ids={x['uuid'] for x in d['candidates'][0]['removed_objects']}
for n in list(t):
 if isinstance(n,list) and n and n[0]=='segment' and children(n,'uuid') and str(first(n,'uuid')[1]) in ids:t.remove(n)
r=Router(t);r.path(d['pad']['net'],0,d['candidates'][0]['F_path'],.2);r.via(d['pad']['net'],d['candidates'][0]['via'])

def blockers(net,layer,points=None,via=None):
 rows=[]
 from hardware.electronics.rail_disconnect.revision28.focused import inside,rect_edges
 for g in r.geometry:
  if g['net']==net or g['net']=='BULK_BODY_NOVIA':continue
  if via is None and layer not in g['layers']:continue
  margin=.200001+(.3 if via else .1)
  if via:
   if g['kind']=='line':distance=point_segment(via,g['start'],g['end'])-g['width']/2
   elif g['kind']=='via':distance=math.dist(via,g['xy'])-g['radius']
   else:distance=math.hypot(*(max(abs(via[i]-g['xy'][i])-g['size'][i]/2,0) for i in (0,1)))
  else:
   vals=[]
   for a,b in zip(points,points[1:]):
    if g['kind']=='line':v=segment_distance(a,b,g['start'],g['end'])-g['width']/2
    elif g['kind']=='via':v=point_segment(g['xy'],a,b)-g['radius']
    elif inside(a,g) or inside(b,g):v=0
    else:v=min(segment_distance(a,b,c,d) for c,d in rect_edges(g))
    vals.append(v)
   distance=min(vals)
  if distance<margin:rows.append(dict(distance_to_copper=distance,need=margin,obstacle=g))
 return rows
p12='P12_OV_OK_SCHMITT'
checks=[dict(label='new_P12via11_14p5',net=p12,via=[11,14.5],layer=None),
 dict(label='proposed_P12F',net=p12,points=[[8.6375,14],[10.65,13.95],[11,14.5]],layer=0),
 dict(label='proposed_P12B',net=p12,points=[[9.95,13.75],[8,14.6],[6.75,14.6]],layer=5)]
for c in checks:
 c['blockers']=blockers(c['net'],c['layer'],c.get('points'),c.get('via'));print(c['label'],len(c['blockers']),flush=True)
 for b in c['blockers'][:8]:print(b,flush=True)
print('N12existing',flush=True)
for g in r.geometry:
 if g['net']=='N12_OV_OK_SCHMITT':print(g,flush=True)
(R/'proposed-checks.json').write_text(json.dumps(dict(source=d['source'],source_sha256=d['source_pcb_sha256'],checks=checks),indent=2)+'\n')
# Save reconstructed candidate0 in a private old-format source for local routers.
(R/'reconstructed-candidate0.kicad_pcb').write_text(sexpr(t)+'\n')
