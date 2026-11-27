"""Retain source F.Cu ground except the native corner run clearing new C907.1."""
import json,copy
from difflib import SequenceMatcher
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from ..routed.plan import sha
from ..vin_escape.verify import saved_fill
from .screen import H,BASE
U='d0572a8e-b95d-5c59-9a7c-1d3514a507b4'
def run():
 src=read_sexpr((BASE/'power_protection.kicad_pcb').read_text());tree=read_sexpr((H/'native-02/power_protection.kicad_pcb').read_text());orig={first(z,'uuid')[1]:z for z in children(src,'zone')};native=copy.deepcopy(next(z for z in children(tree,'zone') if first(z,'uuid')[1]==U));tree[:]=[copy.deepcopy(orig[first(x,'uuid')[1]]) if isinstance(x,list) and x[0]=='zone' else x for x in tree];z=next(z for z in children(tree,'zone') if first(z,'uuid')[1]==U);a=first(children(z,'filled_polygon')[0],'pts');b=first(children(native,'filled_polygon')[0],'pts');coords=lambda p:[tuple(map(float,x[1:])) for x in p[1:]];ops=[x for x in SequenceMatcher(None,coords(a),coords(b),autojunk=False).get_opcodes() if x[0]!='equal'];assert ops[0]==('replace',118,138,118,132);i,j,k,l=ops[0][1:];a[i+1:j+1]=copy.deepcopy(b[k+1:l+1]);old,new=saved_fill(orig[U]),saved_fill(z);assert new.difference(old).area<1e-9;out=H/'local-fill.kicad_pcb';out.write_text(sexpr(tree)+'\n');result={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'native_source_sha256':sha(H/'native-02/power_protection.kicad_pcb'),'script_sha256':sha(H/'local_fill.py'),'candidate_sha256':sha(out),'applied_native_run':ops[0],'rejected_remote_native_runs':ops[1:],'rejected_native_extra_polygons':len(children(native,'filled_polygon'))-1,'removed_mm2':old.difference(new).area,'added_mm2':new.difference(old).area,'qualified':False};(H/'local-fill.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':run()
