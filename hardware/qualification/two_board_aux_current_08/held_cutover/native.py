"""Run inside pinned Linux KiCad only; input trees read-only, outputs isolated."""
import hashlib,json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]);logs=[]
for tag,root in [('baseline',Path('/baseline')),('candidate',Path(sys.argv[2]))]:
 inputs={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.suffix in ['.kicad_sch','.kicad_sym','.kicad_pro']}
 (out/(tag+'-input-hashes.json')).write_text(json.dumps(inputs,indent=2)+'\n')
 for kind,args in [('netlist',['sch','export','netlist','--format','kicadxml','--output',str(out/(tag+'-netlist.xml'))]),('erc',['sch','erc','--format','json','--output',str(out/(tag+'-erc.json'))])]:
  cmd=['kicad-cli',*args,str(root/'power_protection.kicad_sch')];r=subprocess.run(cmd,capture_output=True,text=True,timeout=90);logs.append(dict(tag=tag,kind=kind,command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));print(tag,kind,r.returncode,r.stdout,r.stderr,flush=True)
(out/'commands.json').write_text(json.dumps(logs,indent=2)+'\n')
assert all(x['returncode']==0 for x in logs)
