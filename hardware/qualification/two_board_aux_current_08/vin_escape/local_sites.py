"""Screen off-track paired via sites for an explicit short F.Cu source stub."""
import json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from shapely.prepared import prep
from ..routed.plan import sha,shape
H=Path(__file__).resolve().parent;SRC=H.parent/'main_feeds';NET='/P_power_supply/VIN_IC';GROUP='04693f6e-fbbf-53d2-8cb7-16d7e4b68b5a'
def run():
 c=json.loads((SRC/'capture-01/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quiet=set(q['retained_object_uuids']);quietz={z['zone_uuid'] for z in q['plane_exclusions']};tracks=[o for o in c['objects'] if o['group']==GROUP and o['kind']=='PCB_TRACK' and 'In5.Cu' in o['layers']];refs={l:unary_union([shape(z['polygons']) for z in c['zones'] if z['layer']==l and z['net']=='PWR_AGND' and z['uuid'] not in quietz and not z['keepout']]) for l in ['In1.Cu','In6.Cu']};pads=[shape(ps).buffer(.402) for o in c['objects'] if o['kind']=='PAD' for ps in o['layers'].values()]
 def forbid(net,ground_cut):
  return prep(unary_union([shape(ps).buffer(.502) for o in c['objects'] if o['net']!=net or o['uuid'] in quiet for ps in o['layers'].values()]+pads+[shape(z['authored_outline'] if z['keepout'] or z['uuid'] in quietz else z['polygons']).buffer(.502) for z in c['zones'] if z['keepout'] or z['uuid'] in quietz or (z['net']!=net and not(ground_cut and z['net']=='PWR_AGND'))]))
 vf=forbid(NET,True);gf=forbid('PWR_AGND',False);rows=[]
 for xx in range(1890,1981,2):
  for yy in range(1160,1291,2):
   xy=[xx/10,yy/10];point=Point(xy)
   if vf.intersects(point) or not all(g.covers(point.buffer(.31)) for g in refs.values()):continue
   paired=[]
   for dx,dy in [(x*.1,y*.1) for x in range(-9,10) for y in range(-9,10) if .81<math.hypot(x*.1,y*.1)<1]:
    rp=[xy[0]+dx,xy[1]+dy];rpoint=Point(rp)
    if not gf.intersects(rpoint) and all(g.covers(rpoint.buffer(.31)) for g in refs.values()):paired.append(rp)
   if paired:rows.append({'vin_via_mm':xy,'return_sites_mm':paired,'pair_count':len(paired),'cutback_zone_uuids':sorted(z['uuid'] for z in c['zones'] if z['net']=='PWR_AGND' and z['uuid'] not in quietz and shape(z['polygons']).intersects(point.buffer(.502)))})
 result={'capture_sha256':sha(SRC/'capture-01/capture.json'),'script_sha256':sha(Path(__file__)),'source_group':GROUP,'source_tracks':len(tracks),'legal_paired_sites':rows,'all_non_AGND_foreign_fills_preserved':True,'qualified':False};(H/'local-sites.json').write_text(json.dumps(result,indent=2)+'\n');print('paired VIN sites',len(rows));print(rows[:3])
if __name__=='__main__':run()
