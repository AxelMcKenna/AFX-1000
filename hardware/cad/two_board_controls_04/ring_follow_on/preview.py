"""Render exact reviewed STL facets with bounded component reference solids."""
from pathlib import Path
import numpy as np,trimesh
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
img=Image.new('RGB',(1500,850),'#f4f6f8');d=ImageDraw.Draw(img)
f=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',23);sm=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',17)
cam=np.array([.65,-.7,.5]);cam/=np.linalg.norm(cam);right=np.cross([0,0,1],cam);right/=np.linalg.norm(right);up=np.cross(cam,right);basis=np.array([right,up,cam]).T

def render(items,vp):
 pts=np.concatenate([np.asarray(m.vertices)@basis for m,c in items]);lo,hi=pts.min(0),pts.max(0);scale=min(vp[2]/(hi[0]-lo[0]),vp[3]/(hi[1]-lo[1]));faces=[]
 for m,col in items:
  pts=np.asarray(m.vertices)@basis;pts[:,0]=vp[0]+(pts[:,0]-lo[0])*scale;pts[:,1]=vp[1]+(hi[1]-pts[:,1])*scale
  shade=.5+.5*np.maximum(0,m.face_normals@np.array([.5,-.2,.84]))
  for i,face in enumerate(m.faces):
   if m.face_normals[i]@cam>0:faces.append((pts[face,2].mean(),pts[face,:2],tuple(int(c*shade[i])for c in col)))
 pixels=np.array(img);depth=np.full((img.height,img.width),-np.inf)
 for m,col in items:
  pts=np.asarray(m.vertices)@basis;pts[:,0]=vp[0]+(pts[:,0]-lo[0])*scale;pts[:,1]=vp[1]+(hi[1]-pts[:,1])*scale
  shade=.5+.5*np.maximum(0,m.face_normals@np.array([.5,-.2,.84]))
  for i,face in enumerate(m.faces):
   if m.face_normals[i]@cam<=0:continue
   a,b,c=pts[face];den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
   if abs(den)<1e-10:continue
   xmin=max(0,int(np.floor(min(a[0],b[0],c[0]))));xmax=min(img.width-1,int(np.ceil(max(a[0],b[0],c[0]))));ymin=max(0,int(np.floor(min(a[1],b[1],c[1]))));ymax=min(img.height-1,int(np.ceil(max(a[1],b[1],c[1]))))
   yy,xx=np.mgrid[ymin:ymax+1,xmin:xmax+1];xx=xx+.5;yy=yy+.5
   u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w=1-u-v;z=u*a[2]+v*b[2]+w*c[2]
   dep=depth[ymin:ymax+1,xmin:xmax+1];mask=(u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8)&(z>dep);dep[mask]=z[mask];pixels[ymin:ymax+1,xmin:xmax+1][mask]=[int(cc*shade[i])for cc in col]
 img.paste(Image.fromarray(pixels))
def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m

import json
from shapely.geometry import Polygon
from shapely.ops import triangulate
def extrude(poly,height):
 ts=[t for t in triangulate(poly) if poly.covers(t.representative_point())];v=np.array([list(t.exterior.coords)[:3] for t in ts]).reshape((-1,2));return trimesh.creation.extrude_triangulation(v,np.arange(len(v)).reshape((-1,3)),height)

import json
from shapely.geometry import Point
frame=trimesh.load_mesh(R/'native-r6/ring_frame/ring_frame.stl');frame.apply_translation([-31.3,-31.3,40.9])
lens=trimesh.load_mesh(R/'native-r6/ring_lens/ring_lens.stl');lens.apply_translation([-31.3,-31.3,50])
outline=json.loads((R/'board-data.scad').read_text().split('=',1)[1].split(';',1)[0]);poly=Polygon(outline).difference(Point(0,0).buffer(17.8,quad_segs=48));board=extrude(poly,1.6);board.apply_translation([0,0,39.3]);items=[(frame,(120,155,178)),(board,(45,104,87)),(lens,(204,180,115))]
for p in json.loads((R/'contract.json').read_text())['parts']:
 size=[2,2,.9] if p['kind']=='led' else [.9,1.7,.55];m=box(size,[0,0,size[2]/2]);m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(p['angle']),[0,0,1]));m.apply_translation([p['center'][0]-244,p['center'][1]-78,40.9]);items.append((m,(110,210,155) if p['kind']=='led' else (65,65,70)))
render(items,(180,130,1140,580));d=ImageDraw.Draw(img)
d.text((40,25),'RGB ring | Eight emitters and a screw-retained lens',font=f,fill='#17232c')
d.text((40,65),'Reviewed print meshes; lens lifted 8 mm. Three sink channels, 24 balancing resistors.',font=sm,fill='#46525c')
d.text((40,760),'Three shared M2 mounts retain the lens, frame and populated PCB. Housing and wires omitted for visibility.',font=sm,fill='#17232c')
d.text((40,800),'Modeled fit only. Optical brightness, color balance and physical receiving remain acceptance gates.',font=sm,fill='#46525c')
img.save(R/'preview.png')
