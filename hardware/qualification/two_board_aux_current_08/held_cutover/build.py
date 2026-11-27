"""Explicit held-bypass reassignment, preserving unrelated circuits and positions."""
import json,shutil,math
from pathlib import Path
from ..schematic_candidate.build import retarget,pinpoint,H,field
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import prop
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'held_rail/authored';OUT=HERE/'authored'
AUX='PWR_V2V5_AUX';HELD='PWR_AUX_HELD3V3';CAPS=['E_C29','E_C36','E_C9','E_C13'];MPN='C0805C104K5RACTU';URL='https://search.kemet.com/component-documentation/download/specsheet/'+MPN
MOVES=[['E_C1','1',AUX],['E_C5','1',AUX],['E_C29','1',HELD],['E_C36','1',HELD]]
def build():
 assert not OUT.exists();shutil.copytree(SOURCE,OUT)
 files=[p for p in SOURCE.iterdir() if p.suffix in ['.kicad_sch','.kicad_pro'] or p.name in ['sym-lib-table','fp-lib-table']]
 e=read_sexpr((OUT/'E_rail_disconnect.kicad_sch').read_text())
 for ref,pin,new in MOVES:
  old=HELD if new==AUX else AUX;sym=next(s for s in children(e,'symbol') if prop(s,'Reference')[2]==ref);pt=pinpoint(e,sym,pin);direct=[l for l in children(e,'global_label')+children(e,'label') if math.dist(pt,list(map(float,first(l,'at')[1:3])))<1e-6]
  if direct:assert len(direct)==1 and direct[0][1]==old;direct[0][1]=new
  else:retarget(e,ref,pin,old,new)
 for l in children(e,'label'):
  if l[1] in [AUX,HELD]:l[0]=a('global_label');l.insert(2,[a('shape'),a('passive')])
 changed=[]
 for ref in CAPS:
  s=next(s for s in children(e,'symbol') if prop(s,'Reference')[2]==ref);old=prop(s,'Value')[2];new='100nF 50V X7R 10%';field(s,'Value',new);field(s,'MPN',MPN);field(s,'Datasheet',URL);changed.append({'ref':ref,'old_value':old,'new_value':new})
 (OUT/'E_rail_disconnect.kicad_sch').write_text(sexpr(e)+'\n');root=read_sexpr((OUT/'power_protection.kicad_sch').read_text());first(first(root,'title_block'),'rev')[1]='AUX-HELD-CUTOVER-01';(OUT/'power_protection.kicad_sch').write_text(sexpr(root)+'\n')
 manifest={'source_directory':'AUX-HELD-CANDIDATE-02','source_sha256':{p.name:H(p) for p in files},'builder_sha256':H(Path(__file__)),'changed_values':changed,'new_parts':[],'retargeted_existing_pins':MOVES,'PCB_emitted':False,'fabrication_released':False,'qualification':'Explicit capacitor ownership correction only. C29/C36 return loops and native supply branch cutover pending.','capacitor_mpn':MPN,'capacitor_primary_sha256':H(HERE/'primary/c0805c104k5ractu.pdf')}
 (OUT/'candidate.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':build()
