"""Full original contacts/reference and exact foreign fills, independent of DRC."""
import json
from pathlib import Path
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..vin_escape.verify import saved_fill
from ..routed.plan import shape,sha
H=Path(__file__).resolve().parent
src=read_sexpr((H/'inputs-IN-slot-01/power_protection.kicad_pcb').read_text());dst=read_sexpr((H/'local-IN-slot-01.kicad_pcb').read_text());zones=lambda t:{str(first(z,'uuid')[1]):z for z in children(t,'zone')};a,b=zones(src),zones(dst);m=json.loads((H/'local-IN-slot-01.json').read_text());allowed={r['uuid'] for r in m['zones']};c=json.loads((H/'capture-02/capture.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());quiet={r['zone_uuid'] for r in q['plane_exclusions']};retained=[];contacts=[];lost=[]
for uid,z in a.items():
 if uid not in allowed:assert z==b[uid],uid;continue
 old,new=saved_fill(z),saved_fill(b[uid]);layer=str(first(z,'layer')[1]);assert str(first(z,'net')[1])=='PWR_AGND'
 for o in c['objects']:
  if o.get('ref')=='P_C907':continue
  if o['net']=='PWR_AGND' and layer in o['layers']:
   copper=shape(o['layers'][layer]);prior=old.intersection(copper).area
   if prior>1e-9:
    reduction=prior-new.intersection(copper).area;assert reduction<1e-9,(uid,o['uuid'],reduction);contacts.append([uid,o['uuid'],prior])
for layer,reference in [('F.Cu','In1.Cu'),('B.Cu','In6.Cu')]:
 old=unary_union([saved_fill(z) for uid,z in a.items() if str(first(z,'layer')[1])==reference and str(first(z,'net')[1])=='PWR_AGND' and uid not in quiet]);new=unary_union([saved_fill(z) for uid,z in b.items() if str(first(z,'layer')[1])==reference and str(first(z,'net')[1])=='PWR_AGND' and uid not in quiet])
 for o in c['objects']:
  if o['kind']!='PCB_TRACK' or layer not in o['layers'] or o['uuid'] in json.loads((H/'manifest-IN-slot-01.json').read_text())['removed_owned_track_UUIDs']:continue
  g=shape(o['layers'][layer]);loss=g.intersection(old).difference(new).area
  if loss>1e-9:lost.append([o['uuid'],layer,loss])
  retained.append(o['uuid'])
r={'status':'PASS' if not lost else 'FAIL','original_ground_contacts_checked':len(contacts),'original_track_references_checked':len(retained),'lost_original_track_reference':lost,'candidate_sha256':sha(H/'local-IN-slot-01.kicad_pcb'),'source_capture_sha256':sha(H/'capture-02/capture.json'),'contacts':contacts,'no_foreign_fill_change':True,'qualified':False};(H/'local-check.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='contacts'});assert not lost
