"""Local F.Cu capacitor relocation with explicit positive and ground paths."""
import json,math
from pathlib import Path
from shapely.geometry import box,Point,LineString
from shapely.affinity import translate,rotate
from shapely.ops import unary_union,nearest_points,polygonize
from shapely.prepared import prep
from ..routed.plan import shape,astar,sha
H=Path(__file__).resolve().parent

def run():
 c=json.loads((H/'capture-01/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quietids=set(q['retained_object_uuids']);quietzones={x['zone_uuid'] for x in q['plane_exclusions']};main='00b41082-e346-59e4-aee2-f34d9b87e697';reference=shape(next(z['polygons'] for z in c['zones'] if z['uuid']=='13cfea4d-d36e-5757-b531-ed680e4c4562'));by={(o['ref'],o['pin']):o for o in c['objects'] if o.get('ref')};out=[]
 courts={}
 for row in json.loads((H/'courtyards.json').read_text()):
  g=unary_union(list(polygonize([LineString(l) for l in row['lines']]))+[box(*r[0],*r[1]) for r in row['rects']]);at=row['at'];courts[row['ref']]=translate(rotate(g,-(at[2] if len(at)>2 else 0),origin=(0,0)),at[0],at[1])
 for cap,ic in [('E_C36','E_U2'),('E_C13','E_U4')]:
  assert by[ic,'1']['net'] in ['PWR_AUX_HELD3V3','PWR_V2V5_AUX'] and by[ic,'4']['net']=='PWR_AGND' and by[ic,'2']['net'].endswith('_TT')
  courtblocked=prep(unary_union([g for r,g in courts.items() if r!=cap]));originalcenter=[57,118.5] if cap=='E_C36' else [97,127.5];originalangle=90 if cap=='E_C36' else 180;localcourt=rotate(translate(courts[cap],-originalcenter[0],-originalcenter[1]),originalangle,origin=(0,0))
  removed=[o['uuid'] for o in c['objects'] if o.get('ref')==cap];cut=[]
  if cap=='E_C36':
   members=c['all_groups'][by[cap,'1']['group']];cut=[u for u in members if u not in [by[cap,'1']['uuid'],by[ic,'1']['uuid']]];assert len(cut)==1
  obsolete=['6a809b80-0ffb-551e-8b88-4080568a9785'] if cap=='E_C13' else [];retained=[o for o in c['objects'] if o['uuid'] not in removed+cut+obsolete];foreign=unary_union([shape(o['layers']['F.Cu']).buffer(.202) for o in retained if 'F.Cu' in o['layers']]);foreignprep=prep(foreign)
  positive=by[ic,'1'];supplyblocked=unary_union([shape(o['layers']['F.Cu']).buffer(.352) for o in retained if 'F.Cu' in o['layers'] and o['uuid']!=positive['uuid']]);groundblocked=unary_union([shape(o['layers']['F.Cu']).buffer(.352) for o in retained if 'F.Cu' in o['layers'] and (o['group']!=main or o['uuid'] in quietids)])
  viaforbidden=prep(unary_union([shape(polys).buffer(.502) for o in retained for layer,polys in o['layers'].items() if o['group']!=main or o['uuid'] in quietids]+[shape(polys).buffer(.402) for o in retained if o['kind']=='PAD' for polys in o['layers'].values()]+[shape(z['polygons']).buffer(.502) for z in c['zones'] if z['keepout'] or z['net']!='PWR_AGND' or z['uuid'] in quietzones]))
  # Restrict body to the outside of the SOIC input pad row; native courtyard checks still required.
  px,py=positive['position_mm'];positions=sorted(([px-dx*.25,py+dy*.25] for dx in range(9,23) for dy in range(-14,15)),key=lambda p:math.dist(p,[px-2.75,py]));attempts=0;chosen=None
  for center in positions:
   for angle in [180,90,270,0]:
    pads={pin:translate(rotate(box(x-.5,-.725,x+.5,.725),-angle,origin=(0,0)),*center) for pin,x in [('1',-.95),('2',.95)]};body=translate(rotate(box(-1.45,-.725,1.45,.725),-angle,origin=(0,0)),*center)
    if foreignprep.intersects(body) or courtblocked.intersects(translate(rotate(localcourt,-angle,origin=(0,0)),*center)):continue
    sr=pads['1'].intersection(reference.buffer(-.152));er=shape(positive['layers']['F.Cu']).intersection(reference.buffer(-.152));gr=pads['2'].intersection(reference.buffer(-.152))
    if sr.is_empty or er.is_empty or gr.is_empty:continue
    a,b=nearest_points(sr,er);a=list(a.coords)[0];b=list(b.coords)[0];sp,n=astar(a,b,unary_union([supplyblocked,pads['2'].buffer(.352)]),reference,.3,margin=2,step=.15);attempts+=1
    if not sp:continue
    sgeom=LineString(sp).buffer(.15);gb=unary_union([groundblocked,pads['1'].buffer(.352),sgeom.buffer(.202)]);gp=None;v=None;target=None
    targets=sorted([o for o in retained if o['group']==main and o['uuid'] not in quietids and 'F.Cu' in o['layers'] and math.dist(center,o['position_mm'])<4],key=lambda o:math.dist(center,o['position_mm']))[:8]
    for t in targets:
     tr=shape(t['layers']['F.Cu']).intersection(reference.buffer(-.152))
     if tr.is_empty:continue
     a,b=nearest_points(gr,tr);gp,_=astar(list(a.coords)[0],list(b.coords)[0],gb,reference,.3,margin=2,step=.15)
     if gp:target=t['uuid'];break
    if not gp:
     gc=pads['2'].centroid;vcandidates=sorted(([gc.x+dx*.25,gc.y+dy*.25] for dx in range(-8,9) for dy in range(-8,9)),key=lambda p:math.dist(p,[gc.x,gc.y]))
     for pos in vcandidates:
      pt=Point(pos)
      if viaforbidden.intersects(pt) or not reference.covers(pt.buffer(.35)) or pt.distance(body)<.402 or pt.distance(sgeom)<.502:continue
      a=nearest_points(gr,pt)[0];gp,_=astar(list(a.coords)[0],pos,gb,reference,.3,margin=2,step=.15)
      if gp:v={'position_mm':pos,'size_mm':.6,'drill_mm':.3,'net':'PWR_AGND'};break
    if gp:
     chosen={'capacitor':cap,'driver':ic,'position_mm':center,'orientation_degrees':angle,'removed_positive_track_uuids':cut,'removed_obsolete_ground_track_uuids':obsolete,'supply_path_mm':sp,'ground_path_mm':gp,'ground_target_uuid':target,'new_ground_via':v,'supply_length_mm':LineString(sp).length,'ground_length_mm':LineString(gp).length,'pad_centers_mm':{p:[g.centroid.x,g.centroid.y] for p,g in pads.items()},'native_courtyard_verified':False};break
   if chosen:break
  out.append({'capacitor':cap,'attempts':attempts,'chosen':chosen});print(cap,attempts,chosen,flush=True)
 result={'source_capture_sha256':sha(H/'capture-01/capture.json'),'planner_sha256':sha(Path(__file__)),'courtyards_sha256':sha(H/'courtyards.json'),'rows':out,'qualified':False};(H/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':run()
