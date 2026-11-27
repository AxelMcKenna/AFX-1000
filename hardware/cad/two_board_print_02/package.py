"""Create the minimal print-first kit without changing sealed r6 artifacts."""
import csv,hashlib,json,shutil,struct,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from hardware.cad.two_board_print_01 import verify_delivery
from hardware.cad.two_board_print_02.run import PARTS,EMPTY,POSITIVE
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2];BASE=ROOT.parent/'two_board_print_01';OUT=ROOT/'print-first-kit'
GROUPS={
 '00-core-fit-tests':{'corner_shell_coupon':1,'corner_lid_coupon':1,'coupon':1,'rear_coupon':1},
 '01-tray-single':{'shell':1},'01-tray-split':{'shell_left':1,'shell_right':1,'floor_join_plate':3},
 '02-close-single':{'lid':1,'rear_plate':1},'02-close-split':{'lid_left':1,'lid_right':1,'rear_left':1,'rear_right':1,'lid_join_bar':2,'rear_join_bar':1},
 '03-optional-control-tests':{'button_panel_coupon':1,'button_guide_coupon':1,'pot_panel_coupon':1,'shaft_coupon':1,'button_quantize':1,'holder_1':1,'retaining_clip':3,'knob_16x13':1}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def triangles(path):
 raw=path.read_bytes();n=struct.unpack_from('<I',raw,80)[0]
 return [[tuple(struct.unpack_from('<12fH',raw,84+50*i)[j:j+3]) for j in [3,6,9]] for i in range(n)]
def make_3mf(files):
 ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',ns)
 def add(p,n,a=None):return ET.SubElement(p,'{'+ns+'}'+n,a or {})
 model=ET.Element('{'+ns+'}model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
 add(model,'metadata',{'name':'Title'}).text='TBH01 r6 core fit tests; geometry only, no printer profile'
 resources=add(model,'resources');build=add(model,'build');placements={ 'rear_coupon':[0,0], 'coupon':[0,30], 'corner_shell_coupon':[65,30], 'corner_lid_coupon':[90,30]};checks=[]
 for oid,(name,xy) in enumerate(placements.items(),1):
  tris=triangles(files[name]);verts=[];ids={};faces=[]
  for tri in tris:
   face=[]
   for v in tri:
    if v not in ids:ids[v]=len(verts);verts.append(v)
    face.append(ids[v])
   faces.append(face)
  low=[min(v[i] for v in verts) for i in range(3)];high=[max(v[i] for v in verts) for i in range(3)]
  obj=add(resources,'object',{'id':str(oid),'type':'model','name':name});m=add(obj,'mesh');vs=add(m,'vertices');ts=add(m,'triangles')
  for v in verts:add(vs,'vertex',{k:format(n,'.17g') for k,n in zip(['x','y','z'],v)})
  for f in faces:add(ts,'triangle',{k:str(n) for k,n in zip(['v1','v2','v3'],f)})
  trans=[xy[0]-low[0],xy[1]-low[1],-low[2]]
  add(build,'item',{'objectid':str(oid),'transform':'1 0 0 0 1 0 0 0 1 '+' '.join(format(n,'.17g') for n in trans)})
  checks.append(dict(name=name,source_stl_sha256=sha(files[name]),triangles=len(tris),minimum_mm=[*xy,0],maximum_mm=[xy[0]+high[0]-low[0],xy[1]+high[1]-low[1],high[2]-low[2]],translation_mm=trans))
 target=OUT/'00-core-fit-tests.3mf'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
  z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
  z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None;parsed=ET.fromstring(z.read('3D/3dmodel.model'));assert parsed.attrib['unit']=='millimeter'
  for obj in parsed.findall('.//{'+ns+'}object'):
   name=obj.attrib['name'];vv=[tuple(float(v.attrib[k]) for k in ['x','y','z']) for v in obj.findall('.//{'+ns+'}vertex')]
   tt=[[vv[int(f.attrib[k])] for k in ['v1','v2','v3']] for f in obj.findall('.//{'+ns+'}triangle')]
   assert tt==triangles(files[name]),name
 assert len(checks)==4
 for i,a in enumerate(checks):
  for b in checks[i+1:]:assert any(a['maximum_mm'][j]<=b['minimum_mm'][j] or b['maximum_mm'][j]<=a['minimum_mm'][j] for j in [0,1])
 return dict(file=target.name,sha256=sha(target),units='millimetres',geometry_round_trip_exact=True,objects=checks,footprint_mm=[110,54],contains_printer_profile=False)
def main():
 assert not OUT.exists(),'Fresh package only'
 assert sha(BASE/'TBH01-r6-print-package.zip')=='7f3c53a54b73f08c3b2342c9bcb806b327a6ca1779ff3d3dea3c82932126791d'
 native=json.loads((ROOT/'verification.json').read_text())
 for f,h in native['source_sha256'].items():assert sha(REPO/f)==h,f
 for r in native['cases']:
  if r['part'] in EMPTY:assert r['empty'] and r['statistics'] is None
  else:assert r['statistics']['closed_oriented_boundary'] and r['statistics']['degenerate_triangles_excluded']==0
 OUT.mkdir();verify_delivery.ROOT=ROOT;rows=[];records=[];files={}
 for group,items in GROUPS.items():
  for name,quantity in items.items():
   if name in PARTS:src=ROOT/'generated-r3'/name/(name+'.stl')
   else:
    matches=list((BASE/'print-package-r6/print').rglob(name+'.stl'));assert len(matches)==1;src=matches[0]
   dst=OUT/'print'/group/(name+'.stl');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   assert sha(src)==sha(dst);m=verify_delivery.inspect(dst);records.append(dict(m,source=str(src.relative_to(REPO)),quantity=quantity));files[name]=dst
   rows.append(dict(file=str(dst.relative_to(OUT)),quantity=quantity,stage=group,bounds_mm=' × '.join(f'{n:.3f}' for n in m['extents_mm'])))
 assert len(records)==24
 with (OUT/'parts.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 report=dict(scope='Direct exact-facet delivery checks; no repairs; native checks separate',mesh_count=len(records),meshes=records,core_3mf=make_3mf(files))
 (ROOT/'delivery-review.json').write_text(json.dumps(report,indent=2)+'\n')
 for n in ['README.md','verification.json','delivery-review.json','latest-physical-compatibility.json']:shutil.copy2(ROOT/n,OUT/n)
 ref=OUT/'reference';ref.mkdir();shutil.copy2(BASE/'README.md',ref/'r6-assembly.md');shutil.copy2(BASE/'preview-r6.png',ref/'preview-r6.png');shutil.copy2(BASE/'independent-review-r6.json',ref/'independent-review-r6.json')
 for src in [ROOT/'coupons.scad',*[REPO/p for p in native['source_sha256'] if p.endswith('.scad')]]:
  dst=OUT/'source'/src.relative_to(REPO);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 for src in (ROOT/'generated-r3').rglob('*'):
  if src.name in ['result.json','native.log']:
   dst=OUT/'evidence'/src.relative_to(ROOT/'generated-r3');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 manifest=dict(scope='Print-first kit; unchanged r6 case geometry',files={str(p.relative_to(OUT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file()})
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 target=ROOT/'TBH01-r6-print-first-kit.zip';assert not target.exists()
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file():z.write(p,Path('TBH01-r6-print-first')/p.relative_to(OUT))
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 print(json.dumps(dict(zip=str(target),sha256=sha(target),bytes=target.stat().st_size,stl_count=len(records),new_native_empty_cases=len(EMPTY))))
if __name__=='__main__':main()
