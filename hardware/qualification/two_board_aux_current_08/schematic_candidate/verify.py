"""Fail closed on native circuit drift, extra ERC findings, or stale provenance."""
import csv,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def netlist(path):
 t=ET.parse(path)
 return {x.attrib['ref']:x for x in t.findall('./components/comp')},{(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in t.findall('./nets/net') for n in net.findall('node')}
def issues(path):
 j=json.loads(path.read_text())
 return sorted((v['severity'],v['type'],v['description'],tuple(x['description'] for x in v['items'])) for s in j['sheets'] for v in s['violations'])
def verify():
 a=HERE/'authored';n=HERE/'native-03';m=json.loads((a/'candidate.json').read_text());assert m['builder_sha256']==H(HERE/'build.py')
 native_inputs=json.loads((n/'candidate-input-hashes.json').read_text())
 for name,h in native_inputs.items():assert H(a/name)==h,name
 old,op=netlist(n/'baseline-netlist.xml');new,np=netlist(n/'candidate-netlist.xml')
 assert set(new)-set(old)=={p['ref'] for p in m['new_parts']};assert not set(old)-set(new)
 changed={r:(old[r].findtext('value'),new[r].findtext('value')) for r in old if old[r].findtext('value')!=new[r].findtext('value')}
 assert changed=={r['ref']:(r['old_value'],r['new_value']) for r in m['changed_values']}
 moves={tuple(k):np[k] for k in op if op[k]!=np.get(k)}
 expected={(r,p):('/P_power_supply/' if r.startswith('P_') else '/E_rail_disconnect/')+net for r,p,net in m['retargeted_existing_pins']}
 assert moves==expected,(moves,expected)
 for p in m['new_parts']:
  for pin,net in p['pins'].items():
   actual=np.get((p['ref'],pin))
   if net is None:assert actual is None or actual.startswith('unconnected-'),(p['ref'],pin,actual)
   else:assert actual==(net if net.startswith('PWR_') else ('/P_power_supply/' if p['ref'].startswith('P_') else '/E_rail_disconnect/')+net),(p['ref'],pin,net,actual)
 assert issues(n/'baseline-erc.json')==issues(n/'candidate-erc.json')
 # Existing source pin partition is preserved everywhere outside four declared moves.
 # Pin-name and numeric mapping of added ICs remains primary-datasheet review.
 with (HERE/'candidate-bom.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['reference','value','MPN','footprint','datasheet'])
  for r,c in sorted(new.items()):
   fields={x.attrib['name']:x.text or '' for x in c.findall('./fields/field')}
   w.writerow([r,c.findtext('value'),fields.get('MPN',''),c.findtext('footprint'),c.findtext('datasheet')])
 report=dict(native_ERC_added_violations=0,inherited_ERC=issues(n/'candidate-erc.json'),existing_components=len(old),new_components=len(new)-len(old),changed_values=len(changed),existing_pins_moved=len(moves),all_other_existing_pin_nets_unchanged=True,new_part_pin_mapping_verified=True,board_emitted=False,fabrication_released=False,
 source_sha256={str(p.relative_to(HERE)):H(p) for p in [HERE/'build.py',HERE/'native.py',HERE/'verify.py',*sorted(a.rglob('*.kicad_sch')),*sorted(a.rglob('*.kicad_sym')),a/'candidate.json',*sorted(n.glob('*.json')),*sorted(n.glob('*.xml'))]},
 missing_new_footprints=[p['ref'] for p in m['new_parts'] if not p['footprint']])
 (HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ['source_sha256','inherited_ERC']})
 return report
if __name__=='__main__':verify()
