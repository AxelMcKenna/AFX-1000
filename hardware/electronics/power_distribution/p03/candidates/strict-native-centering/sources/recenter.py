from pathlib import Path
import sys,json,hashlib,copy,shutil,math
sys.path.insert(0,'/Users/axelmckrnna/dev/rmx-publish')
from hardware.electronics.common.sexpr import *
ROOT=Path('/private/tmp/afx-p03-strict-current');SOURCE=ROOT/'strict-db83';dest=ROOT/'centered1';dest.mkdir(exist_ok=True)
for p in SOURCE.iterdir():
 if p.is_dir():shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
 else:shutil.copy2(p,dest/p.name)
blob=(SOURCE/'power_p03.kicad_pcb').read_bytes();t=read_sexpr(blob.decode());nodes={str(first(n,'uuid')[1]):n for n in t if isinstance(n,list) and n and n[0] in ['segment','via'] and children(n,'uuid')};rows=json.load(open(ROOT/'centering-classification.json'));changes=[]
assert len({x['track_uuid'] for x in rows})==len(rows)==171
for row in rows:
 tr=nodes[row['track_uuid']];before=sexpr(tr);c=row['via'];s=row['start'];e=row['end'];radius=row['via_size']/2
 assert min(row['endpoint_distance'])<=radius+1e-9
 if max(row['endpoint_distance'])<=radius+1e-9:
  t.remove(tr);action='remove centreline fullyinside same-net via pad; no electricalendpointoutsidevia'
 else:
  key='start' if row['endpoint_distance'][0]<row['endpoint_distance'][1] else 'end';node=first(tr,key)
  node[1:3]=read_sexpr(f'(at {c[0]:.9f} {c[1]:.9f})')[1:3];action='snap '+key+' toexistingviacentre'
 changes.append(dict(action=action,source_track_uuid=row['track_uuid'],via_uuid=row['via_uuid'],net=row['net'],via_size=row['via_size'],original_endpoint_offset_mm=min(row['endpoint_distance']),original_object=before,new_object=None if tr not in t else sexpr(tr)))
(dest/'power_p03.kicad_pcb').write_text(sexpr(t)+'\n')
# No new vias, footprints, zones, edgecuts, or rule values. Sourcegeometry and
# same-face critical loop contracts need independent renewal after centering.
assert [sexpr(n) for n in children(t,'via')]==[sexpr(n) for n in children(read_sexpr(blob.decode()),'via')]
assert [sexpr(n) for n in children(t,'footprint')]==[sexpr(n) for n in children(read_sexpr(blob.decode()),'footprint')]
report=dict(source_pcb_sha256=hashlib.sha256(blob).hexdigest(),source_strict_report_sha256=hashlib.sha256((ROOT/'strict-drc.json').read_bytes()).hexdigest(),changes=changes,
 source_count=171,modified_tracks=sum(x['new_object'] is not None for x in changes),removed_inside_via_tracks=sum(x['new_object'] is None for x in changes),
 all_vias_and_all_FPs_exact=True,all_existing_track_widths_and_nets_preserved=True,rule_values_unchanged=True,
 actual_ground_thermal_force_feedback_model_must_be_renewed=True,
 literal_aux_and_buck_link_proofs_NOT_inherited=True,
 engineering_filled_capped_receiving_requirement_not_process_acceptance=True,
 no_physical_or_current_or_thermal_qualification=True)
(ROOT/'centering1-delta.json').write_text(json.dumps(report,indent=2)+'\n')
print('modified',report['modified_tracks'],'removed',report['removed_inside_via_tracks'])
