"""Review saved PD diagnostic fields; explicitly not a route acceptance gate."""
import json,hashlib
from pathlib import Path
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;d=json.loads((R/'native-probe-r138-recapture/fields.json').read_text());c=json.loads((R/'capture-r131/capture.json').read_text());f={k:unary_union([shape(z['polygons'])for z in d[k]if z['net']=='LINK_AGND'and z['layer']=='In1.Cu'])for k in ['before','after']};rows=[]
for o in c['objects']:
 if o['kind']=='PCB_TRACK'and o['net']=='/A_ADC/NBIAS_R'and o['layers'].get('F.Cu'):
  covered=shape(o['layers']['F.Cu']).intersection(f['before']);loss=covered.difference(f['after']);res=covered.difference(f['after'].buffer(.005))
  rows.append({'uuid':o['uuid'],'prior_coverage_mm2':covered.area,'raw_loss_mm2':loss.area,'after_5um_tolerance_loss_mm2':res.area})
paths=[Path(__file__),R/'native-probe-r138-recapture/fields.json',R/'native-probe-r138/diagnostic-only.kicad_pcb',R/'pd_native_probe_r138.py',R/'pd_native_recapture_r138.py',R/'capture-r131/capture.json']
out={'diagnostic_only':True,'routing_candidate_acceptable':False,'removed_copper_requires_exact_replacement':d['removed_without_replacement'],'via_at':[75.8,77.65],'NBIAS_R_reference_cases':rows,'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}}
(R/'pd-probe-review-r138.json').write_text(json.dumps(out,indent=2)+'\n');assert all(x['raw_loss_mm2']<1e-9 for x in rows);print('PASS diagnostic: no NBIAS_R reference loss; no route accepted')
