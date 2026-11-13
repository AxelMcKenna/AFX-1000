"""Source-bound retained-zone, ground-contact, quiet-exclusion and package checks."""
import json,os
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
from ..routed.plan import sha,shape
from hardware.electronics.common.sexpr import read_sexpr,children,first
from .preflight import zone_coordinates
H=Path(__file__).resolve().parent;OUT=H/'native-plane-04';BASE=H.parent/'shared_cutover/native-04'
def library_link(link,binding,root,expected):
 root=Path(root).resolve();link=Path(link);assert link.is_symlink() and os.readlink(link)==binding['relative_link'];target=link.resolve(strict=True);assert target.is_relative_to(root) and target==Path(expected).resolve(strict=True),'Library target escaped expected source'
 files={}
 for p in target.rglob('*'):
  assert p.resolve(strict=True).is_relative_to(root),'Nested library target escaped worktree'
  if p.is_file():files[str(p.relative_to(target))]=sha(p)
 assert files==binding['files_sha256'],'Library content changed or missing'
 return len(files)
def verify():
 r=json.loads((OUT/'review.json').read_text());p=json.loads((H/'plane-plan-03.json').read_text());gdata=json.loads((OUT/'new-zone-geometry.json').read_text());q=json.loads((H.parent/'routed/quiet-exclusion.json').read_text());c=json.loads((H.parent/'bypass_local/capture-01/capture.json').read_text());capturebase=H.parent/'held_loops/native-02/power_protection.kicad_pcb'
 assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(capturebase) for k,v in c['source_sha256'].items())
 for key,path in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('plan_sha256',H/'plane-plan-03.json'),('script_sha256',H/'native_plane.py'),('adapter_sha256',H/'process_adapter.py'),('full_refill_sha256',OUT/'full-refill.kicad_pcb'),('geometry_sha256',OUT/'new-zone-geometry.json')]:assert r[key]==sha(path)
 assert p['builder_sha256']==sha(H/'build_plane.py') and p['authored_board_sha256']==sha(H/'authored-03/power_protection.kicad_pcb');assert r['all_original_groups_unchanged'] and r['all_original_objects_unchanged'] and r['all_original_fills_unchanged'] and r['anonymous_identity_bijection_preserved']==55 and r['original_group_count']==2714 and r['opens_before']==r['opens_after']==1964
 a,b=[read_sexpr((x/'power_protection.kicad_pcb').read_text()) for x in [BASE,OUT]];oldzones={first(z,'uuid')[1]:z for z in children(a,'zone')};newzones={first(z,'uuid')[1]:z for z in children(b,'zone')};assert len(oldzones)==47 and len(newzones)==48 and set(newzones)-set(oldzones)=={p['new_zone_uuid']};assert all(newzones[u]==z for u,z in oldzones.items());assert children(read_sexpr(capturebase.read_text()),'zone')==children(a,'zone');assert zone_coordinates(newzones[p['new_zone_uuid']])==[p['outline_mm']] and int(first(newzones[p['new_zone_uuid']],'priority')[1])==2
 assert gdata['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');g=unary_union([Polygon([[x/1e6,y/1e6] for x,y in v['outer']],[[[x/1e6,y/1e6] for x,y in hole] for hole in v['holes']]) for v in gdata['polygons_nm']]);main=shape(next(z['polygons'] for z in c['zones'] if z['uuid']==p['main_source_zone_uuid']));overlap=g.intersection(main).area;assert overlap>180
 quietids=set(q['retained_object_uuids']);quietzones={x['zone_uuid'] for x in q['plane_exclusions']}
 for o in c['objects']:
  if o['uuid'] in quietids and 'In6.Cu' in o['layers']:assert g.distance(shape(o['layers']['In6.Cu']))>=.199
 for z in c['zones']:
  if z['uuid'] in quietzones and z['layer']=='In6.Cu':assert g.distance(shape(z['authored_outline']))>=.199
 for name in ['parent-process','refill-process','final-drc-process']:
  rr=json.loads((OUT/name/'process.json').read_text());assert rr['status']=='passed' and rr['returncode']==0 and all(rr['inputs_unchanged'].values())
  for log in ['stdout.log','stderr.log']:assert rr[log+'_sha256']==sha(OUT/name/log)
 old,new=[json.loads((x/'drc.json').read_text()) for x in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(old['violations'],key=key)==sorted(new['violations'],key=key) and len(new['violations'])==4
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 binding=json.loads((H/'library-binding.json').read_text());count=library_link(OUT/'libraries',binding,H.parents[3],BASE/'libraries')
 result={'main_fill_overlap_mm2':overlap,'new_fill_area_mm2':g.area,'unchanged_original_zones':47,'unchanged_native_groups':2714,'linked_library_files':count,'qualified':False};print(result);return result
if __name__=='__main__':(H/'plane-verification.json').write_text(json.dumps(verify(),indent=2)+'\n')
