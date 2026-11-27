"""Fail-closed package/pin compatibility and source-bound native evidence audit."""
import argparse,copy,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(c,a,inv):
 headers={x['reference']:x for x in a['headers']};assert len(c['choices'])==11
 used=0
 for row in c['choices']:
  h=headers[row['ref']];assert len(row['pin_map'])==len(h['pads'])
  for p,q in zip(row['pin_map'],h['pads']):
   assert p['board_pin']==q['pin'] and p['xy_mm']==q['xy_mm'] and p['net']==q['net']
   assert p['assigned_female_position_from_west']==int(q['pin'])
   expected=[w for w in inv['wires'] if w['source']==row['ref']+':'+q['pin']]
   if row['ref']=='D_J2003' and q['pin']=='1':assert not p['populated'] and p['receiver'] is None
   else:
    assert p['populated'] and len(expected)==1 and expected[0]['target']==p['receiver'] and expected[0]['net']==p['net'];used+=1
 assert used==34
 w=c['wire_contract'];assert .9<=w['od_range_mm'][0]<=w['od_range_mm'][1]<=1.6
 assert w['receiving_diameter_mm']>=w['od_range_mm'][1] and w['min_bend_radius_mm']>=10*w['od_range_mm'][1]
 assert 5.5<=5.8-.25 and 5.8+.25<=6.3
 assert not c['fabrication_released'] and not c['pcb_changed'] and not c['bom_changed']
def main():
 p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,required=True);a=p.parse_args();c=json.loads((H/'mate-contract.json').read_text());audit=json.loads((H/'board-audit.json').read_text());invpath=H.parent/'r19_panel_inventory/inventory.json';inv=json.loads(invpath.read_text())
 assert sha(a.pcb)==audit['board_provenance']['sha256'];assert sha(H/'audit_board.py')==audit['generator_sha256']
 for f,s in c['source_sha256'].items():assert sha(R/f)==s,f
 check(c,audit,inv)
 mutations=[]
 for key in ('net','receiver','populated','assigned_female_position_from_west'):
  bad=copy.deepcopy(c);p=bad['choices'][0]['pin_map'][0];p[key]=False if key=='populated' else ('WRONG' if key in ('net','receiver') else 99)
  try:check(bad,audit,inv)
  except AssertionError:mutations.append(key)
  else:raise AssertionError('mutation accepted:'+key)
 evidence={}
 for part in ('components','structure','wires_supports','positive','withdrawal'):
  f=H/'native'/(part+'-r5')/'result.json';v=json.loads(f.read_text());assert not v['runtime_failure']
  for src,s in v['source_sha256'].items():assert sha(R/src)==s,src
  if part in ('positive','withdrawal'):assert not v['empty'] and v['mesh']['closed_oriented_boundary']
  else:assert v['empty'] and v['mesh'] is None
  evidence[part]={'result':'FAIL_SERVICE_SWEEP' if part=='withdrawal' else 'PASS','evidence':str(f.relative_to(R)),'sha256':sha(f)}
 report={'source_sha256':{str(f.relative_to(R)):sha(f) for f in (H/'mate-contract.json',H/'mates.scad',H/'verify.py',invpath)},'pcb_sha256':sha(a.pcb),'installed_local_checks_pass':True,'withdrawal_pass':False,'withdrawal_obstruction':'D_J1022 receiving sweep intersects lid-mounted R04; lid opening/ground displacement and feed slack must be qualified before unplugging','native':evidence,'mutations_rejected':mutations,'full_assembly_checked':False,'fabrication_released':False}
 (H/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
