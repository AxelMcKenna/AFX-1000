"""Geometric analog proximity screen; no inferred parasitic capacitance or noise pass."""
import json,hashlib,math
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape
R=Path(__file__).resolve().parent;c=json.loads((R/'capture-r7/capture.json').read_text());r=json.loads((R/'candidate-r7/routing.json').read_text());rows=[]
for net in ['/A_INPUT/BUF_IN_L','/A_INPUT/BUF_IN_R']:
 tracks=[o for o in c['objects']if o['kind']=='PCB_TRACK'and o['net']==net];others=[o for o in c['objects']if o['kind']=='PCB_TRACK'and o['net']!=net and ('BUF_OUT'in o['net']or o['net']in ['A__P12','A__N12','A__V5_REG']or(o['net'].startswith('/A_INPUT/')and o['net'].endswith('_R'if net.endswith('_L')else'_L')))]
 pairs=[]
 for a in tracks:
  layer=next(iter(a['layers']));line=LineString([a['position_mm'],a['end_mm']])
  for b in others:
   if not b['layers'].get(layer):continue
   other=LineString([b['position_mm'],b['end_mm']]);d=line.distance(other)
   if d<1.000001:pairs.append({'input_track':a['uuid'],'other_track':b['uuid'],'other_net':b['net'],'layer':layer,'minimum_center_distance_mm':d,'input_length_within_1mm':line.intersection(other.buffer(1)).length})
 rows.append({'net':net,'native_total_trace_length_mm':sum(math.dist(o['position_mm'],o['end_mm'])for o in tracks),'signal_vias':sum(o['net']==net and o['kind']=='PCB_VIA'for o in c['objects']),'same_layer_proximity_cases':pairs})
old=json.loads((R/'candidate-r6/routing.json').read_text());p=LineString(next(v['path_mm']for v in old['routes']if v['net']=='/A_INPUT/BUF_IN_L'and v['layer']=='In3.Cu'));q=LineString(next(v['path_mm']for v in old['routes']if v['net']=='/A_INPUT/HP_SRC_R'and v['layer']=='In3.Cu'))
assert next(v['layer']for v in r['routes']if v['net']=='/A_INPUT/HP_SRC_R'and v['role']=='join')=='In5.Cu'
paths=[Path(__file__),R/'capture-r7/capture.json',R/'candidate-r7/routing.json',R/'candidate-r6/routing.json',R/'native-r7/review.json',R.parents[3]/'hardware/electronics/input_range/README.md']
report={'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'input_proximity':rows,'corrected_r6_opposite_channel_parallel_run':{'minimum_center_distance_mm':p.distance(q),'input_length_within_1mm':p.intersection(q.buffer(1)).length,'fix':'Move right pre-coupling route In3 to In5, retaining actual In4 ground between channels; native reference proof separately required'},'no_semiconductor_or_parasitic_simulation':True,'noise_stability_crosstalk_qualified':False}
(R/'analog-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows,indent=2))
