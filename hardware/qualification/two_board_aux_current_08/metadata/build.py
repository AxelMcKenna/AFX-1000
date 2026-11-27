"""Align isolated PCB metadata and use a package-compatible timing capacitor."""
import copy,json,shutil,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from ..schematic_candidate.build import field
H=Path(__file__).resolve().parent; ROOT=H.parent
MPN='C0805C681J5GACTU';URL='https://search.kemet.com/component-documentation/download/specsheet/'+MPN
VALUES={'P_R108','P_R117','P_R118','P_R119','P_C109','E_R83','E_R84','E_R88','E_R89'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def props(x):return {p[1]:p for p in children(x,'property')}
def build():
 out=H/'authored';out.mkdir()
 source=ROOT/'held_cutover/authored'
 for p in source.iterdir():
  if p.is_dir(): (out/p.name).symlink_to(Path('../../held_cutover/authored')/p.name,target_is_directory=True)
  elif p.name!='candidate.json':shutil.copy2(p,out/p.name)
 path=out/'P_power_p03.kicad_sch';s=read_sexpr(path.read_text());sym=next(x for x in children(s,'symbol') if props(x)['Reference'][2]=='P_C109')
 for k,v in [('MPN',MPN),('Datasheet',URL),('Footprint','TB05_P_Capacitor_SMD:C_0805_2012Metric')]:field(sym,k,v)
 path.write_text(sexpr(s)+'\n')
 c={x.attrib['ref']:x for x in ET.parse(ROOT/'held_cutover/native-03/candidate-netlist.xml').findall('./components/comp')};board=read_sexpr((ROOT/'held_cell/native-local-02/power_protection.kicad_pcb').read_text());changes=[];seen=set()
 for f in children(board,'footprint'):
  p=props(f);r=p['Reference'][2]
  if r not in c:continue
  seen.add(r);comp=c[r];desired={'Value':comp.findtext('value')};fields={x.attrib['name']:x.text for x in comp.findall('./fields/field')}
  if fields.get('MPN'):desired['MPN']=fields['MPN'];desired['Datasheet']=comp.findtext('datasheet') or ''
  elif r in VALUES:desired['MPN']=''
  if r=='P_C109':desired.update(MPN=MPN,Datasheet=URL)
  for k,v in desired.items():
   old=p[k][2] if k in p else None
   if old==v:continue
   if k not in p:
    assert k in ['MPN','Datasheet'];q=copy.deepcopy(p['Datasheet']);q[1]=k;q[2]=v;f.append(q)
   else:p[k][2]=v
   changes.append(dict(ref=r,field=k,before=old,after=v))
 assert seen==set(c);assert {x['ref'] for x in changes if x['field']=='Value'}==VALUES
 (out/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n')
 for n in ['power_protection.kicad_pro','power_protection.kicad_dru','fp-lib-table']:shutil.copy2(ROOT/'held_cell/native-local-02'/n,out/n)
 report={'source_board_sha256':sha(ROOT/'held_cell/native-local-02/power_protection.kicad_pcb'),'source_netlist_sha256':sha(ROOT/'held_cutover/native-03/candidate-netlist.xml'),'source_schematic_sha256':{p.name:sha(p) for p in source.iterdir() if p.is_file()},'builder_sha256':sha(Path(__file__)),'native_script_sha256':sha(H/'native.py'),'primary_pdf_sha256':sha(H/'primary/c0805c681j5gactu.pdf'),'primary_url':URL,'candidate_board_sha256':sha(out/'power_protection.kicad_pcb'),'changes':changes,'library_sha256':{n:{str(p.relative_to(source/n)):sha(p) for p in (source/n).rglob('*') if p.is_file()} for n in ['libraries','symbols']},'missing_precision_MPNs':['E_R83','E_R84','E_R88','E_R89'],'qualified':False}
 (H/'changes.json').write_text(json.dumps(report,indent=2)+'\n');print(len(changes),'metadata changes; no geometry changes')
if __name__=='__main__':build()
