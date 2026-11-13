"""Conservative host-side copper audit of native CAD seat and edge receiving band."""
import argparse,json,math,hashlib,struct,re
from pathlib import Path
from collections import Counter
from shapely.geometry import Point,Polygon,LineString,box,mapping
from shapely.ops import unary_union,polygonize
import numpy as np
from hardware.fabrication import assembly_layout as al
from hardware.cad.a12.thermal.enlarged_base.verify import mesh
from hardware.electronics.common import sexpr as sx
H=Path(__file__).resolve().parent;R=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def circle(x,y,r):return Point(x,y).buffer(r/math.cos(math.pi/128),resolution=32)
def filled_shape(points):
 poly=Polygon(points)
 if poly.is_valid:return poly,False
 # KiCad serializes hole bridges as repeated edges. Split the planar walk
 # into faces and retain only cells whose original winding is nonzero.
 # Require simple 0/+1/-1 winding, so odd/even and nonzero rules agree.
 closed=points+[points[0]];aa=np.array(closed[:-1]);bb=np.array(closed[1:]);cells=list(polygonize(unary_union(LineString(closed))));keep=[]
 assert cells,'Cannot reconstruct filled-zone walk'
 for cell in cells:
  rp=cell.representative_point();x,y=rp.x,rp.y;cross=(bb[:,0]-aa[:,0])*(y-aa[:,1])-(x-aa[:,0])*(bb[:,1]-aa[:,1])
  winding=int(np.sum((aa[:,1]<=y)&(bb[:,1]>y)&(cross>0))-np.sum((aa[:,1]>y)&(bb[:,1]<=y)&(cross<0)))
  assert abs(winding)<=1,'Ambiguous multiply-wound copper'
  if winding:keep.append(cell)
 result=unary_union(keep);assert result.is_valid
 return result,True
def audit(pcb,inflate=0):
 tree,outline=al.outline(pcb)
 capture=(R/'hardware/cad/two_board_print_01/captured.scad').read_text();profiles=json.loads(re.search(r'^board_profiles = (.*);',capture,re.M).group(1));assert outline.equals(Polygon(profiles[1][0]))
 mount_found=False
 rec=json.loads((H/'native/positive-seat1/result.json').read_text())
 for n,h in rec['source_sha256'].items():assert sha(R/n)==h,n
 raw=H/'native/positive-seat1/positive.stl';assert rec['mesh']['closed_oriented_boundary'] and mesh(raw)==rec['mesh'];data=raw.read_bytes();polys=[]
 for i in range(struct.unpack_from('<I',data,80)[0]):
  v=struct.unpack_from('<12fH',data,84+50*i);pts=[v[j:j+3] for j in [3,6,9]];assert all(abs(z)<1e-8 or abs(z-.1)<1e-6 for x,y,z in pts)
  poly=Polygon([(x,y) for x,y,z in pts])
  if poly.area:assert poly.is_valid;polys.append(poly)
 seat=unary_union(polys).intersection(outline);assert seat.area>40
 # Additional0.2 mm receiving placement/shape uncertainty. This does not
 # authorize its pressure or prove a printing process attains the limit.
 seat=seat.buffer((.2+inflate)/math.cos(math.pi/128),resolution=32)
 edge=box(160.8,108.3,167.2,108.9).intersection(outline)
 regions={'top_seat':(seat,{'F.Cu'}),'edge_key':(edge,{'F.Cu','B.Cu'})}
 minima={k:(1e9,None) for k in regions};hits=[];counts=Counter();unknown=[]
 def check(shape,layers,label):
  assert shape.is_valid,label;counts[label.split(':')[0]]+=1
  for role,(area,selected) in regions.items():
   if not selected.intersection(layers):continue
   d=area.distance(shape)
   if d<minima[role][0]:minima[role]=(d,label)
   if area.intersects(shape):hits.append({'region':role,'item':label,'area_mm2':area.intersection(shape).area})
 for i,s in enumerate(sx.children(tree,'segment')):
  lay=str(sx.first(s,'layer')[1]);pts=[tuple(map(float,sx.first(s,k)[1:3])) for k in ['start','end']];w=float(sx.first(s,'width')[1]);check(LineString(pts).buffer(w/2/math.cos(math.pi/128),resolution=32),{lay},'track:'+str(i))
 assert not sx.children(tree,'arc'),'Unimplemented copper arc audit'
 for i,v in enumerate(sx.children(tree,'via')):
  x,y=map(float,sx.first(v,'at')[1:3]);r=float(sx.first(v,'size')[1])/2;check(circle(x,y,r),{'F.Cu','B.Cu'},'via:'+str(i))
 for f in sx.children(tree,'footprint'):
  props={str(q[1]):str(q[2]) for q in sx.children(f,'property')};ref=props['Reference'];a=sx.first(f,'at');fx,fy=map(float,a[1:3]);ang=math.radians(float(a[3]) if len(a)>3 else 0)
  if ref=='H_NEW5':
   assert (fx,fy)==(164,113);mount_found=True
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
 assert mount_found
 return {'keepout_features':[{'type':'Feature','properties':{'id':k,'layers':sorted(v[1]),'coordinate_system':'native_power_pcb_mm','purpose':'Preserve conditional cradle contact; no force/insulation qualification'},'geometry':mapping(v[0])} for k,v in regions.items()],'hits':hits,'minimum_conservative_gap_mm':{k:{'gap':v[0],'item':v[1]} for k,v in minima.items()},'objects':dict(counts),'seat_area_with_0_2mm_receiving_expansion_mm2':seat.area,'edge_key_receiving_band_xy_mm':[160.8,108.3,167.2,108.9],'native_seat_sha256':sha(raw)}
def main():
 hole=[(0,0),(4,0),(4,4),(0,4),(0,0),(1,1),(1,3),(3,3),(3,1),(1,1),(0,0)];assert abs(filled_shape(hole)[0].area-12)<1e-9
 try:filled_shape([(0,0),(4,0),(4,4),(0,4),(0,0),(4,0),(4,4),(0,4),(0,0)])
 except AssertionError:pass
 else:raise AssertionError('Multiply-wound mutation accepted')
 p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,required=True);a=p.parse_args();r=audit(a.pcb);assert not r['hits'],r['hits']
 bad=audit(a.pcb,inflate=3);assert bad['hits'],'Expanded seat mutation failed to intersect nearby copper'
 r.update(status='CONSERVATIVE_COPPER_CLEARANCE_ONLY',expanded_seat_mutation='rejected',source_pcb=str(a.pcb.name),source_pcb_sha256=sha(a.pcb),source_sha256={str(q.relative_to(R)):sha(q) for q in [Path(__file__),H/'support.scad',H/'native/positive-seat1/result.json',R/'hardware/cad/two_board_print_01/captured.scad',R/'hardware/fabrication/assembly_layout.py',R/'hardware/electronics/common/sexpr.py']},physical_pressure_insulation_qualified=False)
 keep={'type':'FeatureCollection','features':r['keepout_features'],'source_pcb_sha256':sha(a.pcb),'source_sha256':r['source_sha256'],'status':'FUTURE_CONDITIONAL_CONTACT_KEEP_OUT','physical_qualified':False};(H/'contact-keepouts.json').write_text(json.dumps(keep,indent=2)+'\n')
 (H/'copper-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['minimum_conservative_gap_mm']))
if __name__=='__main__':main()
