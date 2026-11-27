import csv,json,hashlib
from pathlib import Path
b=Path('hardware/qualification/two_board_aux_current_08'); out=b/'package_envelopes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bom={r['Reference']:r for r in csv.DictReader((b/'footprint_identity/candidate-bom.csv').open())}
bom['P_C907']={'MPN':'C0603C105K3RACTU','Datasheet':'https://search.kemet.com/component-documentation/download/specsheet/C0603C105K3RACTU'}
added='P_C906 E_C900 P_C902 P_L900 P_R902 P_C904 P_C900 P_R903 P_U901 P_R900 P_C903 E_U900 P_U902 P_C905 P_R901 P_C901 P_U900 E_R900 P_C907'.split()
changed='E_C13 E_C29 E_C36 E_C9 E_R83 E_R84 E_R88 E_R89 P_C109 P_R108 P_R117 P_R118 P_R119'.split()
spec={}
def add(refs,dims,source,location,basis):
 for ref in refs.split():spec[ref]={'reference':ref,'mpn':bom[ref]['MPN'],'max_envelope_mm':dims,'source':source,'source_sha256':sha(b/source),'url':bom[ref]['Datasheet'],'location':location,'dimensional_basis':basis}
for p in json.loads((b/'placement/footprints.json').read_text())['parts']:
 add(' '.join(p['references']),p['body_max_mm'],p['source'],'PDF pages '+str(p['pdf_pages']),p['note'])
add('P_C902 P_C905',[7.6,4.6,3.1],'held_rail/primary/t520d227m010ate025.pdf','page1 Dimensions','L7.3±0.3 W4.3±0.3 H2.8±0.3')
add('E_C13 E_C29 E_C36 E_C9',[2.2,1.45,.88],'held_cutover/primary/c0805c104k5ractu.pdf','page1 Dimensions','L2±.2 W1.25±.2 T.78±.10')
add('P_C109',[2.2,1.45,.88],'metadata/primary/c0805c681j5gactu.pdf','page1 Dimensions','L2±.2 W1.25±.2 T.78±.10')
add('E_C900 P_C903 P_C906',[1.75,.95,.95],'package_envelopes/primary/c0603c104k5ractu.pdf','page1 Dimensions','L1.6±.15 W.8±.15 T.8±.15')
add('P_C907',[1.75,.95,.95],'ldo_local/primary/c0603c105k3ractu.pdf','page1 Dimensions','L1.6±.15 W.8±.15 T.8±.15')
add('E_R900 P_R900 P_R901 P_R903 P_R108 P_R117 P_R118 P_R119',[2.1,1.4,.55],'schematic_candidate/primary/tnpw-e3.pdf','Dimensions and mass, TNPW0805 row','L2±.1 W1.25±.15 H.45±.10')
add('E_R83 E_R84 E_R88 E_R89',[2.1844,1.397,.8382],'precision/primary/plt.pdf','page2 Dimensions,0805 row','Inches L.080±.006 W.050±.005 T.015 to .033; multiply upper limits by25.4')
for refs,mpn,dim,text in [('P_C900 P_C904','C3216X7R1H225K160AB',[3.4,1.8,1.8],'L3.20±.20 W1.60±.20 T1.60±.20'),('P_C901','C3225X7R1C226K250AC',[3.6,2.8,2.8],'L3.20±.40 W2.50±.30 T2.50±.30')]:
 source='package_envelopes/primary/'+mpn+'.json'
 (b/source).write_text(json.dumps({'url':bom[refs.split()[0]]['Datasheet'],'retrieved':'2026-11-13','method':'Primary TDK page retrieved with web tool; direct HTML/PDF cache HTTP403. This is a transcribed observation, not original HTML.','section':'Size','dimension_text_mm':text,'status':'Production (NRND)' if '3225' in mpn else 'Production'},indent=2)+'\n')
 add(refs,dim,source,'Primary product page Size',text)
data={'status':'package bounds only; assembly and housing acceptance conditional','source_board':'reference_fix/inputs-reference-09/power_protection.kicad_pcb','source_board_sha256':sha(b/'reference_fix/inputs-reference-09/power_protection.kicad_pcb'),'bom_source':'footprint_identity/candidate-bom.csv','bom_sha256':sha(b/'footprint_identity/candidate-bom.csv'),'added_references':added,'changed_mpn_references':changed,'allowances':{'solder_height_mm':None,'placement_xy_mm':None,'tilt_degrees':None,'board_warp_mm':None,'meaning':'Not bounded by these component sheets. Use separately declared process/mechanical allowances; do not infer zero or reuse package-code typical heights. Package envelopes include component terminals where stated but exclude assembled solder standoff.'},'parts':[spec[r] for r in sorted(added+changed)]}
(out/'envelopes.json').write_text(json.dumps(data,indent=2)+'\n')
print(len(data['parts']))
