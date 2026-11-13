"""Check translated C907 receiving allocation without shrinking any peer."""
import json
from pathlib import Path
from shapely.geometry import box
from ..ldo_local.immutable_inputs import sha
H=Path(__file__).resolve().parent;R=H.parent/'c13_receiving'
for source in json.loads((R/'receiving-sources.json').read_text()):assert sha(R/source['local_file'])==source['sha256']
c=json.loads((R/'receiving-capture.json').read_text());s=json.loads((R/'receiving-scope.json').read_text());excluded=set(json.loads((R/'receiving-base.json').read_text())['replaced_allocations']);refs={r[0] for r in s['rows']};peers=[r for r in c['component_envelopes']+c['tail_envelopes'] if r[0] not in refs|excluded]+s['rows'];old=next(r for r in s['rows'] if r[0]=='P_C907');new=[old[0],[old[1][0]-1,old[1][1],old[1][2]-1,old[1][3]],old[2]];conflicts=[]
for r in peers:
 if r[0]==old[0]:continue
 overlap=box(*new[1]).intersection(box(*r[1])).area*max(0,min(new[2][1],r[2][1])-max(new[2][0],r[2][0]))
 if overlap>0:conflicts.append([r[0],overlap])
assert not conflicts;ldo=next(r for r in peers if r[0]=='P_U102');result={'status':'PASS','candidate_board_sha256':sha(H/'inputs-review-02/power_protection.kicad_pcb'),'before':old,'after':new,'P_U102_gap_mm':box(*new[1]).distance(box(*ldo[1])),'peer_allocations_checked':len(peers)-1,'peer_conflicts':conflicts,'allowances_process_qualified':False,'qualified':False};(H/'receiving-review.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
