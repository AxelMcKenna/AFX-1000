"""Declare the complete old-net copper touching the eight shared supply/reset pads."""
import json,xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import Point
from ..routed.plan import shape,sha
H=Path(__file__).resolve().parent

def run():
 cp=H.parent/'bypass_local/capture-01/capture.json';c=json.loads(cp.read_text());netpath=H.parent/'held_cutover/native-03/candidate-netlist.xml';nets={(p.attrib['ref'],p.attrib['pin']):n.attrib['name'] for n in ET.parse(netpath).findall('./nets/net') for p in n.findall('node')};by={(o['ref'],o['pin']):o for o in c['objects'] if o.get('ref')};rows=[];cut=set()
 for ref,pin in [('E_U31','6'),('E_U31','8'),('E_C76','1'),('E_U29','8'),('E_C74','1'),('P_U102','5'),('P_U102','8'),('P_C102','1')]:
  p=by[ref,pin];assert p['net']!=nets[ref,pin];contacts=[]
  for o in c['objects']:
   if o['net']!=p['net'] or o['uuid']==p['uuid']:continue
   if any(shape(p['layers'][l]).intersects(shape(o['layers'][l])) for l in set(p['layers'])&set(o['layers'])):
    assert o['kind']=='PCB_TRACK';contacts.append(o['uuid']);cut.add(o['uuid'])
  assert contacts;rows.append({'ref':ref,'pin':pin,'uuid':p['uuid'],'old_net':p['net'],'new_net':nets[ref,pin],'old_group':p['group'],'touching_old_tracks':contacts})
 cut.add('7939af3a-030c-5147-a907-f9d2569a4ea2') # Native endpoint-dangling spur overlapping the retained parent trace.
 moved={r['uuid'] for r in rows};geoms={(o['uuid'],l):shape(polys) for o in c['objects'] for l,polys in o['layers'].items()};zonegeoms=[(z['net'],z['layer'],shape(z['polygons'])) for z in c['zones'] if not z['keepout']];pruned=[];reasons=[]
 relevant={r['old_group'] for r in rows};candidates=[o for o in c['objects'] if o['group'] in relevant and o['kind'] in ['PCB_TRACK','PCB_VIA']]
 for sweep in range(100):
  found=[]
  for o in candidates:
   if o['uuid'] in cut:continue
   layers=list(o['layers']);points=[o['position_mm']]+([o['end_mm']] if o['kind']=='PCB_TRACK' else []);contacts=[]
   for xy in points:
    pt=Point(xy).buffer(.000002);hitlayers=set()
    for other in c['objects']:
     if other['uuid'] in cut|moved|{o['uuid']} or other['net']!=o['net']:continue
     for layer in set(layers)&set(other['layers']):
      if pt.intersects(geoms[other['uuid'],layer]):hitlayers.add(layer)
    for net,layer,g in zonegeoms:
     if net==o['net'] and layer in layers and pt.intersects(g):hitlayers.add(layer)
    contacts.append(sorted(hitlayers))
   dead=(any(not x for x in contacts) if o['kind']=='PCB_TRACK' else len(contacts[0])<2)
   if dead:found.append(o['uuid']);reasons.append({'uuid':o['uuid'],'kind':o['kind'],'sweep':sweep,'remaining_endpoint_contact_layers':contacts})
  if not found:break
  cut.update(found);pruned.extend(found)
 else:raise AssertionError('Obsolete-tail pruning did not converge')
 out={'pruned_obsolete_tail_uuids':pruned,'prune_evidence':reasons,'source_capture_sha256':sha(cp),'netlist_sha256':sha(netpath),'planner_sha256':sha(Path(__file__)),'pin_moves':rows,'removed_track_uuids':sorted(cut),'qualified':False,'scope':'Isolation boundary only; new distribution and fast-reset routes still required'};(H/'plan.json').write_text(json.dumps(out,indent=2)+'\n');print(len(rows),len(cut))
if __name__=='__main__':run()
