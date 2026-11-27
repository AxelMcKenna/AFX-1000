"""Independent exact groups, moved-cap identity and source-bound native gates."""
import copy,json,gzip
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..ldo_local.immutable_inputs import sha,check_tree,check_recorded
H=Path(__file__).resolve().parent;Q=H.parent

def semantics(e,p):
 a,b=e['source'],e['candidate'];old,new=a['pad_identities'],b['pad_identities'];assert set(old)==set(new)
 by={(v['ref'],v['pin']):u for u,v in old.items()};moved={by['P_C907','1'],by['P_C907','2']};assert old[by['P_U102','8']]['net']==old[by['P_C907','1']]['net']==old[by['P_C102','1']]['net']=='/P_power_supply/AUX_PREREG5'
 assert old[by['P_U102','9']]['net']==old[by['P_C907','2']]['net']=='PWR_AGND'
 for u,v in old.items():
  expected=copy.deepcopy(v)
  if u in moved:
   for key in ['position_nm','footprint_position_nm']:expected[key][0]-=1000000
   for parts in expected['copper_polygons_nm'].values():
    for part in parts:
     for ring in [part['outer'],*part['holes']]:
      for xy in ring:xy[0]-=1000000
  assert new[u]==expected,u
 assert len({json.dumps(v,sort_keys=True) for v in new.values()})==len(new)
 removed=set(p['removed_owned_track_UUIDs']);added=set(p['added_UUIDs']);assert len(removed)==4 and len(added)==9;assert set(b['objects'])==(set(a['objects'])-removed)|added
 for u,v in a['objects'].items():
  if u not in removed|moved:assert b['objects'][u]==v,u
 normal=lambda rows:sorted((r['net'],tuple(sorted(set(r['members'])-removed-added))) for r in rows)
 ga=copy.deepcopy(a['groups']);target=[r for r in ga if by['P_U102','8'] in r['members'] or by['P_C102','1'] in r['members']];assert len(target)==2 and len({r['net'] for r in target})==1
 expected=[r for r in ga if r not in target]+[{'net':target[0]['net'],'members':sorted(set(target[0]['members'])|set(target[1]['members']))}];assert normal(expected)==normal(b['groups']);assert a['opens']==1943 and b['opens']==1942
 main=next(r for r in b['groups'] if by['P_U102','9'] in r['members']);supply=next(r for r in b['groups'] if by['P_U102','8'] in r['members'])
 for v in p['vias']:
  assert b['objects'][v['uuid']][0:2]==['PCB_VIA',v['net']]
  assert v['uuid'] in (main if v['net']=='PWR_AGND' else supply)['members']
 return {'exact_declared_source_group_merge':True,'all_other_original_groups_preserved':True,'anonymous_pad_physical_identities_preserved':True}

def contact_evidence(contacts):
 assert contacts['candidate_sha256']==sha(H/'local-IN-slot-01.kicad_pcb')
 assert contacts['source_capture_sha256']==sha(H/'capture-02/capture.json')
 assert contacts['status']=='PASS' and not contacts['lost_original_track_reference']

def run():
 m=json.loads((H/'review-manifest-02.json').read_text());src=H/m['bundle_name'];check_tree(src,m);p=json.loads((H/'manifest-IN-slot-01.json').read_text());e=json.loads(gzip.decompress((H/'review-02/native-evidence.json.gz').read_bytes()));result=semantics(e,p)
 assert e['source']['board_sha256']==sha(Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb')==m['source_board_sha256'];assert e['candidate']['board_sha256']==sha(src/'power_protection.kicad_pcb')
 expected={'/repo/hardware/qualification/two_board_aux_current_08/ldo_feed/'+m['bundle_name']+'/'+n:v for n,v in m['files'].items() if n=='power_protection.kicad_pcb' or n.endswith('.kicad_sch') and '/' not in n};check_recorded(json.loads((H/'review-02/parity-process/process.json').read_text()),expected)
 d=json.loads((H/'review-02/parity.json').read_text());prior=json.loads((Q/'reference_fix/native-02/parity.json').read_text());sig=lambda rows:sorted((x['type'],x['description'],tuple(sorted(i['uuid'] for i in x['items']))) for x in rows);assert not d['schematic_parity'] and sig(d['violations'])==sig(prior['violations']) and len(d['violations'])==4
 a,b=[read_sexpr(x.read_text()) for x in [Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb',src/'power_protection.kicad_pcb']];zs=lambda t:{str(first(z,'uuid')[1]):z for z in children(t,'zone')};af={next(x[2] for x in children(f,'property') if x[1]=='Reference'):f for f in children(a,'footprint')};bf={next(x[2] for x in children(f,'property') if x[1]=='Reference'):f for f in children(b,'footprint')};assert set(af)==set(bf)
 for ref in af:
  actual=copy.deepcopy(bf[ref])
  if ref=='P_C907':
   first(actual,'at')[1:]=first(af[ref],'at')[1:]
   actualref=next(x for x in children(actual,'property') if x[1]=='Reference');oldref=next(x for x in children(af[ref],'property') if x[1]=='Reference');first(actualref,'at')[1:]=first(oldref,'at')[1:]
  assert actual==af[ref],ref
 for v in p['vias']:
  actual=next(via for via in children(b,'via') if str(first(via,'uuid')[1])==v['uuid']);assert list(map(float,first(actual,'at')[1:]))==v['position_mm'] and float(first(actual,'size')[1])==.6 and float(first(actual,'drill')[1])==.3
 a,b=zs(a),zs(b);assert b==zs(read_sexpr((H/'local-IN-slot-01.kicad_pcb').read_text()));local=json.loads((H/'local-IN-slot-01.json').read_text());allowed={r['uuid'] for r in local['zones']};assert len(allowed)==5
 for u in a:
  if u not in allowed:assert a[u]==b[u],u
 transition=json.loads((H/'transition-review.json').read_text());assert transition['status']=='PASS' and transition['candidate_sha256']==e['candidate']['board_sha256'];contacts=json.loads((H/'local-check.json').read_text());contact_evidence(contacts)
 result.update(status='PASS',opens=1942,foreign_fills_unchanged=True,local_native_antipad_zones=5,original_ground_contacts=107,original_referenced_tracks=2206,remaining_DSE_violations=4,qualified=False);return result
if __name__=='__main__':print(json.dumps(run(),indent=2))
