"""Strict reconciliation for pads that were anonymous in the original PCB."""
import json
from .verify import HERE

def physical_key(identity):return json.dumps(identity,sort_keys=True,separators=(',',':'))
def reconcile(snapshot,capture):
 assert snapshot['explicit_pad_identities_unchanged']
 candidate={}
 for row in snapshot['candidate_relevant_pads']:
  key=physical_key(row['identity']);assert key not in candidate,'Ambiguous duplicate pad identity';candidate[key]=row['uuid']
 original={}
 for row in snapshot['baseline_anonymous']:
  key=physical_key(row['identity']);assert key not in original,'Ambiguous source identity';original[key]=row
 mappings=[]
 for key,row in original.items():
  assert key in candidate,'Anonymous pad physical identity changed'
  ident=row['identity'];matches=[]
  for p in capture['objects']:
   if p.get('ref')!=ident['ref'] or p.get('pin')!=ident['pin'] or p['net']!=ident['net']:continue
   if [round(v*1e6) for v in p['position_mm']]!=ident['position_nm']:continue
   if p['orientation_degrees']%360!=ident['orientation_degrees']:continue
   if [round(v*1e6) for v in p['drill_mm']]!=ident['drill_nm']:continue
   geom={l:[{'outer':[[round(v*1e6) for v in xy] for xy in q['outer']],'holes':[[[round(v*1e6) for v in xy] for xy in hole] for hole in q['holes']]} for q in polys] for l,polys in p['layers'].items()}
   if geom==ident['copper_polygons_nm']:matches.append(p['uuid'])
  assert len(matches)==1,'Capture identity missing or ambiguous'
  mappings.append({'capture_uuid':matches[0],'native_source_load_uuid':row['uuid'],'candidate_uuid':candidate[key],'full_physical_identity':ident})
 assert len(mappings)==snapshot['source_anonymous_pad_count']==55
 assert sum(bool(r['full_physical_identity']['net'] and r['full_physical_identity']['pin']) for r in mappings)==49
 assert len(candidate)==len(original),'Unexpected pad in anonymous-source footprints'
 return mappings
if __name__=='__main__':
 import argparse
 from pathlib import Path
 from .verify import sha
 a=argparse.ArgumentParser();a.add_argument('root',type=Path);root=a.parse_args().root;cap=root/'hardware/fabrication/staging/two-board-power-routing-inputs-aux-local-distribution-03/capture.json';s=json.loads((HERE/'native-04/pad-identities.json').read_text());m=reconcile(s,json.loads(cap.read_text()));(HERE/'anonymous-pad-mapping.json').write_text(json.dumps({'source_board_sha256':s['source_sha256'],'candidate_board_sha256':s['candidate_sha256'],'capture_sha256':sha(cap),'native_identity_sha256':sha(HERE/'native-04/pad-identities.json'),'mappings':m},indent=2)+'\n');print({'reconciled':len(m),'explicit_pads_checked':s['explicit_source_pads_checked']})
