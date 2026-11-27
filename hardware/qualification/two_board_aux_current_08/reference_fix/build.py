"""Correct C907 reference from mistaken global values to local footprint coordinates."""
import copy,json,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,Atom
from ..ldo_local.immutable_inputs import prepare,sha
H=Path(__file__).resolve().parent;SRC=H.parent/'ldo_local/inputs-local-return-08';STAGE=H/'stage-01';OUT=H/'inputs-reference-09'
def global_point(origin,angle,local):
 import math
 a=math.radians(angle);return [origin[0]+local[0]*math.cos(a)+local[1]*math.sin(a),origin[1]-local[0]*math.sin(a)+local[1]*math.cos(a)]
def run():
 assert not STAGE.exists();shutil.copytree(SRC,STAGE);board=read_sexpr((STAGE/'power_protection.kicad_pcb').read_text());fp=next(f for f in children(board,'footprint') if any(p[1:3]==['Reference','P_C907'] for p in children(f,'property')));ref=next(p for p in children(fp,'property') if p[1]=='Reference');before=copy.deepcopy(ref);assert first(ref,'at')[1:]==['184.5','129','0'];first(ref,'at')[1:]=[Atom('3'),Atom('-2.4'),Atom('0')];(STAGE/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n');r=prepare(STAGE,OUT);r.update(source_board_sha256=sha(SRC/'power_protection.kicad_pcb'),builder_sha256=sha(Path(__file__)),reference_before=before,reference_after=ref,expected_global_reference_mm=[184.5,129],old_mistaken_global_reference_mm=global_point([187.5,126.6],180,[184.5,129]),bundle_name=OUT.name);(H/'manifest.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':run()
