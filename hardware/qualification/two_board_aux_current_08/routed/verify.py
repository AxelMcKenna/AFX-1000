"""Verify an isolated native checkpoint without treating known rule errors as approval."""
import json,hashlib,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:AUX-ROUTED-01:'+s))
def audit_groups(report,plan):
 before={(g['net'],tuple(g['members'])) for g in report['before_groups']};old={u for _,ms in before for u in ms}
 after={(g['net'],tuple(sorted(set(g['members'])&old))) for g in report['after_groups'] if set(g['members'])&old}
 assert before==after,'Original native connectivity delta'
 membership={u:i for i,g in enumerate(report['after_groups']) for u in g['members']}
 main=membership['6374938c-2e28-5b13-9764-9176d6fa9230']
 for r in plan['routes']:
  start=uid(r['source'])
  if r['net']=='PWR_AGND':assert membership[start]==main,'Return not anchored to main ground'
  else:assert membership[start]==membership[uid(r['target'])],'Local route not natively connected'
 for v in plan['new_vias']:assert membership[uid('via:'+v['name'])]==main,'Via missing main-ground contact'
 return len(before)
def verify(root,here=HERE):
 out=here/'native-04';r=json.loads((out/'review.json').read_text());p=json.loads((here/'plan.json').read_text());d=json.loads((out/'drc.json').read_text())
 assert sha(here/'plan.json')==r['plan_sha256']
 for name,digest in r['artifact_sha256'].items():assert sha(out/name)==digest,('Artifact drift',name)
 paths={'baseline_pcb':root/'hardware/fabrication/staging/two-board-power-aux-local-distribution-native-03/power_protection.kicad_pcb','baseline_capture':root/'hardware/fabrication/staging/two-board-power-routing-inputs-aux-local-distribution-03/capture.json','placement_baseline':here.parent/'placement/individual-placement.json','placement':here/'placement.json','native_poses':here.parent/'placement/native/native-poses.json','netlist':here.parent/'held_rail/native-03/candidate-netlist.xml'}
 for name,path in paths.items():assert sha(path)==p['source_sha256'][name],('Source drift',name)
 for name,f in r['derived_footprints'].items():assert sha(out/'libraries/AUX_ROUTE.pretty'/(name+'.kicad_mod'))==f['derived_sha256']
 assert r['all_original_fills_preserved'] and r['all_original_pad_and_track_states_preserved']
 assert not d['ignored_checks'];assert len(d['violations'])==4
 assert all(v['type']=='clearance' and v['severity']=='error' and 'actual 0.1500 mm' in v['description'] and all(('E_U900' in i['description'] or 'P_U902' in i['description']) for i in v['items']) for v in d['violations']),'Unexpected native DRC violation'
 count=audit_groups(r,p);c=json.loads(paths['baseline_capture'].read_text());objects={o['uuid']:o for o in c['objects']}
 from .identity import reconcile
 snapshot=json.loads((out/'pad-identities.json').read_text());aliases=json.loads((here/'anonymous-pad-mapping.json').read_text())
 assert snapshot['source_sha256']==p['source_sha256']['baseline_pcb'] and snapshot['candidate_sha256']==r['artifact_sha256']['power_protection.kicad_pcb']
 assert aliases['native_identity_sha256']==sha(out/'pad-identities.json') and aliases['capture_sha256']==sha(paths['baseline_capture'])
 mappings=reconcile(snapshot,c);assert mappings==aliases['mappings'];remap={m['capture_uuid']:m['candidate_uuid'] for m in mappings}
 expected={(objects[ms[0]]['net'],tuple(sorted(remap.get(u,u) for u in ms))) for ms in c['all_groups'].values()};actual={(g['net'],tuple(g['members'])) for g in r['before_groups']};assert expected==actual,'Baseline capture/native groups disagree'
 # Compare complete raw authored outlines and filled polygons, including all holes/slits.
 from hardware.electronics.common.sexpr import read_sexpr,children,first,Atom
 def canonical(n):
  if isinstance(n,list):return [canonical(x) for x in n]
  if isinstance(n,Atom):
   try:return float(n)
   except ValueError:return str(n)
  return n
 def zones(path):
  b=read_sexpr(path.read_text());return {str(first(z,'uuid')[1]):canonical(children(z,'polygon')+children(z,'filled_polygon')) for z in children(b,'zone')}
 assert zones(paths['baseline_pcb'])==zones(out/'power_protection.kicad_pcb'),'Original zone outline/fill drift'
 visual=json.loads((here/'visual-review.json').read_text())
 for field in ['source_sha256','artifact_sha256']:
  for name,digest in visual[field].items():assert sha(here/name)==digest
 assert visual['visually_inspected'] and visual['native_geometry_rendered']
 quiet=json.loads((here/'quiet-exclusion.json').read_text())
 for name,digest in quiet['source_sha256'].items():assert sha((root/name) if name.startswith('hardware/') else here/name)==digest
 assert quiet['quiet_network_count']==7 and quiet['new_contacts_with_retained_quiet_pass_ground_copper']==0
 assert not p['failures'] and all(x['reference_uncovered_mm2']==0 for x in p['routes'])
 return dict(original_native_groups_preserved=count,anonymous_physical_pad_mappings=len(mappings),explicit_pad_identities_preserved=snapshot['explicit_source_pads_checked'],local_routes_connected=len(p['routes']),anchored_ground_vias=len(p['new_vias']),original_plane_fills_preserved=True,added_tracks=r['added_tracks'],native_opens=r['opens_after'],unresolved_native_errors=4,native_warnings=0,existing_supply_cutover=False,held_rail_routed=False,fabrication_qualified=False)
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('root',type=Path);result=verify(a.parse_args().root);(HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
