"""Restore exact source zone ASTs after native no-refill serialization."""
import copy,json,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from ..ldo_local.immutable_inputs import prepare,sha
H=Path(__file__).resolve().parent;Q=H.parent
source=Q/'reference_fix/inputs-reference-09/power_protection.kicad_pcb';native=H/'native-02/power_protection.kicad_pcb';a=read_sexpr(source.read_text());b=read_sexpr(native.read_text());zs={str(first(z,'uuid')[1]):z for z in children(a,'zone')};assert set(zs)=={str(first(z,'uuid')[1]) for z in children(b,'zone')}
b[:]=[copy.deepcopy(zs[str(first(x,'uuid')[1])]) if isinstance(x,list) and x[0]=='zone' else x for x in b];target=H/'retained-candidate.kicad_pcb';target.write_text(sexpr(b)+'\n')
stage=H/'review-stage-02';shutil.copytree(Q/'reference_fix/inputs-reference-09',stage);shutil.copy2(target,stage/'power_protection.kicad_pcb');m=prepare(stage,H/'inputs-review-02');m.update(bundle_name='inputs-review-02',source_board_sha256=sha(source),authored_native_sha256=sha(native),retained_source_zones=50)
(H/'review-manifest-02.json').write_text(json.dumps(m,indent=2)+'\n')
