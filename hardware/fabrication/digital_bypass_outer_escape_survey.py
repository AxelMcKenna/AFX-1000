"""Look for a BYPASS_SENSE escape while preserving all ground/thermal copper."""
import copy,json,math
from pathlib import Path
from shapely.geometry import LineString
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
ROOT=Path(__file__).resolve().parent
REMOVED={'af606d42-b58e-5757-9568-378377db938e','b30f01e6-b9f7-54aa-9d6a-2761e55ac0e2','169e771c-c1c3-4b76-988a-dd2d411f24f8','6bede44e-44ec-43a7-8ed5-9b0649087a5b'}
def run():
 cp=ROOT/'staging/digital-blank-codec-inputs-32/capture.json';cap=json.loads(cp.read_text())
 assert all(sha(Path(p))==h for p,h in cap['source_sha256'].items())
 work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in REMOVED]
 surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=DigitalViaScreen(work,signal_layers=surface.SIGNAL_LAYERS)
 net='BYPASS_SENSE';start=[98.15,34.635];options=[];tested=0
 for x in [99+i*.1 for i in range(51)]:
  for y in [24+i*.1 for i in range(61)]:
   tested+=1;p=[round(x,6),round(y,6)]
   if not screen.via_legal(net,p):continue
   for path in ([start,[p[0],start[1]],p],*surface.candidate_paths(start,p)):
    if screen.legal(net,'B.Cu',path):
     options.append(dict(point_mm=p,runs=[('B.Cu',path)],vias=[p],length_mm=LineString(path).length));break
 options.sort(key=lambda r:r['length_mm'])
 paths=[cp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_via_spacing_v2.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','nf_minimum_logic.py','route_nf_surface.py')]
 out=ROOT/'staging/digital-bypass-outer-escape-survey-01';out.mkdir(exist_ok=False)
 result=dict(source_sha256={str(p):sha(p) for p in paths},removed_track_uuids=sorted(REMOVED),grid_points_tested=tested,legal_options=options,all_ground_thermal_copper_preserved=True,restoration_and_global_connection_not_established=True,candidate_emitted=False,fabrication_released=False)
 (out/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
 print('Legal outer escapes:',len(options),'best:',options[:3],flush=True)
if __name__=='__main__':run()
