"""Verify source ordering codes, exact metadata deltas, native nets and retained copper."""
import json,xml.etree.ElementTree as ET
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..metadata.verify import exact_delta,nets
from ..metadata.build import props,sha
from ..held_cell.verify_plane import library_link
from .select import PARTS
H=Path(__file__).resolve().parent;ROOT=H.parent;BASE=ROOT/'reference_bridge/native-01';OUT=H/'native-01'
def canonical(e):return(e.tag,tuple(sorted(e.attrib.items())),(e.text or '').strip(),tuple(sorted(canonical(c) for c in e)))
def selection_valid(selected):
 assert set(selected)==set(PARTS)
 for ref,(code,ohms) in PARTS.items():assert selected[ref]['MPN']=='PLT0805Z'+code+'LST1' and selected[ref]['nominal_ohm']==ohms and int(code[:3])*10**int(code[3])==ohms and selected[ref]['initial_tolerance_fraction']==.0001 and selected[ref]['TCR_ppm_per_C']==5
def verify():
 sel=json.loads((H/'selection.json').read_text());r=json.loads((H/'changes.json').read_text());assert len(sel['parts'])==4;selected={p['ref']:p for p in sel['parts']};assert set(selected)==set(PARTS)
 for n,v in sel['source_sha256'].items():assert sha(H/n)==v
 selection_valid(selected)
 for k,p in [('source_board_sha256',BASE/'power_protection.kicad_pcb'),('source_netlist_sha256',ROOT/'metadata/native-01/candidate-netlist.xml'),('candidate_board_sha256',OUT/'power_protection.kicad_pcb'),('builder_sha256',H/'build.py'),('selection_sha256',H/'selection.json'),('native_script_sha256',H/'native.py')]:assert r[k]==sha(p)
 for n,v in r['source_schematic_sha256'].items():assert sha(ROOT/'metadata/authored'/n)==v
 for n in ['libraries','symbols']:
  link=H/'authored'/n;target=(ROOT/'held_cutover/authored'/n).resolve();assert link.is_symlink() and link.resolve(strict=True)==target and target.is_relative_to(ROOT.resolve());assert {str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()}==r['library_sha256'][n]
 old,new=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]];exact_delta(old,new,r['changes']);assert len(r['changes'])==8 and {(d['ref'],d['field']) for d in r['changes']}=={(ref,f) for ref in PARTS for f in ['MPN','Datasheet']}
 before,after=[ET.parse(p) for p in [ROOT/'metadata/native-01/candidate-netlist.xml',OUT/'candidate-netlist.xml']];assert nets(before)==nets(after);a,b=[{c.attrib['ref']:c for c in t.findall('./components/comp')} for t in [before,after]];assert set(a)==set(b) and len(a)==1104
 for ref in PARTS:
  comp=a[ref];p=selected[ref];ds=comp.find('datasheet')
  if ds is None:ds=ET.SubElement(comp,'datasheet')
  ds.text=p['datasheet']
  for key,value in [('MPN',p['MPN']),('Datasheet',p['datasheet'])]:
   f=next((x for x in comp.findall('./fields/field') if x.attrib['name']==key),None)
   if f is None:f=ET.SubElement(comp.find('fields'),'field',name=key)
   f.text=value
  prop=next((x for x in comp.findall('property') if x.attrib['name']=='MPN'),None)
  if prop is None:prop=ET.SubElement(comp,'property',name='MPN')
  prop.attrib['value']=p['MPN']
 for ref in a:assert canonical(a[ref])==canonical(b[ref]),ref
 pcb={props(f)['Reference'][2]:f for f in children(new,'footprint')}
 for ref,c in b.items():
  pp=props(pcb[ref]);assert pp['Value'][2]==c.findtext('value');fs={f.attrib['name']:f.text for f in c.findall('./fields/field')}
  if fs.get('MPN'):assert pp['MPN'][2]==fs['MPN']
 for ref in PARTS:
  pads=children(pcb[ref],'pad');assert len(pads)==2;assert sorted(float(first(p,'at')[1]) for p in pads)==[-.9125,.9125];assert all(list(map(float,first(p,'size')[1:]))==[1.025,1.4] for p in pads)
 olderc,erc=[json.loads(p.read_text()) for p in [ROOT/'metadata/native-01/candidate-erc.json',OUT/'candidate-erc.json']];assert olderc['sheets']==erc['sheets'];oldrc,drc=[json.loads((d/'drc.json').read_text()) for d in [BASE,OUT]];key=lambda x:json.dumps(x,sort_keys=True);assert sorted(oldrc['violations'],key=key)==sorted(drc['violations'],key=key) and len(drc['violations'])==4
 for name in ['netlist','erc','drc']:
  d=OUT/(name+'-process');p=json.loads((d/'process.json').read_text());assert p['status']=='passed' and all(p['inputs_unchanged'].values())
  for log in ['stdout.log','stderr.log']:assert p[log+'_sha256']==sha(d/log)
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:assert (BASE/n).read_bytes()==(OUT/n).read_bytes()
 library_link(OUT/'libraries',json.loads((ROOT/'held_cell/library-binding.json').read_text()),H.parents[3],ROOT/'shared_cutover/native-04/libraries')
 return {'exact_precision_MPNs':{r:p['MPN'] for r,p in selected.items()},'components':1104,'unchanged_netted_pins':len(nets(after)),'all_values_copper_pad_poses_fills_unchanged':True,'unwaived_DSE_errors':4,'stock_confirmed':False,'service_life_qualified':False,'qualified':False}
if __name__=='__main__':
 result=verify();(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
