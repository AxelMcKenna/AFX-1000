"""Fail closed on native circuit drift, extra ERC findings, or stale provenance."""
import csv,hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def netlist(path):
 t=ET.parse(path)
 return {x.attrib['ref']:x for x in t.findall('./components/comp')},{(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in t.findall('./nets/net') for n in net.findall('node')}
def issues(path):
 j=json.loads(path.read_text())
 return sorted((v['severity'],v['type'],v['description'],tuple(x['description'] for x in v['items'])) for s in j['sheets'] for v in s['violations'])
def check_hashes(root,expected):
 actual={str(p.relative_to(root)):H(p) for p in root.rglob('*') if p.is_file() and p.suffix in ['.kicad_sch','.kicad_sym','.kicad_pro']}
 assert actual==expected,('native input set/content changed',sorted(set(actual)^set(expected)),[n for n in actual.keys()&expected.keys() if actual[n]!=expected[n]])
def check_pins(old_refs,op,np,expected,new_parts):
 # Union is essential: new connectivity on a formerly absent pin must fail.
 keys={k for k in op.keys()|np.keys() if k[0] in old_refs}
 moves={k:np.get(k) for k in keys if op.get(k)!=np.get(k)}
 assert moves==expected,(moves,expected)
 for part in new_parts:
  actual={pin:net for (ref,pin),net in np.items() if ref==part['ref']}
  assert set(actual)==set(part['pins']),('added part pin set',part['ref'],actual,part['pins'])
  for pin,net in part['pins'].items():
   got=actual[pin]
   if net is None:assert got.startswith('unconnected-'),(part['ref'],pin,got)
   else:assert got==(net if net.startswith('PWR_') else ('/P_power_supply/' if part['ref'].startswith('P_') else '/E_rail_disconnect/')+net),(part['ref'],pin,net,got)
 return moves
def verify(baseline=None):
 a=HERE/'authored';n=HERE/'native-03';m=json.loads((a/'candidate.json').read_text());assert m['builder_sha256']==H(HERE/'build.py')
 baseline=Path(baseline) if baseline else HERE.parents[3]/'hardware/fabrication/staging'/m['source_directory']
 assert baseline.is_dir(),('frozen baseline missing; pass its directory explicitly',str(baseline))
 check_hashes(a,json.loads((n/'candidate-input-hashes.json').read_text()))
 check_hashes(baseline,json.loads((n/'baseline-input-hashes.json').read_text()))
 for name,h in m['source_sha256'].items():assert H(baseline/name)==h,name
 old,op=netlist(n/'baseline-netlist.xml');new,np=netlist(n/'candidate-netlist.xml')
 assert set(new)-set(old)=={p['ref'] for p in m['new_parts']};assert not set(old)-set(new)
 changed={r:(old[r].findtext('value'),new[r].findtext('value')) for r in old if old[r].findtext('value')!=new[r].findtext('value')}
 assert changed=={r['ref']:(r['old_value'],r['new_value']) for r in m['changed_values']}
 expected={(r,p):('/P_power_supply/' if r.startswith('P_') else '/E_rail_disconnect/')+net for r,p,net in m['retargeted_existing_pins']}
 moves=check_pins(set(old),op,np,expected,m['new_parts'])
 assert issues(n/'baseline-erc.json')==issues(n/'candidate-erc.json')
 # Existing source pin partition is preserved everywhere outside four declared moves.
 # Pin-name and numeric mapping of added ICs remains primary-datasheet review.
 with (HERE/'candidate-bom.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['reference','value','MPN','footprint','datasheet'])
  for r,c in sorted(new.items()):
   fields={x.attrib['name']:x.text or '' for x in c.findall('./fields/field')}
   w.writerow([r,c.findtext('value'),fields.get('MPN',''),c.findtext('footprint'),c.findtext('datasheet')])
 report=dict(native_ERC_added_violations=0,inherited_ERC=issues(n/'candidate-erc.json'),existing_components=len(old),new_components=len(new)-len(old),changed_values=len(changed),existing_pins_moved=len(moves),all_other_existing_pin_nets_unchanged=True,existing_pin_union_checked=True,added_pin_sets_exact=True,baseline_original_input_hashes_verified=True,new_part_pin_mapping_verified=True,board_emitted=False,fabrication_released=False,
 source_sha256={str(p.relative_to(HERE)):H(p) for p in [HERE/'build.py',HERE/'native.py',HERE/'verify.py',*sorted(a.rglob('*.kicad_sch')),*sorted(a.rglob('*.kicad_sym')),a/'candidate.json',*sorted(n.glob('*.json')),*sorted(n.glob('*.xml'))]},
 missing_new_footprints=[p['ref'] for p in m['new_parts'] if not p['footprint']])
 (HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ['source_sha256','inherited_ERC']})
 return report
if __name__=='__main__':verify(sys.argv[1] if len(sys.argv)>1 else None)
