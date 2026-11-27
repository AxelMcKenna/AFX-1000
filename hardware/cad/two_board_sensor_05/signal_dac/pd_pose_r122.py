"""Pinned Linux serialization of the one declared footprint pose; not an accepted board."""
import sys,json,hashlib
from pathlib import Path
assert sys.platform=='linux'
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
R=Path(__file__).resolve().parent;O=R/sys.argv[1];B=R/'native-r107/signal_main.kicad_pcb';assert O.is_dir()and not list(O.iterdir());p=json.loads((R/'pd-plan-r121.json').read_text());assert p['move']['after_mm']==[75.8,65.2]and p['move']['orientation_degrees']==90
b=pcbnew.LoadBoard(str(B));f=next(f for f in b.GetFootprints()if f.GetReference()=='A_D101');beforepads={x.GetNumber():[x.GetPosition().x/1e6,x.GetPosition().y/1e6]for x in f.Pads()};f.SetOrientationDegrees(90);f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(75.8),pcbnew.FromMM(65.2)))
rows=[]
for pad in f.Pads():
 old=beforepads[pad.GetNumber()];expected=[75.8+old[1]-66,65.2-(old[0]-75)];actual=[pad.GetPosition().x/1e6,pad.GetPosition().y/1e6];assert all(abs(x-y)<1e-6 for x,y in zip(actual,expected));rows.append({'number':pad.GetNumber(),'net':pad.GetNetname(),'before_mm':old,'after_mm':actual,'orientation_degrees':pad.GetOrientation().AsDegrees()})
output=O/'signal_main.kicad_pcb';pcbnew.SaveBoard(str(output),b)
def objects(path):
 t=read_sexpr(path.read_text());out={}
 for row in t:
  if not isinstance(row,list)or not children(row,'uuid'):continue
  out[first(row,'uuid')[1]]=sexpr(row)
 return out
old,new=objects(B),objects(output);changed=[u for u,v in old.items()if new.get(u)!=v];assert changed==['8faa53e9-5e58-5636-a554-f778027070b5'];assert set(old)==set(new)
report={'source_sha256':{str(x.relative_to(R.parents[3])):hashlib.sha256(x.read_bytes()).hexdigest()for x in [Path(__file__),B,R/'pd-plan-r121.json']},'declared_pose_change':{'uuid':changed[0],'reference':'A_D101','before_sexpr':old[changed[0]],'after_sexpr':new[changed[0]]},'exact_pad_world_coordinates':rows,'all_other_authored_objects_and_fill_unchanged':True,'output_pcb_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'accepted':False};(O/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS one footprint pose serialized, exact pads, all other authored objects and fill unchanged')
