import copy,json,math
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first
from ..ldo_local.immutable_inputs import sha,check_tree,check_recorded
from .build import global_point
H=Path(__file__).resolve().parent
def position_gate(at,local,expected):
 point=global_point(at[:2],at[2],local);assert math.dist(point,expected)<1e-6

def bounds_gate(text,board):
 assert board[0]<=text[0]<=text[2]<=board[2] and board[1]<=text[1]<=text[3]<=board[3]

def verify():
 m=json.loads((H/'manifest.json').read_text());src=H.parent/'ldo_local/inputs-local-return-08';dst=H/m['bundle_name'];check_tree(dst,m);assert sha(src/'power_protection.kicad_pcb')==m['source_board_sha256'] and sha(H/'build.py')==m['builder_sha256']
 a=read_sexpr((src/'power_protection.kicad_pcb').read_text());b=read_sexpr((dst/'power_protection.kicad_pcb').read_text());f=next(f for f in children(a,'footprint') if any(p[1:3]==['Reference','P_C907'] for p in children(f,'property')));r=next(p for p in children(f,'property') if p[1]=='Reference');assert r==m['reference_before'];r[:]=m['reference_after'];assert a==b;position_gate(list(map(float,first(f,'at')[1:])),list(map(float,first(r,'at')[1:3])),[184.5,129])
 for n,h in m['files'].items():
  if n!='power_protection.kicad_pcb':assert sha(src/n)==h
 nr=json.loads((H/'native-02/review.json').read_text());assert nr['manifest_sha256']==sha(H/'manifest.json') and nr['script_sha256']==sha(H/'native.py') and nr['candidate_board_sha256']==sha(dst/'power_protection.kicad_pcb') and nr['reference_global_mm']==[184.5,129.0] and nr['reference_bbox_inside_board_bbox'] and nr['native_parity_issues']==0
 bounds_gate(nr['reference_bbox_mm'],nr['board_bbox_mm'])
 assert nr['parity_sha256']==sha(H/'native-02/parity.json');p=json.loads((H/'native-02/parity-process/process.json').read_text());inputs=[dst/'power_protection.kicad_pcb',*sorted(dst.glob('*.kicad_sch'))];check_recorded(p,{'/repo/'+str(x.relative_to(H.parents[3])):sha(x) for x in inputs})
 for log in ['stdout.log','stderr.log']:assert sha(H/'native-02/parity-process'/log)==p[log+'_sha256']
 pr=json.loads((H/'native-02/parity.json').read_text());old=json.loads((H.parent/'ldo_local/native-08/parity.json').read_text());assert not pr['schematic_parity'] and sorted(pr['violations'],key=lambda x:json.dumps(x,sort_keys=True))==sorted(old['violations'],key=lambda x:json.dumps(x,sort_keys=True))
 result={'reference_global_mm':nr['reference_global_mm'],'reference_local_mm':[3,-2.4],'only_C907_reference_position_changed':True,'native_parity_issues':0,'unwaived_DSE_errors':4,'candidate':str(dst.relative_to(H))+'/power_protection.kicad_pcb','qualified':False};(H/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':verify()
