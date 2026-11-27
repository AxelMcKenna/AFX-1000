"""Independent C13 semantic, physical, source and receiving gates."""
import copy,json,hashlib,gzip
from pathlib import Path
from shapely.geometry import LineString
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..routed.plan import shape
from ..ldo_local.immutable_inputs import check_tree,check_recorded
H=Path(__file__).resolve().parent;Q=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def semantics(e,r):
 a,b=e['source'],e['candidate'];old,new=a['pad_identities'],b['pad_identities'];assert set(old)==set(new)
 by={(p['ref'],p['pin']):p for p in new.values()}
 assert by['E_U4','1']['net']==by['E_C13','1']['net']=='PWR_AUX_HELD3V3'
 assert by['E_U4','4']['net']==by['E_C13','2']['net']=='PWR_AGND'
 assert by['E_U4','2']['net']=='/E_rail_disconnect/N12_TT'
 moved=set(r['moved_pad_UUIDs']);assert {old[u]['ref'] for u in moved}=={'E_C13'} and len(moved)==2
 for u,p in old.items():
  expected=copy.deepcopy(p)
  if u in moved:
   for field in ['position_nm','footprint_position_nm']:expected[field]=[v-1500000 for v in p[field]]
   for ps in expected['copper_polygons_nm'].values():
    for part in ps:
     for ring in [part['outer'],*part['holes']]:
      for xy in ring:xy[0]-=1500000;xy[1]-=1500000
  assert new[u]==expected,u
 removed=set(r['removed_track_UUIDs']);added=set(r['added_track_UUIDs']);assert len(removed)==len(added)==2
 assert set(b['objects'])==(set(a['objects'])-removed)|added
 for u,v in a['objects'].items():
  if u not in removed|moved:assert b['objects'][u]==v,u
 norm=lambda gs:sorted((g['net'],tuple(sorted(set(g['members'])-removed-added))) for g in gs)
 assert norm(a['groups'])==norm(b['groups']) and a['opens']==b['opens']==1943
 assert len({json.dumps(p,sort_keys=True) for p in new.values()})==len(new)
def run():
 m=json.loads((H/'review-manifest-02.json').read_text());src=H/m['bundle_name'];check_tree(src,m);e=json.loads(gzip.decompress((H/'review-02/native-evidence.json.gz').read_bytes()));r=json.loads((H/'native-02/review.json').read_text());semantics(e,r)
 assert e['source']['board_sha256']==m['source_board_sha256']==sha(Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb')
 assert m['authored_native_sha256']==r['candidate_sha256']==sha(H/'native-02/power_protection.kicad_pcb')
 assert e['candidate']['board_sha256']==sha(src/'power_protection.kicad_pcb')
 assert e['source']['native_fill_state_sha256']==e['candidate']['native_fill_state_sha256']
 p=json.loads((H/'review-02/parity-process/process.json').read_text());expected={'/repo/hardware/qualification/two_board_aux_current_08/c13_receiving/'+m['bundle_name']+'/'+n:v for n,v in m['files'].items() if n=='power_protection.kicad_pcb' or n.endswith('.kicad_sch') and '/' not in n};check_recorded(p,expected)
 d=json.loads((H/'review-02/parity.json').read_text());prior=json.loads((Q/'reference_fix/native-02/parity.json').read_text());assert not d['schematic_parity'];sig=lambda rows:sorted((x['type'],x['description'],tuple(sorted(i['uuid'] for i in x['items']))) for x in rows);assert sig(d['violations'])==sig(prior['violations']) and len(d['violations'])==4
 trees=[read_sexpr(p.read_text()) for p in [Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb',src/'power_protection.kicad_pcb']];zs=lambda t:{str(first(z,'uuid')[1]):([x for x in z if not isinstance(x,list) or x[0]!='filled_polygon'],sorted(json.dumps(x) for x in children(z,'filled_polygon'))) for z in children(t,'zone')};assert zs(trees[0])==zs(trees[1])
 c=json.loads((Q/'ldo_feed/capture-02/capture.json').read_text());reference=shape(next(z['polygons'] for z in c['zones'] if z['uuid']=='13cfea4d-d36e-5757-b531-ed680e4c4562'));plan=json.loads((H/'plan.json').read_text())['rows'][0]['chosen']
 for kind in ['supply','ground']:assert LineString(plan[kind+'_path_mm']).buffer(.15).difference(reference).area<1e-9
 receiving=json.loads((H/'receiving-review.json').read_text());assert receiving['status']=='PASS' and not receiving['peer_collisions'] and receiving['candidate_board_sha256']==e['candidate']['board_sha256']
 return {'status':'PASS','opens':1943,'original_pad_groups_preserved':True,'reference_coverage':'PASS','receiving_peers':1940,'C16_gap_mm':receiving['C16_receiving_gap_mm'],'remaining_DSE_violations':4,'qualified':False}
if __name__=='__main__':print(json.dumps(run(),indent=2))
