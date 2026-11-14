"""Build source-closed carrier review delivery from verified meshes only."""
import json,hashlib,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[2];OUT=R/'delivery'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 records=[json.loads((R/n).read_text()) for n in ['verification.json','selector-verification.json']]
 for rec in records:
  for p,h in rec['source_sha256'].items():assert sha(REPO/p)==h,p
 OUT.mkdir(exist_ok=False);(OUT/'print').mkdir();sources=set()
 def capture(p):
  p=p.resolve()
  if p in sources:return
  sources.add(p)
  for rel in re.findall(r'(?:include|use)\s*<([^>]+)>',p.read_text()):capture(p.parent/rel)
 for p in [R/'display.scad',R/'selectors.scad']:capture(p)
 for p in sources:
  dest=OUT/'source'/p.relative_to(REPO);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 for group,names in [('generated-r7',['tray','bezel']),('selectors-r6',['settings_bracket','selector_lid','selector_guide','selector_lid_left','selector_lid_right','selector_guide_left','selector_guide_right'])]:
  for n in names:
   result=json.loads((R/group/n/'result.json').read_text());assert not result['runtime_failure'] and result['statistics']['closed_oriented_boundary'];shutil.copyfile(R/group/n/(n+'.stl'),OUT/'print'/(n+'.stl'))
 for n in ['README.md','preview.png','display-wiring.csv','display-wiring-review.json','selector-contract.json','settings.kicad_pcb','release.kicad_pcb','settings.kicad_pro','release.kicad_pro','fp-lib-table','verification.json','selector-verification.json']:
  shutil.copyfile(R/n,OUT/n)
 shutil.copytree(R/'TBH04.pretty',OUT/'TBH04.pretty');shutil.copytree(R/'pcb-native-r2',OUT/'pcb-review')
 manifest={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()}
 (OUT/'manifest.json').write_text(json.dumps(dict(scope='Unpowered fit checkpoint; full LED, harness, thermal and manufacturing gates remain',files=manifest),indent=2)+'\n')
 target=R/'TBH04-display-selectors-review.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(OUT))
 (R/'delivery-review.json').write_text(json.dumps(dict(files=len(manifest),archive_sha256=sha(target),source_bindings_checked=sum(len(r['source_sha256'])for r in records),source_include_closure=len(sources),fabrication_released=False),indent=2)+'\n')
 print(target)
if __name__=='__main__':main()
