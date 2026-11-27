"""Stage a source-bound lever add-on; never overwrite a released archive."""
import csv,hashlib,json,shutil,zipfile
from pathlib import Path
from hardware.cad.two_board_print_01.build_package import clean_exact
import hardware.cad.two_board_print_01.verify_delivery as qa
from hardware.cad.two_board_print_03.run import PARTS
R=Path(__file__).resolve().parent;REPO=R.parents[2];OUT=R/'retention-package';qa.ROOT=R
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stage():
 assert not OUT.exists()
 for f in ['verification.json','negative-stop-review.json']:
  v=json.loads((R/f).read_text())
  for p,h in v['source_sha256'].items():assert sha(REPO/p)==h,p
  assert all(not c['runtime_failure'] for c in v['cases'])
 OUT.mkdir();(OUT/'print').mkdir();records=[]
 for part in PARTS+['lever_arm_r6']:
  src=R/'generated-r2'/part/(part+'.stl') if part!='lever_arm_r6' else R.parent/'two_board_print_01/print-package-r6/print/shared/lever_arm.stl'
  dst=OUT/'print'/(part+'.stl');removed=clean_exact(src,dst)
  m=qa.inspect(dst);records.append(dict(name=part,source=str(src.relative_to(REPO)),source_sha256=sha(src),delivered_sha256=sha(dst),removed_exact_zero_area_facets=removed,inspection=m))
 bindings=json.loads((R/'verification.json').read_text())['source_sha256']
 for name in list(bindings)+[str((R/'stop_check.scad').relative_to(REPO))]:
  src=REPO/name;dst=OUT/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 for folder in ['generated-r2','generated-stop']:
  for src in (R/folder).rglob('*'):
   if src.is_file() and src.suffix!='.stl':
    dst=OUT/'evidence'/src.relative_to(R);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 review=dict(scope='Direct exact delivery mesh checks; no hole filling',mesh_count=len(records),meshes=[r['inspection'] for r in records]);(R/'delivery-review.json').write_text(json.dumps(review,indent=2)+'\n')
 (R/'delivery-manifest.json').write_text(json.dumps(dict(revision='TBH03-r2',units='mm',parts=records),indent=2)+'\n')
 with (R/'parts.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['file','quantity','selection','bounds_mm'])
  for r in records:
   n=r['name'];selection='optional alternative' if '_shim_' in n and not n.endswith('_9') else 'reuse or print' if n=='lever_arm_r6' else 'print first' if n=='pivot_coupon' else 'required'
   w.writerow(['print/'+n+'.stl',1,selection,r['inspection']['extents_mm']])
 for f in ['README.md','parts.csv','verification.json','negative-stop-review.json','tolerance-review.json','delivery-review.json','delivery-manifest.json','run.py','run_stop.py','tolerance.py','package.py']:shutil.copy2(R/f,OUT/f)
 print(json.dumps(dict(stage=str(OUT),mesh_count=len(records),removed_zero_area_facets=sum(r['removed_exact_zero_area_facets'] for r in records))))
def finalize():
 assert (R/'independent-review.json').exists()
 for f in ['README.md','independent-review.json']:shutil.copy2(R/f,OUT/f)
 manifest={str(p.relative_to(OUT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 dest=R/'TBH03-lever-retention-r2.zip';assert not dest.exists()
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file():z.write(p,Path('TBH03-lever-retention-r2')/p.relative_to(OUT))
 with zipfile.ZipFile(dest) as z:assert z.testzip() is None
 print(json.dumps(dict(zip=str(dest),sha256=sha(dest),bytes=dest.stat().st_size,files=len(manifest)+1)))
if __name__=='__main__':
 import sys
 stage() if sys.argv[1]=='stage' else finalize()
