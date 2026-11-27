"""Conditional held-supply prototype derived from checked AUX candidate01."""
import copy,json,math,shutil
from pathlib import Path
from ..schematic_candidate.build import add,retarget,pinpoint,H,U,field,fx
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import prop
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'schematic_candidate/authored';OUT=HERE/'authored'
RESET='PWR_AUX_FAST_RESET_N';HELD='PWR_AUX_HELD3V3';AUX='PWR_V2V5_AUX';GND='PWR_AGND'
MOVES=[(r,'1') for r in ['E_U1','E_U2','E_U3','E_U4','E_C1','E_C5','E_C9','E_C13','E_C74','E_C76','E_R900','E_C900']]+[('E_U29','8'),('E_U31','8'),('E_U900','2')]
def build():
 assert not OUT.exists();OUT.mkdir()
 files=[p for p in SOURCE.iterdir() if p.suffix in ['.kicad_sch','.kicad_pro'] or p.name in ['sym-lib-table','fp-lib-table']]
 for p in files:shutil.copy2(p,OUT/p.name)
 for name in ['symbols','libraries']:shutil.copytree(SOURCE/name,OUT/name)
 e=read_sexpr((OUT/'E_rail_disconnect.kicad_sch').read_text());p=read_sexpr((OUT/'P_power_p03.kicad_sch').read_text())
 for ref,pin in MOVES:
  sym=next(s for s in children(e,'symbol') if prop(s,'Reference')[2]==ref);pt=pinpoint(e,sym,pin)
  direct=[l for l in children(e,'global_label')+children(e,'label') if math.dist(pt,list(map(float,first(l,'at')[1:3])))<1e-6]
  if direct:
   assert len(direct)==1 and direct[0][1]==AUX,(ref,pin,direct);direct[0][1]=HELD
  else:retarget(e,ref,pin,AUX,HELD)
 for label in children(e,'label'):
  if label[1]==HELD:label[0]=a('global_label');label.insert(2,[a('shape'),a('passive')])
 for label in children(e,'label'):
  if label[1]=='AUX_FAST_RESET_N':label[0]=a('global_label');label[1]=RESET;label.insert(2,[a('shape'),a('passive')])
 new=[];libs=[]
 def part(ref,val,mpn,url,pins,xy,fp=''):
  libs.append(add(p,ref,val,mpn,url,pins,xy,fp));new.append(dict(ref=ref,value=val,mpn=mpn,datasheet=url,pins={n:net for n,_,_,net in pins},footprint=fp))
 def passive(ref,val,mpn,url,n1,n2,xy,fp=''):
  part(ref,val,mpn,url,[('1','1','passive',n1),('2','2','passive',n2)],xy,fp)
 part('P_U901','TPS7A2033PDBVR','TPS7A2033PDBVR','https://www.ti.com/lit/ds/symlink/tps7a20.pdf',[
 ('1','IN','power_in','AUX_HELD_IN'),('2','GND','power_in',GND),('3','EN','input','AUX_HELD_IN'),('4','NC','passive',None),('5','OUT','power_out',HELD)],(150,3900),'TB05_P_Package_TO_SOT_SMD:SOT-23-5')
 passive('P_R902','4.7R 1% 100ppm','CRCW25124R70FKEG','https://www.vishay.com/docs/20035/dcrcwe3.pdf','AUX_PREREG5','AUX_HELD_IN',(350,3900))
 passive('P_C902','220uF 10V polymer 20%','T520D227M010ATE025','https://search.kemet.com/component-documentation/download/specsheet/T520D227M010ATE025','AUX_HELD_IN',GND,(550,3900))
 passive('P_C903','100nF 50V X7R 10%','C0603C104K5RACTU','https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU','AUX_HELD_IN',GND,(750,3900),'TB05_P_Capacitor_SMD:C_0603_1608Metric')
 passive('P_C904','2.2uF 50V X7R 10%','C3216X7R1H225K160AB','https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3216X7R1H225K160AB',HELD,GND,(950,3900),'TB05_P_Capacitor_SMD:C_1206_3216Metric')
 passive('P_R903','3.01k 0.1% 25ppm','TNPW08053K01BEEA','https://www.vishay.com/docs/28758/tnpw_e3.pdf',HELD,GND,(1150,3900),'TBP51_AUX:R_0805_Vishay_TNPW_28950')
 passive('P_C905','220uF 10V polymer 20%','T520D227M010ATE025','https://search.kemet.com/component-documentation/download/specsheet/T520D227M010ATE025','AUX_HELD_IN',GND,(350,4000))
 part('P_U902','TPS3703A5500DSER','TPS3703A5500DSER','https://www.ti.com/lit/ds/symlink/tps3703.pdf',[
 ('1','SENSE','input','AUX_PREREG5'),('2','VDD','power_in',HELD),('3','CT','input',None),('4','RESET','open_collector',RESET),('5','GND','power_in',GND),('6','MR','input',None)],(650,4000))
 passive('P_C906','100nF 50V X7R 10%','C0603C104K5RACTU','https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU',HELD,GND,(950,4000),'TB05_P_Capacitor_SMD:C_0603_1608Metric')
 flag=copy.deepcopy(next(s for s in children(p,'symbol') if first(s,'lib_id')[1].endswith(':SUPPLY_FLAG')))
 oldx,oldy=map(float,first(flag,'at')[1:3]);newx,newy=101.6,4076.7
 first(flag,'at')[1:3]=[newx,newy];first(flag,'uuid')[1]=U('held-input-flag')
 for propnode in children(flag,'property'):
  at=first(propnode,'at');at[1:3]=[float(at[1])+newx-oldx,float(at[2])+newy-oldy]
 field(flag,'Reference','#P_HELD900');field(flag,'Value','Held input powered through R902')
 for pin in children(flag,'pin'):first(pin,'uuid')[1]=U('held-flag-pin-'+str(pin[1]))
 first(first(first(first(flag,'instances'),'project'),'path'),'reference')[1]='#P_HELD900'
 p.append(flag);p.append([a('label'),'AUX_HELD_IN',[a('at'),newx,newy,0],fx(),[a('uuid'),U('held-input-flag-label')]])
 first(p,'paper')[1:]=['User',1300,4100]
 (OUT/'P_power_p03.kicad_sch').write_text(sexpr(p)+'\n');(OUT/'E_rail_disconnect.kicad_sch').write_text(sexpr(e)+'\n')
 root=read_sexpr((OUT/'power_protection.kicad_sch').read_text());first(first(root,'title_block'),'rev')[1]='AUX-HELD-CANDIDATE-02';(OUT/'power_protection.kicad_sch').write_text(sexpr(root)+'\n')
 libtree=read_sexpr((OUT/'symbols/AUX01.kicad_sym').read_text())
 for lib in libs:l=copy.deepcopy(lib);l[1]=l[1].split(':')[1];libtree.append(l)
 (OUT/'symbols/AUX01.kicad_sym').write_text(sexpr(libtree)+'\n')
 m=dict(source_directory='AUX-CANDIDATE-01',source_sha256={f.name:H(f) for f in files},builder_sha256=H(Path(__file__)),changed_values=[],new_parts=new,retargeted_existing_pins=[[r,p,HELD] for r,p in MOVES]+[[r,p,RESET] for r,p in [('E_U31','6'),('E_R900','2'),('E_U900','4')]],PCB_emitted=False,fabrication_released=False,qualification='Conditional receiving limits in analysis.json; current and capacitor bounds not yet accepted')
 (OUT/'candidate.json').write_text(json.dumps(m,indent=2)+'\n');print({'new_parts':len(new),'retargeted_pins':len(MOVES)})
if __name__=='__main__':build()
