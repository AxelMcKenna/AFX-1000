"""Retain original fill except two source-observed local corner replacement runs."""
import json,copy
from difflib import SequenceMatcher
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr
from .verify import H,BASE,saved_fill,sha,nmshape
from shapely.geometry import Point
from shapely.ops import unary_union
U='bc76c316-2c04-5ecb-85b7-3e5f80b26bf1'
def run():
 prior=H/'native-01';tree=read_sexpr((prior/'authored.kicad_pcb').read_text());refill=read_sexpr((prior/'full-refill.kicad_pcb').read_text());z=next(z for z in children(tree,'zone') if first(z,'uuid')[1]==U);rz=next(z for z in children(refill,'zone') if first(z,'uuid')[1]==U);assert len(children(z,'filled_polygon'))==len(children(rz,'filled_polygon'))==1;old=copy.deepcopy(z);ap=first(children(z,'filled_polygon')[0],'pts');bp=first(children(rz,'filled_polygon')[0],'pts');coords=lambda ps:[tuple(float(v) for v in x[1:]) for x in ps[1:]];a,b=coords(ap),coords(bp);ops=[x for x in SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if x[0]!='equal'];assert [(i,j,k,l) for _,i,j,k,l in ops]==[(0,3,0,30),(57,59,84,86),(130,132,157,160),(163,164,191,192)]
 for _,i,j,k,l in reversed([ops[0],ops[-1]]):ap[i+1:j+1]=copy.deepcopy(bp[k+1:l+1])
 before,after=saved_fill(old),saved_fill(z);g=json.loads((prior/'added-copper-geometry.json').read_text());cu=unary_union([nmshape(o['layers_nm']['B.Cu']) for o in g['objects']]);r=before.difference(after);parts=list(r.geoms) if hasattr(r,'geoms') else[r];m=max(Point(v).distance(cu) for part in parts for v in part.exterior.coords);report={'source_board_sha256':sha(BASE/'power_protection.kicad_pcb'),'authored_board_sha256':sha(prior/'authored.kicad_pcb'),'native_full_refill_sha256':sha(prior/'full-refill.kicad_pcb'),'script_sha256':sha(H/'local_fill.py'),'added_mm2':after.difference(before).area,'removed_mm2':r.area,'max_removed_vertex_distance_from_new_tracks_mm':m,'retained_remote_change_runs':ops[1:3],'applied_local_change_runs':[ops[0],ops[-1]]};out=H/'local-fill.kicad_pcb';out.write_text(sexpr(tree)+'\n');report['candidate_sha256']=sha(out);(H/'local-fill.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':run()
