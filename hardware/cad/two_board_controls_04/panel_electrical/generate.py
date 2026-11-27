"""Generate independently specified passive-board schematics, without changing PCBs."""
import sys,json,copy,os
from contracts import *
sys.path.insert(0,str(REPO/'hardware/electronics'))
from common.flat_schematic import generate
from common.sexpr import read_sexpr,children,first

def local():
 result={}
 for name,(path,lib) in DESIGNS.items():
  spec=contract(name);cs=copy.deepcopy(spec['components'])
  # Wide spaced rows keep labels/values legible, including RGB branch nets.
  for i,c in enumerate(cs):c.update(x=63.5+(i%3)*114.3,y=38.1+(i//3)*50.8)
  out=R/'layouts'/name;out.mkdir(parents=True,exist_ok=True)
  generate(out,'PANEL_'+name,name,cs,[(15,12,'Independent passive PCB circuit; no fabrication release')],(370,max(120,65+((len(cs)+2)//3)*50)),[])
  fpdir=(CONTROLS/path).parent/(lib+'.pretty')
  (out/'fp-lib-table').write_text(f'(fp_lib_table (version 7) (lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/{os.path.relpath(fpdir,out)}") (options "") (descr "Frozen carrier footprint library")))\n')
  pcb=read_sexpr((CONTROLS/path).read_text());actual={};values={}
  for f in children(pcb,'footprint'):
   props={x[1]:x[2] for x in children(f,'property')};ref=props['Reference'];values[ref]=(props['Value'],f[1])
   for p in children(f,'pad'):
    ns=children(p,'net')
    if ns:actual.setdefault(ns[0][-1],[]).append(ref+'.'+p[1])
  assert values=={c['ref']:(c['part'],c['footprint']) for c in cs},name
  assert {k:sorted(v) for k,v in actual.items()}==groups(cs),name
  result[name]=dict(pcb=path,components=len(cs),nets=len(actual),independent_contract_matches_pcb=True)
 (R/'layout-contract-review.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':local()
