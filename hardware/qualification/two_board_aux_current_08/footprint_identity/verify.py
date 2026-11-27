"""Require only the declared footprint fields to change; preserve every pin and component."""
import copy,csv,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children
from .build import props
H=Path(__file__).resolve().parents[1];D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def schematic_delta(before,after,changes):
 expected=copy.deepcopy(before);seen=set()
 for s in children(expected,'symbol'):
  ps=props(s);ref=ps.get('Reference',[None,None,None])[2]
  if ref in changes:
   assert ps['Footprint'][2]==changes[ref]['before'];ps['Footprint'][2]=changes[ref]['after'];seen.add(ref)
 assert seen==set(changes) and expected==after

def netlist_delta(before,after,changes):
 def comps(t):return {c.attrib['ref']:c for c in t.findall('./components/comp')}
 def pins(t):return {(p.attrib['ref'],p.attrib['pin']):n.attrib['name'] for n in t.findall('./nets/net') for p in n.findall('node')}
 assert pins(before)==pins(after);a=comps(before);b=comps(after);assert set(a)==set(b)
 for ref,c in a.items():
  c=copy.deepcopy(c)
  if ref in changes:
   f=c.find('footprint');assert (f.text if f is not None else '')==changes[ref]['before']
   if f is None:f=ET.SubElement(c,'footprint')
   f.text=changes[ref]['after']
   fields=c.find('fields');ff=fields.find("field[@name='Footprint']");assert ff is not None and (ff.text or '')==changes[ref]['before'];ff.text=changes[ref]['after']
  def canonical(n):return (n.tag,tuple(sorted(n.attrib.items())),(n.text or '').strip(),tuple(sorted(canonical(x) for x in n)))
  assert canonical(c)==canonical(b[ref]),ref

def verify():
 r=json.loads((D/'changes.json').read_text());src=H/'associations/authored';dst=D/'authored';assert sha(src/'power_protection.kicad_pcb')==sha(dst/'power_protection.kicad_pcb')==r['source_board_sha256'];assert sha(D/'build.py')==r['builder_sha256'];assert sha(H/'associations/changes.json')==r['source_association_changes_sha256']
 changes={c['reference']:c for c in r['changes']};assert len(changes)==18
 for name,h in r['source_schematic_sha256'].items():
  assert sha(src/name)==h and sha(dst/name)==r['candidate_schematic_sha256'][name];schematic_delta(read_sexpr((src/name).read_text()),read_sexpr((dst/name).read_text()),{ref:c for ref,c in changes.items() if c['sheet']==name})
 for name in ['symbols','libraries']:
  p=dst/name;assert p.is_symlink() and p.resolve()==(src/name).resolve() and p.resolve().is_relative_to(H.resolve())
  expected=json.loads((H/'associations/changes.json').read_text())['library_sha256'][name];assert {str(f.relative_to(p.resolve())):sha(f) for f in sorted(p.resolve().rglob('*')) if f.is_file()}==expected
 assert sha(H/'precision/candidate-bom.csv')==r['source_bom_sha256'] and sha(D/'candidate-bom.csv')==r['candidate_bom_sha256']
 with (H/'precision/candidate-bom.csv').open() as f:old=list(csv.DictReader(f))
 with (D/'candidate-bom.csv').open() as f:new=list(csv.DictReader(f))
 for row in old:
  if row['Reference'] in changes:row['Schematic footprint']=changes[row['Reference']]['after']
 assert old==new
 out=D/'native-01';netlist_delta(ET.parse(H/'precision/native-01/candidate-netlist.xml'),ET.parse(out/'candidate-netlist.xml'),changes)
 nr=json.loads((out/'review.json').read_text());assert nr['script_sha256']==sha(D/'native.py') and nr['candidate_board_sha256']==r['source_board_sha256'] and nr['native_electrical_associations_and_footprint_ids']==1104 and nr['schematic_parity_issues']==0 and nr['board_unchanged']
 for n,h in nr['result_sha256'].items():assert sha(out/n)==h
 for name in ['netlist','erc','parity']:
  p=json.loads((out/(name+'-process/process.json')).read_text());assert p['status']=='passed' and all(p['inputs_unchanged'].values())
  for n in ['stdout.log','stderr.log']:assert sha(out/(name+'-process')/n)==p[n+'_sha256']
 parity=json.loads((out/'parity.json').read_text());assert not parity['schematic_parity'] and len(parity['violations'])==4 and all(v['type']=='clearance' for v in parity['violations'])
 erc=json.loads((out/'erc.json').read_text());baseline=json.loads((H/'precision/native-01/candidate-erc.json').read_text());assert erc['sheets']==baseline['sheets']
 result={'schematic_uuid_and_footprint_identity_gate':'passed','native_parity_issues':0,'electrical_parts':1104,'board_byte_identical':True,'all_old_pins_nets_values_unchanged':True,'original_four_DSE_errors_unwaived':True,'actual_update_from_schematic_executed':False,'qualified':False};(D/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':verify()
