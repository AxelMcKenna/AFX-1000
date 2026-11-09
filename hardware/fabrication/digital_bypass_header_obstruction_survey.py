"""Check global header access after the complete local BYPASS escape repairs."""
import copy,json,time
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import LineString,box
from collections import defaultdict
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_bypass_ground_signal_repair import SIGNAL_REMOVED,GROUND_TRACK,GROUND_VIA,polys
from hardware.fabrication.digital_sampled_group_contacts import contacts as other_group_contacts
from hardware.fabrication.digital_via_spacing_v2 import DigitalViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_continuous_net_route import route
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
ROOT=Path(__file__).resolve().parent

def run():
 cp=ROOT/'staging/digital-blank-codec-inputs-32/capture.json';rp=ROOT/'staging/digital-bypass-ground-signal-repair-01/construction.json'
 cap,recipe=[json.loads(p.read_text()) for p in (cp,rp)]
 for r in (cap,recipe):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
 ground=recipe['ground_relocation'];work=copy.deepcopy(cap);work['objects']=[o for o in work['objects'] if o['uuid'] not in SIGNAL_REMOVED]
 for o in work['objects']:
  if o['uuid']==GROUND_TRACK:
   o['position_mm']=ground['track_start_mm'];o['end_mm']=ground['track_end_mm'];o['layers']={'F.Cu':polys(LineString([o['position_mm'],o['end_mm']]).buffer(.5,quad_segs=64))}
  if o['uuid']==GROUND_VIA:
   p=ground['via_point_mm'];old=o['position_mm'];o['layers']={f:polys(translate(surface.shape(ps),p[0]-old[0],p[1]-old[1])) for f,ps in o['layers'].items()};o['position_mm']=p;o['drill_mm']=[.3,.3]
 surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.01;faces=surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=DigitalViaScreen(work,signal_layers=faces)
 fixed=recipe['routes'][:3]
 for r in fixed:add(screen,r['net'],dict(runs=r['runs'],vias=[] if r['net']=='CODEC_RUN' else r['new_vias_mm']))
 net='BYPASS_SENSE';via=recipe['routes'][0]['new_vias_mm'][0]
 source=next(o for o in work['objects'] if o.get('ref')=='U2003' and o.get('pin')=='22');contacts=other_group_contacts(work,source,faces)
 crossings=[(o['position_mm'],[f for f in faces if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
 crossings += [(via,list(faces))]
 groups=defaultdict(list);local=box(69,18,75,24)
 for o in work['objects']:
  if o['kind']=='PCB_TRACK' and o['width_mm']==.2 and o['net'] not in (net,'AGND','5V_DIG','V3V3_IO') and any(surface.shape(ps).intersects(local) for ps in o['layers'].values()):groups[o['net']].append(o['uuid'])
 results=[]
 for omitted,ids in sorted(groups.items(),key=lambda r:(len(r[1]),r[0])):
  trial=copy.deepcopy(work);trial['objects']=[o for o in trial['objects'] if o['uuid'] not in ids]
  screen=DigitalViaScreen(trial,signal_layers=faces)
  for r in fixed:add(screen,r['net'],dict(runs=r['runs'],vias=[] if r['net']=='CODEC_RUN' else r['new_vias_mm']))
  frozen=PlannedRegionScreen(screen,net)
  report=reachability(frozen,net,[(f,via) for f in faces],sorted(contacts),faces,existing_crossings=crossings)
  report.update(omitted_net=omitted,omitted_track_uuids=ids,restoration_not_established=True)
  results.append(report);print('Header access omitting',len(ids),omitted,'tracks:',report['connected'],flush=True)
 paths=[cp,rp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_bypass_ground_signal_repair.py','digital_sampled_group_contacts.py','digital_native_route_cleanup.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','digital_planned_region_screen.py','digital_region_reachability.py','digital_continuous_net_route.py','digital_polygon_path.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
 out=ROOT/'staging/digital-bypass-header-obstruction-survey-01';out.mkdir(exist_ok=False)
 with (out/'diagnosis.json').open('x') as f:json.dump(dict(source_sha256={str(p):sha(p) for p in paths},results=results,local_box_mm=[69,18,75,24],candidate_emitted=False,all_other_repaired_routes_fixed=True,fabrication_released=False),f,indent=2);f.write('\n')
if __name__=='__main__':run()
