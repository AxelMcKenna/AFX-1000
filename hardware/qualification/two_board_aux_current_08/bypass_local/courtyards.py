"""Extract source footprint courtyard primitives without interpreting pad bodies as courtyards."""
import json
from .verify import H
from ..routed.plan import sha
from hardware.electronics.common.sexpr import read_sexpr,children,first

def extract():
 source=H.parent/'held_loops/native-02/power_protection.kicad_pcb';t=read_sexpr(source.read_text());out=[];unsupported=[]
 for f in children(t,'footprint'):
  if first(f,'layer')[1]!='F.Cu':continue
  ref=next(p[2] for p in children(f,'property') if p[1]=='Reference');ls=[l for l in children(f,'fp_line') if first(l,'layer')[1]=='F.CrtYd'];rect=[l for l in children(f,'fp_rect') if first(l,'layer')[1]=='F.CrtYd']
  unsupported.extend({'ref':ref,'kind':kind,'at':first(f,'at')[1:]} for kind in ['fp_arc','fp_poly','fp_circle','fp_curve'] for l in children(f,kind) if first(l,'layer')[1]=='F.CrtYd')
  out.append({'ref':ref,'at':[float(x) for x in first(f,'at')[1:]],'lines':[[[float(x) for x in first(l,k)[1:]] for k in ['start','end']] for l in ls],'rects':[[[float(x) for x in first(l,k)[1:]] for k in ['start','end']] for l in rect]})
 assert out==json.loads((H/'courtyards.json').read_text())
 return {'source_board_sha256':sha(source),'courtyards_sha256':sha(H/'courtyards.json'),'extractor_sha256':sha(H/'courtyards.py'),'front_footprints':len(out),'search_screen_omitted_curved_primitives':unsupported,'native_final_courtyard_check_includes_all_shapes':True}
if __name__=='__main__':(H/'courtyard-provenance.json').write_text(json.dumps(extract(),indent=2)+'\n')
