"""Survey remaining nets from complete native groups, including existing track interiors."""
import json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_sampled_group_contacts import contacts
from hardware.fabrication.digital_region_reachability import reachability
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers
ROOT=Path(__file__).resolve().parent

def run():
 cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json';wp=ROOT/'staging/digital-bypass-ground-signal-native-02/stage-connectivity-review.json'
 cap,witness=[json.loads(p.read_text()) for p in (cp,wp)]
 for r in (cap,witness):assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
 nets=[r['net'] for r in witness['nets'] if not r['all_pads_connected']];assert len(nets)==31
 surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;faces=surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 screen=CloseMarginViaScreen(cap,signal_layers=faces);results=[]
 for net in nets:
  objects=[o for o in cap['objects'] if o['net']==net];groups={o['group'] for o in objects};assert len(groups)==2 and None not in groups
  a=next(o for o in objects if o['kind']=='PAD');b=next(o for o in objects if o['kind']=='PAD' and o['group']!=a['group'])
  starts=contacts(cap,b,faces);ends=contacts(cap,a,faces)
  crossings=[(o['position_mm'],[f for f in faces if o['layers'].get(f)]) for o in objects if o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0]))]
  r=reachability(screen,net,sorted(starts),sorted(ends),faces,existing_crossings=crossings)
  r.update(net=net,source_group=a['group'],target_group=b['group'],sampled_source_contacts=len(starts),sampled_target_contacts=len(ends),existing_conductive_crossings=len(crossings));results.append(r)
  print(net,'native-group regional access:',r['connected'],flush=True)
 paths=[cp,wp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_sampled_group_contacts.py','digital_native_route_cleanup.py','digital_region_reachability.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
 out=ROOT/'staging/digital-native-group-regions-31-01';out.mkdir(exist_ok=False)
 report=dict(source_sha256={str(p):sha(p) for p in paths},results=results,connected_nets=[r['net'] for r in results if r['connected']],sampled_track_step_mm=.2,planner_track_margin_mm=.001,no_copper_omitted=True,native_rules_relaxed=False,joint_route_feasibility_not_established=True,not_proof_of_global_routing_infeasibility=True,candidate_emitted=False,fabrication_released=False)
 (out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Native-group survey complete:',len(report['connected_nets']),'potentially connected nets',flush=True)
if __name__=='__main__':run()
