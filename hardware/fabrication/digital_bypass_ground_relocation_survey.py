"""Screen an external thermal-via relocation without narrowing its 1 mm branch."""
import copy,json,math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_bypass_outer_escape_survey import REMOVED as SIGNAL_REMOVED
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
ROOT=Path(__file__).resolve().parent
GROUND_TRACK='c69d87f9-b134-552b-97be-347c7c20a818'
GROUND_VIA='1709749b-df70-5b29-a600-bf25408c657f'
REMOVED=SIGNAL_REMOVED|{GROUND_TRACK,GROUND_VIA}
def run():
 cp=ROOT/'staging/digital-blank-codec-inputs-32/capture.json';cap=json.loads(cp.read_text())
 dp=ROOT/'staging/digital-interface-hard-obstructions-32-01/diagnosis.json';diag=json.loads(dp.read_text())
 for r in (cap,diag):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
 escape=next(r for r in diag['results'] if r['net']=='BYPASS_SENSE')['options'][0]
 assert {o['uuid'] for o in escape['blockers']}==REMOVED
 work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in REMOVED]
 surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01;surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=DigitalViaScreen(work,signal_layers=surface.SIGNAL_LAYERS)
 add(screen,'BYPASS_SENSE',dict(runs=escape['runs'],vias=escape['via_points']))
 foreign=[surface.shape(o['layers']['F.Cu']) for o in work['objects'] if o['net']!='AGND' and o['layers'].get('F.Cu')]
 foreign += [Point(p).buffer(.3,quad_segs=64) for p in escape['via_points']]
 foreign += [surface.shape(z['polygons']) for z in work['zones'] if z['layer']=='F.Cu' and z['keepout'] and z['prohibit_tracks']]
 tree=STRtree(foreign);pad=next(o for o in work['objects'] if o.get('ref')=='U3004' and o.get('pin')=='33');land=surface.shape(pad['layers']['F.Cu'])
 options=[];tested=0
 for x in [96+i*.1 for i in range(51)]:
  for y in [24+i*.1 for i in range(33)]:
   tested+=1;p=[round(x,6),round(y,6)]
   if not screen.via_legal('AGND',p):continue
   for start in ([x,28.] for x in (98.,98.5,99.,99.5,100.,100.5,101.)):
    assert land.covers(Point(start))
    copper=LineString([start,p]).buffer(.5,quad_segs=64)
    if not screen.outline.covers(copper):continue
    if any(copper.distance(foreign[int(i)])<.21-1e-9 for i in tree.query(copper.buffer(.22))):continue
    options.append(dict(via_point_mm=p,track_start_mm=start,track_end_mm=p,track_width_mm=1.,track_length_mm=math.dist(start,p)))
 options.sort(key=lambda r:(r['track_length_mm'],math.dist(r['via_point_mm'],[100,27])))
 paths=[cp,dp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_bypass_outer_escape_survey.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py','nf_minimum_logic.py','route_nf_surface.py')]
 out=ROOT/'staging/digital-bypass-ground-relocation-survey-01';out.mkdir(exist_ok=False)
 report=dict(source_sha256={str(p):sha(p) for p in paths},removed_for_planning=sorted(REMOVED),escape=escape,ground_track_uuid=GROUND_TRACK,ground_via_uuid=GROUND_VIA,grid_points_tested=tested,legal_options=options,original_via_uuid_and_thermal_connectivity_must_be_retained=True,restoration_and_global_connection_not_established=True,candidate_emitted=False,fabrication_released=False)
 (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Ground relocation options:',len(options),'best:',options[:5],flush=True)
if __name__=='__main__':run()
