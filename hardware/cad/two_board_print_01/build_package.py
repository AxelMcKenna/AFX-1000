"""Validate selected native exports and assemble the clean r6 print handoff."""
import argparse,csv,hashlib,json,math,shutil,struct,zipfile
from pathlib import Path
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2]
OUT=ROOT/'print-package-r6'
CORE={
 'single-piece':{'shell':1,'lid':1,'rear_plate':1,'guide':1},
 'split':{'shell_left':1,'shell_right':1,'lid_left':1,'lid_right':1,'guide_left':1,'guide_right':1,'rear_left':1,'rear_right':1,'floor_join_plate':3,'lid_join_bar':2,'rear_join_bar':1},
 'shared':{'touch_backer':1,'lever_bracket':1,'lever_arm':1},
 'fit-coupons':{'coupon':1,'rear_coupon':1,'lid_nut_coupon':1}}
EMPTY='pcb_shell_collision component_shell_collision component_lid_collision component_guide_collision component_holder_collision component_join_collision split_overlap_collision lid_shell_collision rear_shell_collision component_head_collision component_split_collision split_pcb_collision floor_join_post_collision control_join_collision component_rear_collision component_rear_bar_collision lid_nut_collision lid_nut_insertion_collision lever_component_collision lever_lid_collision lever_shell_collision lever_guide_collision lever_holder_collision'.split()
POSITIVE=['pcb_positive','shell_positive','lid_nut_retention_positive']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_result(revision,name):
 p=ROOT/'generated'/revision/name/'result.json';r=json.loads(p.read_text())
 assert not r['runtime_failure']
 for f,h in r['source_sha256'].items():assert sha(REPO/f)==h,f
 return p,r
def clean_exact(src,dst):
 data=src.read_bytes();n=struct.unpack_from('<I',data,80)[0];keep=[]
 for i in range(n):
  raw=data[84+50*i:84+50*(i+1)];row=struct.unpack('<12fH',raw);a,b,c=[row[j:j+3] for j in (3,6,9)]
  cross=[(b[(k+1)%3]-a[(k+1)%3])*(c[(k+2)%3]-a[(k+2)%3])-(b[(k+2)%3]-a[(k+2)%3])*(c[(k+1)%3]-a[(k+1)%3]) for k in range(3)]
  if sum(v*v for v in cross)>=1e-24:keep.append(raw)
 dst.write_bytes(data[:80]+struct.pack('<I',len(keep))+b''.join(keep));return n-len(keep)
def connected_faces(path):
 data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0];parent=list(range(n));edges={};terms=[]
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i in range(n):
  row=struct.unpack_from('<12fH',data,84+50*i);a,b,c=[tuple(row[j:j+3]) for j in (3,6,9)]
  terms.append(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))
  for u,v in [(a,b),(b,c),(c,a)]:
   key=tuple(sorted((u,v)))
   if key in edges:parent[find(i)]=find(edges[key])
   else:edges[key]=i
 return len({find(i) for i in range(n)}),math.fsum(terms)/6
def stage():
 assert not OUT.exists(),'Fresh package only; do not overwrite reviewed artifacts'
 cap=json.loads((ROOT/'capture.json').read_text())
 for f,h in cap['source_sha256'].items():assert sha(REPO/f)==h,f
 native=[]
 for name in EMPTY+POSITIVE:
  p,r=read_result('r6',name)
  if name in EMPTY:assert r['empty'] and r['returncode']==1 and r['statistics'] is None,name
  else:
   assert r['returncode']==0 and r['statistics']['closed_oriented_boundary'],name
   if name!='lid_nut_retention_positive':assert abs(r['statistics']['volume_mm3']-.008)<1e-6
   else:assert r['statistics']['volume_mm3']>1
  native.append(dict(name=name,role='empty' if name in EMPTY else 'positive',result_sha256=sha(p)))
 rows=[dict(name=name,category=cat,quantity=q,material='opaque prototype') for cat,parts in CORE.items() for name,q in parts.items()]
 rows += [dict(r,category='fit-coupons' if r['name']=='shaft_coupon' else 'controls') for r in json.loads((ROOT/'accessory-inventory.json').read_text())]
 assert len(rows)==67
 OUT.mkdir();records=[]
 for r in rows:
  name=r['name'];revision='r6-cgal' if name.startswith('holder_') else 'r6';rp,result=read_result(revision,name)
  src=rp.with_name(name+'.stl');assert result['statistics']==mesh(src)
  assert result['returncode']==0 and result['statistics']['closed_oriented_boundary'],name
  dst=OUT/'print'/r['category']/(name+'.stl');dst.parent.mkdir(parents=True,exist_ok=True)
  removed=clean_exact(src,dst);m=mesh(dst);components,signed=connected_faces(dst)
  assert m['closed_oriented_boundary'] and m['degenerate_triangles_excluded']==0 and components==1 and signed>0 and m['min_mm'][2]>=-1e-5,name
  r['file']=str(dst.relative_to(OUT));r['print_bounds_mm']=[round(m['max_mm'][i]-m['min_mm'][i],5) for i in range(3)]
  records.append(dict(name=name,file=r['file'],quantity=r['quantity'],native_file=str(src.relative_to(ROOT)),native_sha256=sha(src),native_result_sha256=sha(rp),backend=result.get('backend','Manifold'),delivered_sha256=sha(dst),removed_zero_area_facets=removed,connected_components=components,signed_volume_mm3=signed,statistics=m))
  evidence=OUT/'evidence'/'native'/name;evidence.mkdir(parents=True)
  shutil.copy2(rp,evidence/'result.json');shutil.copy2(rp.with_name('native.log'),evidence/'native.log')
 for name in EMPTY+POSITIVE:
  src=ROOT/'generated/r6'/name;dst=OUT/'evidence/native'/name;dst.mkdir(parents=True)
  for f in ['result.json','native.log']:shutil.copy2(src/f,dst/f)
 verification=dict(revision='r6',units='millimetres',geometry_source_sha256=json.loads((ROOT/'generated/r6/shell/result.json').read_text())['source_sha256'],capture_sha256=sha(ROOT/'capture.json'),printable_designs=len(records),native_empty_cases=len(EMPTY),positive_controls=len(POSITIVE),prints=records,native_checks=native,excluded_native_exports=[f'generated/r6/holder_{i}/holder_{i}.stl' for i in range(1,6)],limits=['Unpowered fit prototype','Printer/material and physical strength unqualified','Selector/display/LED/angle-sensor carriers unresolved','No electrical or thermal release'])
 (ROOT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
 for base in [ROOT,OUT]:
  with (base/'parts.csv').open('w') as f:
   writer=csv.writer(f);writer.writerow(['file','quantity','category','material','bounds_mm'])
   for r in rows:writer.writerow([r['file'],r['quantity'],r['category'],r['material'],' x '.join(map(str,r['print_bounds_mm']))])
 for f in ['README.md','preview-r6.png','verification.json','accessory-inventory.json']:shutil.copy2(ROOT/f,OUT/f)
 for f in ['capture.json','cross-board-envelope-review-02.json','native-source-review-r6.json']:
  if (ROOT/f).exists():shutil.copy2(ROOT/f,OUT/'evidence'/f)
 sources=list(ROOT.glob('*.scad'))+[REPO/'hardware/cad/a11/controls.scad',REPO/'hardware/cad/a11/mechanisms.scad',REPO/'hardware/cad/a11/generated/button-fixture.scad']
 for src in sources:
  dst=OUT/'source'/src.relative_to(REPO);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 print(json.dumps(dict(stage=str(OUT),designs=len(records),removed_facets=sum(r['removed_zero_area_facets'] for r in records),native_empty_cases=len(EMPTY))))
def finalize():
 assert OUT.is_dir()
 review=ROOT/'independent-review-r6.json';assert review.exists(),'Independent delivery review must finish first'
 for f in ['README.md','verification.json','parts.csv','independent-review-r6.json','cross-board-envelope-review-02.json']:
  shutil.copy2(ROOT/f,OUT/f)
 manifest=dict(revision='r6',units='millimetres',files={str(p.relative_to(OUT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 target=ROOT/'TBH01-r6-print-package.zip';assert not target.exists()
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file():z.write(p,Path('TBH01-r6')/p.relative_to(OUT))
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 print(json.dumps(dict(zip=str(target),bytes=target.stat().st_size,sha256=sha(target),files=len(manifest['files'])+1)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','finalize']);a=p.parse_args();stage() if a.action=='stage' else finalize()
