"""Report full selected-native fill deltas without accepting them."""
import json
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from hardware.qualification.two_board_aux_current_08.vin_escape.verify import saved_fill
H=Path(__file__).resolve().parent
old=read_sexpr((H/'inputs-IN-slot-01/power_protection.kicad_pcb').read_text());new=read_sexpr((H/'native-IN-slot-01/selected-fill.kicad_pcb').read_text())
zs=lambda b:{str(first(z,'uuid')[1]):z for z in children(b,'zone')}
a,b=zs(old),zs(new);assert set(a)==set(b)
rows=[]
for uid,z in a.items():
 p,q=saved_fill(z),saved_fill(b[uid]);removed=p.difference(q);added=q.difference(p)
 if removed.area+added.area>1e-9: rows.append({'uuid':uid,'net':str(first(z,'net_name')[1]) if children(z,'net_name') else str(first(z,'net')[1]),'removed_mm2':removed.area,'added_mm2':added.area,'removed_bounds':list(removed.bounds),'added_bounds':list(added.bounds)})
r={'status':'diagnostic only','changed_zones':rows,'foreign_zone_change':any(x['net']!='PWR_AGND' for x in rows)}
(H/'native-IN-slot-01/fill-delta-diagnostic.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
