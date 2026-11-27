"""Align schematic/BOM footprint identifiers with existing placed assembly variants."""
import csv,json,hashlib,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,sexpr
from ..associations.paths import NEW_REFS
H=Path(__file__).resolve().parents[1];D=Path(__file__).resolve().parent;SRC=H/'associations/authored';OUT=D/'authored';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def props(n):return {p[1]:p for p in children(n,'property')}
def run():
 shutil.copytree(SRC,OUT,symlinks=True);board=read_sexpr((SRC/'power_protection.kicad_pcb').read_text());ids={props(f)['Reference'][2]:f[1] for f in children(board,'footprint') if props(f)['Reference'][2] in NEW_REFS};assert set(ids)==NEW_REFS
 delta=[]
 for p in sorted(OUT.glob('*.kicad_sch')):
  tree=read_sexpr(p.read_text());changed=False
  for s in children(tree,'symbol'):
   ps=props(s);ref=ps.get('Reference',[None,None,None])[2]
   if ref in ids:
    assert ps['Footprint'][2]!=ids[ref];delta.append({'sheet':p.name,'reference':ref,'before':ps['Footprint'][2],'after':ids[ref]});ps['Footprint'][2]=ids[ref];changed=True
  if changed:p.write_text(sexpr(tree)+'\n')
 assert {d['reference'] for d in delta}==NEW_REFS and len(delta)==18
 bom=H/'precision/candidate-bom.csv'
 with bom.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
 for r in rows:
  if r['Reference'] in ids:r['Schematic footprint']=ids[r['Reference']]
 with (D/'candidate-bom.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 report={'changes':delta,'source_board_sha256':sha(SRC/'power_protection.kicad_pcb'),'source_schematic_sha256':{p.name:sha(p) for p in SRC.glob('*.kicad_sch')},'candidate_schematic_sha256':{p.name:sha(p) for p in OUT.glob('*.kicad_sch')},'source_bom_sha256':sha(bom),'candidate_bom_sha256':sha(D/'candidate-bom.csv'),'builder_sha256':sha(Path(__file__)),'source_association_changes_sha256':sha(H/'associations/changes.json')};(D/'changes.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':run()
