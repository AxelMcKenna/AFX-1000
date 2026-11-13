"""Conservative no-copper contact screen for sourced main PCB washers."""
import json,math,re,hashlib
from pathlib import Path
from collections import Counter
from shapely.geometry import LineString,Point,mapping
from hardware.fabrication import assembly_layout as al
from hardware.electronics.common import sexpr as sx
from hardware.cad.two_board_installation_06.r31_touch_cradle.copper_audit import circle,filled_shape
H=Path(__file__).resolve().parent
R=H.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(pcb,mounts,washer_outer=4.5,registration=.15):
 tree,outline=al.outline(pcb)
 footprint_map={str(next(q for q in sx.children(f,'property') if q[1]=='Reference')[2]):f for f in sx.children(tree,'footprint')}
 for m in mounts:
  at=sx.first(footprint_map[m[0]],'at');assert list(map(float,at[1:3]))==m[1:3],m[0]
 regions={m[0]:(circle(m[1],m[2],washer_outer/2+registration),{'F.Cu'}) for m in mounts}
 minima={k:(1e9,None) for k in regions};hits=[];counts=Counter()
 def check(shape,layers,label):
  assert shape.is_valid,label;counts[label.split(':')[0]]+=1
  for role,(area,selected) in regions.items():
   if not selected.intersection(layers):continue
   d=area.distance(shape)
   if d<minima[role][0]:minima[role]=(d,label)
   if area.intersects(shape):hits.append({'mount':role,'item':label,'conservative_overlap_mm2':area.intersection(shape).area})
 for i,s in enumerate(sx.children(tree,'segment')):
  lay=str(sx.first(s,'layer')[1]);pts=[tuple(map(float,sx.first(s,k)[1:3])) for k in ['start','end']];w=float(sx.first(s,'width')[1]);check(LineString(pts).buffer(w/2/math.cos(math.pi/128),resolution=32),{lay},'track:'+str(i))
 assert not sx.children(tree,'arc'),'Unimplemented copper arc audit'
 for i,v in enumerate(sx.children(tree,'via')):
  x,y=map(float,sx.first(v,'at')[1:3]);r=float(sx.first(v,'size')[1])/2;check(circle(x,y,r),{'F.Cu','B.Cu'},'via:'+str(i))
 for f in sx.children(tree,'footprint'):
  props={str(q[1]):str(q[2]) for q in sx.children(f,'property')};ref=props['Reference'];a=sx.first(f,'at');fx,fy=map(float,a[1:3]);ang=math.radians(float(a[3]) if len(a)>3 else 0)
  for pad in sx.children(f,'pad'):
   if pad[2]=='np_thru_hole':continue
   layers={str(x) for x in sx.first(pad,'layers')[1:]};layers={'F.Cu','B.Cu'} if '*.Cu' in layers else layers
   at=sx.first(pad,'at');x,y=map(float,at[1:3]);px=fx+x*math.cos(ang)+y*math.sin(ang);py=fy-x*math.sin(ang)+y*math.cos(ang)
   size=list(map(float,sx.first(pad,'size')[1:3]));rad=math.hypot(*size)/2
   assert pad[3] in ['rect','roundrect','circle','oval','custom'],pad[3]
   if pad[3]=='custom':
    for prim in sx.first(pad,'primitives')[1:]:
     w=float(sx.first(prim,'width')[1])
     if prim[0]=='gr_poly':rad=max(rad,max(math.hypot(float(v[1]),float(v[2])) for v in sx.children(sx.first(prim,'pts'),'xy'))+w/2)
     elif prim[0]=='gr_circle':
      ce=list(map(float,sx.first(prim,'center')[1:3]));en=list(map(float,sx.first(prim,'end')[1:3]));rad=max(rad,math.hypot(*ce)+math.dist(ce,en)+w/2)
     else:raise AssertionError('Unsupported custom primitive '+str(prim[0]))
   check(circle(px,py,rad),layers,'pad:'+ref+':'+str(pad[1]))
  for n in f[2:]:
   if isinstance(n,list) and str(n[0]).startswith('fp_'):
    lay=sx.first(n,'layer')
    if lay and lay[1] in ['F.Cu','B.Cu']:
     assert n[0]=='fp_rect','Unimplemented footprint copper graphic'
     a,b=[list(map(float,sx.first(n,k)[1:3])) for k in ['start','end']];stroke=sx.first(n,'stroke');w=float(sx.first(stroke,'width')[1]);rad=max(math.hypot(x,y) for x in [a[0],b[0]] for y in [a[1],b[1]])+w/2
     check(circle(fx,fy,rad),{str(lay[1])},'graphic:'+ref)
 for i,z in enumerate(sx.children(tree,'zone')):
  filled=sx.children(z,'filled_polygon');assert filled or sx.first(z,'keepout'),'Unfilled copper zone'
  for j,f in enumerate(filled):
   layer=str(sx.first(f,'layer')[1]);pts=sx.first(f,'pts');poly,repaired=filled_shape([(float(q[1]),float(q[2])) for q in sx.children(pts,'xy')]);counts['bridged_zone_walks_reconstructed']+=int(repaired);check(poly,{layer},'zone:'+str(i)+':'+str(j))
 for n in tree[1:]:
  if isinstance(n,list) and str(n[0]).startswith('gr_'):
   lay=sx.first(n,'layer');assert not lay or lay[1] not in ['F.Cu','B.Cu'],'Unimplemented board copper graphic'
 return {'source_pcb':str(pcb.relative_to(R)),'source_pcb_sha256':sha(pcb),'washer_outer_max_mm':washer_outer,'registration_max_mm':registration,'hits':hits,'minimum_conservative_gap_mm':{k:{'gap':v[0],'item':v[1]} for k,v in minima.items()},'objects':dict(counts)}
def run():
 selected=H/'previous-manifest.json'
 if not selected.exists():selected.write_bytes((R/'hardware/cad/assembly_workflow/current.json').read_bytes())
 data=json.loads(selected.read_text());captured=R/'hardware/cad/two_board_print_01/captured.scad'
 mounts=json.loads(re.search(r'^mounts = (.*);',captured.read_text(),re.M).group(1));mounts=[m for m in mounts if m[0] not in ['D_H2','D_H5']];assert len(mounts)==22
 refs={}
 for key in ['signal','power']:
  tree,_=al.outline(R/data['boards'][key]);refs[key]={str(next(q for q in sx.children(f,'property') if q[1]=='Reference')[2]) for f in sx.children(tree,'footprint')}
 assert all(sum(m[0] in refs[k] for k in refs)==1 for m in mounts),'Ambiguous board ownership'
 result={key:audit(R/data['boards'][key],[m for m in mounts if m[0] in refs[key]]) for key in refs}
 out={'status':'CONSERVATIVE_CONTACT_SCREEN','qualified':False,'sensor_owned_mounts_unchanged':True,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),selected,captured,R/'hardware/cad/two_board_installation_06/r31_touch_cradle/copper_audit.py',R/'hardware/fabrication/assembly_layout.py',R/'hardware/electronics/common/sexpr.py',H/'sources/HRDW-M2-A4-BL.pdf']},'boards':result}
 features=[]
 for key in refs:
  for m in mounts:
   if m[0] in refs[key]:features.append({'type':'Feature','properties':{'mount':m[0],'board':key,'layers':['F.Cu'],'center_mm':m[1:3],'minimum_radial_exclusion_mm':2.4,'washer_max_OD_mm':4.5,'washer_center_registration_max_mm':.15,'purpose':'No copper under conductive main-mount receiving bearing area; sensor-owned mounts excluded'},'geometry':mapping(circle(m[1],m[2],2.4))})
 keepout={'type':'FeatureCollection','features':features,'source_sha256':out['source_sha256'],'source_pcbs':{key:{'path':r['source_pcb'],'sha256':r['source_pcb_sha256']} for key,r in result.items()},'receiving_not_supplier_guarantee':['washer_center_registration_max_mm'],'selected_hardware_changed':False,'physical_qualified':False}
 (H/'contact-keepouts.json').write_text(json.dumps(keepout,indent=2)+'\n')
 details=[]
 for key,r in result.items():
  tree,_=al.outline(R/data['boards'][key])
  for hit in r['hits']:
   kind,index=hit['item'].split(':');assert kind in ['track','via'],'Refine unsupported conservative hit before asserting nominal conflict'
   node=sx.children(tree,{'track':'segment','via':'via'}[kind])[int(index)];m=next(m for m in mounts if m[0]==hit['mount'])
   if kind=='track':
    pts=[tuple(map(float,sx.first(node,k)[1:3])) for k in ['start','end']];edge=Point(m[1:3]).distance(LineString(pts))-float(sx.first(node,'width')[1])/2
   else:edge=math.dist(m[1:3],list(map(float,sx.first(node,'at')[1:3])))-float(sx.first(node,'size')[1])/2
   details.append({'board':key,'mount':m[0],'center_mm':m[1:3],'uuid':str(sx.first(node,'uuid')[1]),'net':str(sx.first(node,'net')[1]),'kind':kind,'radial_copper_edge_distance_mm':edge,'gap_to_nominal_4_5mm_washer_mm':edge-2.25,'gap_to_receiving_4_8mm_diameter_mm':edge-2.4,'native_object':node})
 out['exact_track_via_distance_checks']=details
 (H/'copper-screen.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({key:{'mounts':len(r['minimum_conservative_gap_mm']),'hits':r['hits']} for key,r in result.items()},indent=2))
if __name__=='__main__':run()
