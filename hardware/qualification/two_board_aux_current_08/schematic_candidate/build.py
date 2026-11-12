"""Reproducible isolated AUX candidate; never modifies source or emits a PCB."""
import copy,hashlib,json,math,shutil,sys,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import prop
HERE=Path(__file__).resolve().parent
U=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:AUX-CANDIDATE-01:'+s))
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CHANGES={'P_R108':'17.6k 0.1% 25ppm','E_R83':'10.7k 0.01% 5ppm','E_R84':'5.76k 0.01% 5ppm','E_R88':'16.2k 0.01% 5ppm','E_R89':'13.3k 0.01% 5ppm','P_R118':'18k 0.1% 10ppm','P_R119':'11.7k 0.1% 10ppm','P_R117':'392k 0.1% 10ppm','P_C109':'680pF 50V C0G 5%'}
def fx():return [a('effects'),[a('font'),[a('size'),1.27,1.27]]]
def field(s,n,v):
 p=next((p for p in children(s,'property') if p[1]==n),None)
 if p:p[2]=v
 else:s.append([a('property'),n,v,copy.deepcopy(first(s,'at')),[a('effects'),[a('font'),[a('size'),1.27,1.27]],[a('hide'),a('yes')]]])
def pinpoint(sheet,s,pn):
 lib=next(x for x in children(first(sheet,'lib_symbols'),'symbol') if x[1]==first(s,'lib_id')[1]);p=next(p for u in children(lib,'symbol') for p in children(u,'pin') if str(first(p,'number')[1])==pn)
 x,y,ang=map(float,first(s,'at')[1:]);assert ang==0
 px,py=map(float,first(p,'at')[1:3]);return [x+px,y-py]
def retarget(sheet,ref,pn,old,new):
 s=next(s for s in children(sheet,'symbol') if prop(s,'Reference')[2]==ref);pt=pinpoint(sheet,s,pn)
 w=[w for w in children(sheet,'wire') if any(math.dist(pt,list(map(float,p[1:3])))<1e-6 for p in children(first(w,'pts'),'xy'))];assert len(w)==1
 end=next(list(map(float,p[1:3])) for p in children(first(w[0],'pts'),'xy') if math.dist(pt,list(map(float,p[1:3])))>1e-6)
 ls=[l for t in ['label','global_label'] for l in children(sheet,t) if math.dist(end,list(map(float,first(l,'at')[1:3])))<1e-6];assert len(ls)==1 and ls[0][1]==old,(ref,pn,ls)
 ls[0][1]=new
 # New nets stay local to their respective sheet.
 if ls[0][0]=='global_label':ls[0][0]=a('label');ls[0][:]=[n for n in ls[0] if not(isinstance(n,list) and n[0]=='shape')]
def add(sheet,ref,value,mpn,url,pins,xy,footprint=''):
 """pins=(number,name,electrical type,net); None net gets explicit NC."""
 name='AUX01:'+ref;h=5.08*(len(pins)+1)/2
 lib=[a('symbol'),name,[a('pin_names'),[a('offset'),.508]],[a('in_bom'),a('yes')],[a('on_board'),a('yes')],
 [a('property'),'Reference',ref[0],[a('at'),0,h+2.54,0],fx()],[a('property'),'Value',value,[a('at'),0,-h-2.54,0],fx()],
 [a('symbol'),ref+'_0_1',[a('rectangle'),[a('start'),-12.7,h],[a('end'),12.7,-h],[a('stroke'),[a('width'),.254],[a('type'),a('default')]],[a('fill'),[a('type'),a('none')]]]]]
 unit=[a('symbol'),ref+'_1_1'];x,y=[round(v/1.27)*1.27 for v in xy]
 s=[a('symbol'),[a('lib_id'),name],[a('at'),x,y,0],[a('unit'),1],[a('in_bom'),a('yes')],[a('on_board'),a('yes')],[a('dnp'),a('no')],[a('uuid'),U(ref)]]
 for n,v,dy in [('Reference',ref,-h-2.54),('Value',value,h+2.54),('Footprint',footprint,0),('Datasheet',url,0),('MPN',mpn,0)]:
  f=fx()
  if n not in ['Reference','Value']:f.append([a('hide'),a('yes')])
  s.append([a('property'),n,v,[a('at'),x,y+dy,0],f])
 for i,(num,pname,ptype,net) in enumerate(pins):
  py=h-5.08*(i+1);px=-15.24
  unit.append([a('pin'),a(ptype),a('line'),[a('at'),px,py,0],[a('length'),2.54],[a('name'),pname,fx()],[a('number'),num,fx()]])
  s.append([a('pin'),num,[a('uuid'),U(ref+':'+num)]])
  pt=[x+px,y-py]
  if net is None:sheet.append([a('no_connect'),[a('at'),*pt],[a('uuid'),U(ref+':NC:'+num)]])
  else:
   tag='global_label' if net.startswith('PWR_') else 'label'
   l=[a(tag),net]
   if tag=='global_label':l.append([a('shape'),a('passive')])
   f=fx();f.append([a('justify'),a('right'),a('bottom')]);l.extend([[a('at'),*pt,0],f,[a('uuid'),U(ref+':label:'+num)]])
   sheet.append(l)
 lib.append(unit);first(sheet,'lib_symbols').append(lib)
 template=next(s for s in children(sheet,'symbol') if children(s,'instances'))
 inst=copy.deepcopy(first(template,'instances'));path=first(first(inst,'project'),'path');first(path,'reference')[1]=ref;s.append(inst);sheet.append(s)
 return lib

def build(source,out):
 assert not out.exists();out.mkdir(parents=True)
 files=[p for p in source.iterdir() if p.suffix in ['.kicad_sch','.kicad_pro'] or p.name in ['sym-lib-table','fp-lib-table']]
 for p in files:shutil.copy2(p,out/p.name)
 for name in ['symbols','libraries']:shutil.copytree(source/name,out/name)
 hashes={p.name:H(p) for p in files};schematics={p.name:read_sexpr(p.read_text()) for p in files if p.suffix=='.kicad_sch'};changes=[];libs=[]
 for fn,sheet in schematics.items():
  for sym in children(sheet,'symbol'):
   ref=prop(sym,'Reference')[2]
   if ref not in CHANGES:continue
   changes.append({'ref':ref,'old_value':prop(sym,'Value')[2],'new_value':CHANGES[ref]});field(sym,'Value',CHANGES[ref])
   if ref=='P_R108':field(sym,'MPN','TNPW080517K6BEEA')
   if ref in ['P_R117','P_R118','P_R119']:
    field(sym,'MPN',{'P_R117':'TNPW0805392KBYEA','P_R118':'TNPW080518K0BYEA','P_R119':'TNPW080511K7BYEA'}[ref]);field(sym,'Datasheet','https://www.vishay.com/docs/28758/tnpw_e3.pdf')
   if ref=='P_C109':
    field(sym,'MPN','C1608C0G1H681J080AA');field(sym,'Footprint','TB05_P_Capacitor_SMD:C_0603_1608Metric');field(sym,'Datasheet','https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608C0G1H681J080AA')
 p=schematics['P_power_p03.kicad_sch'];e=schematics['E_rail_disconnect.kicad_sch']
 for ref,pn in [('P_U102','8'),('P_U102','5'),('P_C102','1')]:retarget(p,ref,pn,'VIN_IC','AUX_PREREG5')
 retarget(e,'E_U31','6','PWR_V2V5_AUX','AUX_FAST_RESET_N')
 new=[]
 def part(sheet,ref,value,mpn,url,pins,xy,fp=''):
  libs.append(add(sheet,ref,value,mpn,url,pins,xy,fp));new.append(dict(ref=ref,value=value,mpn=mpn,datasheet=url,pins={n:net for n,_,_,net in pins},footprint=fp))
 pg='PWR_AGND';aux='PWR_V2V5_AUX'
 part(p,'P_U900','TPS62175DQCR','TPS62175DQCR','https://www.ti.com/lit/ds/symlink/tps62175.pdf',[
 ('1','PGND','power_in',pg),('2','VIN','power_in','VIN_IC'),('3','EN','input','VIN_IC'),('4','NC','passive',pg),('5','FB','input','AUX_PREREG_FB'),('6','AGND','power_in',pg),('7','PG','open_collector',None),('8','SLEEP','input','AUX_PREREG5'),('9','SW','power_out','AUX_PREREG_SW'),('10','VOS','input','AUX_PREREG5'),('11','EP','power_in',pg)],(150,3650))
 def passive(sheet,ref,val,mpn,url,n1,n2,xy,fp=''):
  part(sheet,ref,val,mpn,url,[('1','1','passive',n1),('2','2','passive',n2)],xy,fp)
 passive(p,'P_L900','10uH 20%','XAL4040-103MEC','https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xal/xal40xx/xal4040-103/','AUX_PREREG_SW','AUX_PREREG5',(350,3650))
 passive(p,'P_C900','2.2uF 50V X7R 10%','C3216X7R1H225K160AB','https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3216X7R1H225K160AB','VIN_IC',pg,(550,3650),'TB05_P_Capacitor_SMD:C_1206_3216Metric')
 passive(p,'P_C901','22uF 16V X7R 10%','C3225X7R1C226K250AC','https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7R1C226K250AC','AUX_PREREG5',pg,(750,3650),'TB05_P_Capacitor_SMD:C_1210_3225Metric')
 for ref,val,mpn,nn,xy in [('P_R900','105k 0.1% 25ppm','TNPW0805105KBEEA',('AUX_PREREG5','AUX_PREREG_FB'),(950,3650)),('P_R901','20k 0.1% 25ppm','TNPW080520K0BEEA',('AUX_PREREG_FB',pg),(1150,3650))]:passive(p,ref,val,mpn,'https://www.vishay.com/docs/28758/tnpw_e3.pdf',*nn,xy,'TBP51_AUX:R_0805_Vishay_TNPW_28950')
 y=max(float(first(x,'at')[2]) for x in children(e,'symbol'))+150
 part(e,'E_U900','TPS3703A5330DSER','TPS3703A5330DSER','https://www.ti.com/lit/ds/symlink/tps3703.pdf',[
 ('1','SENSE','input',aux),('2','VDD','power_in',aux),('3','CT','input',None),('4','RESET','open_collector','AUX_FAST_RESET_N'),('5','GND','power_in',pg),('6','MR','input',None)],(150,y))
 passive(e,'E_R900','10k 0.1% 25ppm','TNPW080510K0BEEA','https://www.vishay.com/docs/28758/tnpw_e3.pdf',aux,'AUX_FAST_RESET_N',(400,y),'TB05_E_Resistor_SMD:R_0805_2012Metric')
 passive(e,'E_C900','100nF 50V X7R 10%','C0603C104K5RACTU','https://search.kemet.com/component-documentation/download/specsheet/C0603C104K5RACTU',aux,pg,(650,y),'TB05_P_Capacitor_SMD:C_0603_1608Metric')
 # Output is energized through L900; KiCad does not propagate power types
 # through passives. Declare that explicit source without hiding ERC rules.
 flag=copy.deepcopy(next(s for s in children(p,'symbol') if first(s,'lib_id')[1].endswith(':SUPPLY_FLAG')))
 oldx,oldy=map(float,first(flag,'at')[1:3]);newx,newy=101.6,3733.8
 first(flag,'at')[1:3]=[newx,newy];first(flag,'uuid')[1]=U('prereg-output-flag')
 for propnode in children(flag,'property'):
  at=first(propnode,'at');at[1:3]=[float(at[1])+newx-oldx,float(at[2])+newy-oldy]
 field(flag,'Reference','#P_AUX900');field(flag,'Value','AUX preregulator output via L900')
 for pin in children(flag,'pin'):first(pin,'uuid')[1]=U('flag-pin-'+str(pin[1]))
 first(first(first(first(flag,'instances'),'project'),'path'),'reference')[1]='#P_AUX900'
 p.append(flag);p.append([a('label'),'AUX_PREREG5',[a('at'),newx,newy,0],fx(),[a('uuid'),U('prereg-output-flag-label')]])
 first(p,'paper')[1:]=['User',1300,3800];first(e,'paper')[1:]=['User',1800,y+100]
 first(first(schematics['power_protection.kicad_sch'],'title_block'),'rev')[1]='AUX-CANDIDATE-01'
 for fn,s in schematics.items():(out/fn).write_text(sexpr(s)+'\n')
 libtree=[a('kicad_symbol_lib'),[a('version'),20241209],[a('generator'),a('kicad_symbol_editor')]]
 for lib in libs:l=copy.deepcopy(lib);l[1]=l[1].split(':')[1];libtree.append(l)
 (out/'symbols/AUX01.kicad_sym').write_text(sexpr(libtree)+'\n')
 t=read_sexpr((out/'sym-lib-table').read_text());t.append([a('lib'),[a('name'),'AUX01'],[a('type'),'KiCad'],[a('uri'),'${KIPRJMOD}/symbols/AUX01.kicad_sym'],[a('options'),''],[a('descr'),'Isolated AUX architecture candidate']]);(out/'sym-lib-table').write_text(sexpr(t)+'\n')
 manifest=dict(source_directory=source.name,source_sha256=hashes,builder_sha256=H(Path(__file__)),changed_values=changes,new_parts=new,retargeted_existing_pins=[['P_U102','8','AUX_PREREG5'],['P_U102','5','AUX_PREREG5'],['P_C102','1','AUX_PREREG5'],['E_U31','6','AUX_FAST_RESET_N']],PCB_emitted=False,fabrication_released=False)
 (out/'candidate.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({'changed_values':len(changes),'new_parts':len(new),'source_files':len(files)}))
if __name__=='__main__':build(Path(sys.argv[1]),Path(sys.argv[2]))
