"""Repair the measured upper INPUT_ENABLE reference gap without a waiver."""
import copy,hashlib,json
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union
from hardware.fabrication import route_nf_surface as S
R=Path(__file__).resolve().parent;plan=json.loads((R/'pd-join-r145.json').read_text());r=json.loads((R/'candidate-r146/routing.json').read_text());c=json.loads((R/'capture-r146/capture.json').read_text());net='/A_BYPASS/INPUT_ENABLE';row=next(x for x in plan['exact_three_authorized_replacements']if x['net']==net);old=next(x for x in r['routes']if x['net']==net);capture=copy.deepcopy(c);capture['objects']=[o for o in capture['objects']if o['uuid']not in old['added_track_uuids']];capture['zones']=[z for z in capture['zones']if z['keepout']or z['net']!='LINK_AGND'];S.SIGNAL_LAYERS=('In2.Cu',);screen=S.Screen(capture)
path=[[75.7,75.5],[75.2,75.5],[75.2,76.5],[75.15,77.0],[75.15,79.2],[75.6,79.2]];assert screen.legal(net,'In2.Cu',path)
field=unary_union([S.shape(z['polygons'])for z in c['zones']if z['net']=='LINK_AGND'and z['layer']in ['In1.Cu','In3.Cu']and not z['keepout']]).buffer(2e-6);assert LineString(path).buffer(.1).difference(field).area<1e-6
row.update(path_mm=path,after_length_mm=LineString(path).length,refinement='Upper dogleg at X75.2; lower corridor X75.15 retained; r146 measured uncovered corner removed')
plan['source_sha256']={str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),R/'pd-join-r145.json',R/'candidate-r146/routing.json',R/'capture-r146/capture.json',R/'reference-review-r146.json']};o=R/'pd-refined-r147.json';assert not o.exists();o.write_text(json.dumps(plan,indent=2)+'\n');print('PASS exact upper dogleg has full captured reference; length',LineString(path).length)
