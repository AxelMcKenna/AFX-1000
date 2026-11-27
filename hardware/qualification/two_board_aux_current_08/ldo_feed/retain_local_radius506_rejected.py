"""Copy exact native via-antipad corner runs only; reject all remote healing."""
import copy,json
from difflib import SequenceMatcher
from pathlib import Path
from shapely.geometry import Point
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from ..vin_escape.verify import saved_fill
from ..routed.plan import sha
H=Path(__file__).resolve().parent
CHOSEN={
 'c10eec5d-cf1f-58da-8d6d-48ce5d70e70d':{0:[('replace',10,11,10,34)]},
 'd5d0775a-fea7-5f03-bf2b-e5c7ca690024':{0:[('replace',64,65,65,77)]},
 '787e0385-5c4c-5b8f-9a2a-017054f7da0e':{0:[('insert',1244,1244,1191,1201)]},
 '1893ea20-0fe1-5364-8239-d1853c450ce0':{1:[('insert',911,911,922,928)]},
 '38c31b6e-bfc4-5702-b059-ff9efeabba60':{0:[('replace',529,530,529,547),('replace',688,689,707,725)]}}
def run():
 source=H/'inputs-IN-slot-01/power_protection.kicad_pcb';native=H/'native-IN-slot-01/selected-fill.kicad_pcb';tree=read_sexpr(source.read_text());nt=read_sexpr(native.read_text());nz={str(first(z,'uuid')[1]):z for z in children(nt,'zone')};results=[]
 for z in children(tree,'zone'):
  uid=str(first(z,'uuid')[1])
  if uid not in CHOSEN:continue
  old=saved_fill(z);ng=nz[uid];runs=[];rejected=[]
  for i,(f,nf) in enumerate(zip(children(z,'filled_polygon'),children(ng,'filled_polygon'))):
   a,b=first(f,'pts'),first(nf,'pts');co=lambda p:[tuple(map(float,x[1:])) for x in p[1:]]
   ops=[x for x in SequenceMatcher(None,co(a),co(b),autojunk=False).get_opcodes() if x[0]!='equal'];wanted=CHOSEN[uid].get(i,[])
   assert all(x in ops for x in wanted)
   for op in reversed(wanted):
    _,j,k,l,m=op;a[j+1:k+1]=copy.deepcopy(b[l+1:m+1])
   runs.extend({'polygon':i,'operation':op} for op in wanted);rejected.extend({'polygon':i,'operation':op} for op in ops if op not in wanted)
  new=saved_fill(z);removed=old.difference(new);added=new.difference(old)
  assert added.area<1e-8,(uid,added.area)
  assert removed.difference(Point(186.1,123.5).buffer(.506,resolution=128)).area<1e-9,(uid,removed.bounds)
  results.append({'uuid':uid,'copied_native_runs':runs,'rejected_native_runs':rejected,'removed_mm2':removed.area,'added_mm2':added.area,'removed_bounds_mm':list(removed.bounds)})
 target=H/'local-IN-slot-01.kicad_pcb';target.write_text(sexpr(tree)+'\n')
 result={'status':'local retention candidate; native audit required','source_sha256':sha(source),'selected_native_sha256':sha(native),'script_sha256':sha(Path(__file__)),'candidate_sha256':sha(target),'via_center_mm':[186.1,123.5],'nominal_antipad_radius_mm':.5,'native_corner_bound_radius_mm':.506,'physical_clearance_mm':.2,'zones':results,'all_other_zone_ASTs':'exact source retained','qualified':False}
 (H/'local-IN-slot-01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':run()
