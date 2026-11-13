"""Center via endpoints and reroute around retained F.Cu ground; no fill changes."""
import copy,json,shutil,uuid
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,Atom
from ..ldo_local.immutable_inputs import prepare,sha
H=Path(__file__).resolve().parent
p=json.loads((H/'manifest-IN-slot-01.json').read_text());correction=json.loads((H/'route-correction.json').read_text());assert correction['script_sha256']==sha(H/'route_correction.py');routes=copy.deepcopy(p['routes']);routes[0]['path_mm'][-1]=[186.1,123.5];routes[1]['path_mm'][0]=[186.1,123.5];routes[2]['path_mm']=correction['routes'][0]['path_mm'];t=read_sexpr((H/'local-IN-slot-01.kicad_pcb').read_text());uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'RMX:IN-SLOT-01:'+s));by={str(first(x,'uuid')[1]):x for x in children(t,'segment')}
for i,r in enumerate(routes):
 for j,(a,b) in enumerate(zip(r['path_mm'],r['path_mm'][1:])):
  seg=by[uid(f'track:{i}:{j}')];first(seg,'start')[1:]=[Atom(str(round(x,6))) for x in a];first(seg,'end')[1:]=[Atom(str(round(x,6))) for x in b]
board=H/'corrected-IN-slot-02.kicad_pcb';board.write_text(sexpr(t)+'\n');stage=H/'review-stage-02';shutil.copytree(H.parent/'reference_fix/inputs-reference-09',stage);shutil.copy2(board,stage/'power_protection.kicad_pcb');m=prepare(stage,H/'inputs-review-02');m.update(bundle_name='inputs-review-02',source_board_sha256=p['source_board_sha256'],local_fill_candidate_sha256=sha(H/'local-IN-slot-01.kicad_pcb'),route_correction_sha256=sha(H/'route-correction.json'),routes=routes,qualified=False);(H/'review-manifest-02.json').write_text(json.dumps(m,indent=2)+'\n')
