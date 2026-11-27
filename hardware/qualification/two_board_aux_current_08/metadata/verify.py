"""Exhaustive value/net parity and exact metadata-only physical preservation."""
import copy,json,xml.etree.ElementTree as ET
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from .build import H,ROOT,props,sha,MPN,URL,VALUES

def exact_delta(old,new,changes):
 expected=copy.deepcopy(old);by={props(f)['Reference'][2]:f for f in children(expected,'footprint')}
 assert len({(x['ref'],x['field']) for x in changes})==len(changes)
 for x in changes:
  p=props(by[x['ref']]);assert x['field'] in ['Value','MPN','Datasheet'];assert (p[x['field']][2] if x['field'] in p else None)==x['before']
  if x['field'] not in p:
   q=copy.deepcopy(p['Datasheet']);q[1]=x['field'];q[2]=x['after'];by[x['ref']].append(q)
  else:p[x['field']][2]=x['after']
 assert expected==new,'Unexpected physical or metadata change'
def nets(tree):
 return { (x.attrib['ref'],x.attrib['pin']):n.attrib['name'] for n in tree.findall('./nets/net') for x in n.findall('node') }
def verify():
 r=json.loads((H/'changes.json').read_text());
 for name in ['libraries','symbols']:
  link=H/'authored'/name;target=(ROOT/'held_cutover/authored'/name).resolve();assert link.is_symlink() and link.resolve(strict=True)==target and target.is_relative_to(ROOT.resolve());assert {str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()}==r['library_sha256'][name]
 from ..held_cell.verify_plane import library_link
 library_link(H/'native-01/libraries',json.loads((ROOT/'held_cell/library-binding.json').read_text()),H.parents[3],ROOT/'shared_cutover/native-04/libraries')
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (ROOT/'held_cell/native-local-02'/n).read_bytes()==(H/'native-01'/n).read_bytes()
 old=read_sexpr((ROOT/'held_cell/native-local-02/power_protection.kicad_pcb').read_text());new=read_sexpr((H/'native-01/power_protection.kicad_pcb').read_text());exact_delta(old,new,r['changes'])
 for k,p in [('source_board_sha256',ROOT/'held_cell/native-local-02/power_protection.kicad_pcb'),('candidate_board_sha256',H/'native-01/power_protection.kicad_pcb'),('source_netlist_sha256',ROOT/'held_cutover/native-03/candidate-netlist.xml'),('builder_sha256',H/'build.py'),('native_script_sha256',H/'native.py'),('primary_pdf_sha256',H/'primary/c0805c681j5gactu.pdf')]:assert r[k]==sha(p)
 for n,v in r['source_schematic_sha256'].items():assert sha(ROOT/'held_cutover/authored'/n)==v
 before,after=[ET.parse(p) for p in [ROOT/'held_cutover/native-03/candidate-netlist.xml',H/'native-01/candidate-netlist.xml']];assert nets(before)==nets(after)
 a,b=[{x.attrib['ref']:x for x in t.findall('./components/comp')} for t in [before,after]];assert set(a)==set(b) and len(a)==1104
 for ref in a:
  if ref=='P_C109':
   a[ref].find('footprint').text='TB05_P_Capacitor_SMD:C_0805_2012Metric';a[ref].find('datasheet').text=URL
   for f in a[ref].findall('./fields/field'):
    if f.attrib['name'] in ['MPN','Datasheet','Footprint']:f.text={'MPN':MPN,'Datasheet':URL,'Footprint':'TB05_P_Capacitor_SMD:C_0805_2012Metric'}[f.attrib['name']]
   for f in a[ref].findall('property'):
    if f.attrib['name']=='MPN':f.attrib['value']=MPN
  assert ET.tostring(a[ref])==ET.tostring(b[ref]),ref
 pcb={props(f)['Reference'][2]:props(f) for f in children(new,'footprint')};assert set(b)<=set(pcb)
 for ref,c in b.items():
  assert pcb[ref]['Value'][2]==c.findtext('value')
  fs={f.attrib['name']:f.text for f in c.findall('./fields/field')}
  if fs.get('MPN'):assert pcb[ref]['MPN'][2]==fs['MPN']
 olderc=json.loads((ROOT/'held_cutover/native-03/candidate-erc.json').read_text());erc=json.loads((H/'native-01/candidate-erc.json').read_text());assert olderc['sheets']==erc['sheets']
 drc=json.loads((H/'native-01/drc.json').read_text());oldrc=json.loads((ROOT/'held_cell/native-local-02/drc.json').read_text());assert sorted(drc['violations'],key=lambda x:json.dumps(x,sort_keys=True))==sorted(oldrc['violations'],key=lambda x:json.dumps(x,sort_keys=True)) and len(drc['violations'])==4
 assert len(drc['unconnected_items'])==len(oldrc['unconnected_items'])==499 # CLI report is capped; physical identity inherits native opens count.
 for name in ['netlist','erc','drc']:
  p=H/'native-01'/(name+'-process');record=json.loads((p/'process.json').read_text());assert record['status']=='passed' and all(record['inputs_unchanged'].values())
  for n in ['stdout.log','stderr.log']:assert sha(p/n)==record[n+'_sha256']
 return {'components_value_parity':1104,'netted_pins_unchanged':len(nets(after)),'declared_metadata_changes':len(r['changes']),'all_copper_pads_fills_poses_unchanged':True,'unwaived_DSE_errors':4,'opens':1946,'missing_precision_MPNs':r['missing_precision_MPNs'],'qualified':False}
if __name__=='__main__':
 result=verify();(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
