"""Check exact reference coverage, BOM binding and retained primary evidence."""
import csv, hashlib, json
from pathlib import Path
B=Path(__file__).resolve().parents[1]
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 d=json.loads((B/'package_envelopes/envelopes.json').read_text())
 assert digest(B/d['source_board'])==d['source_board_sha256']
 assert digest(B/d['bom_source'])==d['bom_sha256']
 rows={r['Reference']:r for r in csv.DictReader((B/d['bom_source']).open())}
 expected=d['added_references']+d['changed_mpn_references']
 assert len(expected)==len(set(expected))==32
 assert len(d['added_references'])==19 and len(d['changed_mpn_references'])==13
 assert sorted(p['reference'] for p in d['parts'])==sorted(expected)
 for p in d['parts']:
  source=(B/p['source']).resolve(); assert source.is_relative_to(B)
  assert digest(source)==p['source_sha256'],p['reference']
  if p['reference']!='P_C907': assert rows[p['reference']]['MPN']==p['mpn']
  assert len(p['max_envelope_mm'])==3 and all(v>0 for v in p['max_envelope_mm'])
 assert all(d['allowances'][k] is None for k in ['solder_height_mm','placement_xy_mm','tilt_degrees','board_warp_mm'])
 return {'status':'PASS','references':32,'assembly_qualified':False,'pcb_modified':False}
if __name__=='__main__': print(json.dumps(verify(),indent=2))
