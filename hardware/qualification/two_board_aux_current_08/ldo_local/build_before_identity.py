"""Add only the selected local LDO input bypass to isolated schematic/BOM."""
import copy,csv,json,shutil,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,Atom
from ..routed.plan import sha
from ..schematic_candidate.build import field
H=Path(__file__).resolve().parent;SRC=H.parent/'precision/authored';OUT=H/'authored';MPN='C0603C105K3RACTU';URL='https://search.kemet.com/component-documentation/download/specsheet/C0603C105K3RAC7867'
def run():
 assert not OUT.exists();shutil.copytree(SRC,OUT,symlinks=True);shutil.copy2(H.parent/'main_ldo/native-03/power_protection.kicad_pcb',OUT/'power_protection.kicad_pcb');path=OUT/'P_power_p03.kicad_sch';t=read_sexpr(path.read_text());s=copy.deepcopy(next(x for x in children(t,'symbol') if any(p[1:3]==['Reference','P_C906'] for p in children(x,'property'))))
 def change(x):
  if not isinstance(x,list):return
  if x and x[0]=='uuid':x[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:LDO-LOCAL-C907:'+str(x[1])))
  if x and x[0]=='at':x[1]=Atom(str(float(x[1])+101.6))
  if x and x[0]=='reference' and x[1]=='P_C906':x[1]='P_C907'
  for y in x:change(y)
 change(s)
 for key,value in [('Reference','P_C907'),('Value','1uF 25V X7R 10%'),('MPN',MPN),('Datasheet',URL)]:field(s,key,value)
 t.append(s);pinpositions=[(1036.32,3997.96),(1036.32,4003.04)]
 for name,(x,y) in zip(['AUX_PREREG5','PWR_AGND'],pinpositions):
  label=copy.deepcopy(next(l for l in children(t,'global_label') if l[1]=='PWR_AGND' and first(l,'at')[1:3]==[Atom('934.72'),Atom('4003.04')]))
  label[1]=name;first(label,'at')[1:3]=[Atom(str(x)),Atom(str(y))];first(label,'uuid')[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:C907-label:'+name))
  if name=='AUX_PREREG5':label[0]=Atom('label');label[:]=[v for v in label if not isinstance(v,list) or v[0]!='shape']
  t.append(label)
 path.write_text(sexpr(t)+'\n');rows=list(csv.DictReader((H.parent/'precision/candidate-bom.csv').open()));assert not any(r['Reference']=='P_C907' for r in rows);rows.append({'Reference':'P_C907','Value':'1uF 25V X7R 10%','MPN':MPN,'Schematic footprint':'TB05_P_Capacitor_SMD:C_0603_1608Metric','Datasheet':URL})
 with (H/'candidate-bom.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 result={'builder_sha256':sha(H/'build.py'),'source_schematic_sha256':{p.name:sha(p) for p in SRC.glob('*.kicad_sch')},'source_netlist_sha256':sha(H.parent/'precision/native-01/candidate-netlist.xml'),'source_bom_sha256':sha(H.parent/'precision/candidate-bom.csv'),'candidate_schematic_sha256':{p.name:sha(p) for p in OUT.glob('*.kicad_sch')},'candidate_bom_sha256':sha(H/'candidate-bom.csv'),'datasheet_sha256':sha(H/'primary/c0603c105k3ractu.pdf'),'added_part':'P_C907','added_pin_nets':{'1':'/P_power_supply/AUX_PREREG5','2':'PWR_AGND'},'old_pin_changes':{},'qualified':False};(H/'schematic-changes.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':run()
