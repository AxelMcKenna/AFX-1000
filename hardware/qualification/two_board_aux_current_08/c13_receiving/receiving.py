"""Keep existing receiving bounds and screen translated C13 against all peers."""
import json,hashlib
from pathlib import Path
from shapely.geometry import box
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for s in json.loads((H/'receiving-sources.json').read_text()):assert sha(H/s['local_file'])==s['sha256']
c=json.loads((H/'receiving-capture.json').read_text());s=json.loads((H/'receiving-scope.json').read_text());excluded=set(json.loads((H/'receiving-base.json').read_text())['replaced_allocations']);refs={r[0] for r in s['rows']};others=[r for r in c['component_envelopes']+c['tail_envelopes'] if r[0] not in refs|excluded]+s['rows'];old=next(r for r in s['rows'] if r[0]=='E_C13');plan=json.loads((H/'plan.json').read_text())['rows'][0]['chosen'];dx,dy=[a-b for a,b in zip(plan['position_mm'],[108.275,129.095])];new=[old[0],[old[1][0]+dx,old[1][1]+dy,old[1][2]+dx,old[1][3]+dy],old[2]];failures=[]
for r in others:
 if r[0]=='E_C13':continue
 volume=box(*new[1]).intersection(box(*r[1])).area*max(0,min(new[2][1],r[2][1])-max(new[2][0],r[2][0]))
 if volume>0:failures.append({'reference':r[0],'volume_mm3':volume,'bounds':r})
cap=next(r for r in others if r[0]=='E_C16');gap=box(*new[1]).distance(box(*cap[1]));assert abs(gap-.455)<1e-9
r={'status':'PASS' if not failures else 'FAIL','old':old,'candidate':new,'C16':cap,'C16_receiving_gap_mm':gap,'all_peer_allocations_checked':len(others)-1,'peer_collisions':failures,'existing_envelope_preserved_by_translation':True,'source_xy_allowance_per_side_mm':s['xy_allowance_per_side_mm'],'source_height_allowance_mm':s['above_package_allowance_mm'],'allowances_qualified':False,'source_PDF_sha256':sha(H/'primary/fr.pdf'),'manufacturer_URL':'https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf','C16_mpn':'EEUFR1V221','C16_manufacturer_max_diameter_mm':8.5,'C16_manufacturer_max_body_height_mm':13.0,'manufacturer_pages':[1,5],'supplier_body_to_lead_centroid_registration_mm':None,'candidate_board_sha256':sha(H/'retained-candidate.kicad_pcb'),'qualified':False};(H/'receiving-review.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert not failures
