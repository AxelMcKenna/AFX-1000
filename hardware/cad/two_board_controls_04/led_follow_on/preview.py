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
items=[]
for j,name in enumerate(['meter_frame','meter_frame_lower']):
 m=trimesh.load_mesh(R/'meters-r4'/name/(name+'.stl'));m.apply_translation([40.9,21.25+14*j-(9.3 if j==0 else 3.5),40.9]);items.append((m,(120,155,178)))
 for i in range(20):items.append((box([.9,1.7,.85],[43.9+3*i,21.25+j*14,41.325]),(80,185,115)))
for b in json.loads((R/'meter-contract.json').read_text())['boards']:
 m=extrude(Polygon(b['outline']),1.6);m.apply_translation([0,0,39.3]);items.append((m,(45,104,87)))
render(items,(40,135,820,560))
m=trimesh.load_mesh(R/'banks-r4/bank_frame/bank_frame.stl');m.apply_translation([-8.8,-8.8,41.2]);b=json.loads((R/'bank-contract.json').read_text());pcb=extrude(Polygon(b['outline']),1.6);pcb.apply_translation([0,0,39.6]);render([(m,(120,155,178)),(pcb,(45,104,87)),(box([.9,1.7,.85],[0,0,41.625]),(80,185,115))],(1000,190,440,450))
d=ImageDraw.Draw(img)
d.text((40,25),'TBH04 follow-on | Meter and bank emitter carriers',font=f,fill='#17232c')
d.text((40,65),'Exact exported frame meshes and PCB outlines; emitter maximum envelopes.',font=sm,fill='#46525c')
d.text((40,730),'Two20-channel boards; opaque cells align each emitter to its retained lens.',font=sm,fill='#17232c')
d.text((950,730),'Bank board: four installed copies.',font=sm,fill='#17232c')
d.text((40,795),'Lid, lenses, hardware and wires omitted for visibility. Modeled fit only; optical acceptance pending.',font=sm,fill='#46525c')
img.save(R/'preview.png')
