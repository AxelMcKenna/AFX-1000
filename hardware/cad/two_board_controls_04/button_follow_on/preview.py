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

c=json.loads((R/'contract.json').read_text());boards={b['name']:b for b in c['boards']}
for idx,(name,key) in enumerate([('vertical','isolate_0'),('horizontal','auto'),('scene','scene_0')]):
 b=boards[name];poly=Polygon(b['outline'],b['cutouts'])
 for p in b['mounts']:poly=poly.difference(Point(*p).buffer(1.2,quad_segs=24))
 board=extrude(poly,.6);board.apply_translation([0,0,42.9]);keymesh=trimesh.load_mesh(R.parent.parent/'two_board_print_01/generated/r6'/('button_'+key)/('button_'+key+'.stl'));keymesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]));keymesh.apply_translation([0,0,57.2])
 items=[(board,(45,104,87)),(keymesh,(204,180,115)),(box([.9,1.7,.85],[4.8,0,43.925]),(110,210,155))]
 for p in b['mounts']:
  m=trimesh.creation.annulus(r_min=1.2,r_max=2.1,height=.1,sections=48);m.apply_translation([p[0],p[1],43.55]);items.append((m,(195,210,220)))
 render(items,(30+idx*495,140,450,530))
d=ImageDraw.Draw(img)
d.text((40,25),'Button indicators | Existing keys, new populated receivers',font=f,fill='#17232c')
d.text((40,65),'Three of six board variants shown. Existing key meshes lifted 8 mm; use translucent cap material.',font=sm,fill='#46525c')
for idx,label in enumerate(['Vertical holder pattern','Horizontal holder pattern','Scene-sector pattern']):d.text((40+idx*495,730),label,font=sm,fill='#17232c')
d.text((40,790),'Guide pockets retain 0.6 mm boards using existing holder screws and 0.1 mm insulating shims. Optical tests pending.',font=sm,fill='#46525c')
img.save(R/'preview.png')
