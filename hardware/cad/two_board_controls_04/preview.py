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
tray=trimesh.load_mesh(R/'generated-r7/tray/tray.stl');tray.apply_translation([147.3,16,31.8])
bezel=trimesh.load_mesh(R/'generated-r7/bezel/bezel.stl');bezel.apply_translation([147.3,16,42.8+5])
items=[(tray,(120,155,178)),(bezel,(232,166,81))]+[(box([7.5,14,8.5],[x,31,38.05]),(86,173,139)) for x in [152,160,168]]
d.text((40,25),'TBH04 | BPM and selector carriers',font=f,fill='#17232c');d.text((40,65),'Modeled fit candidates; exact printed meshes. Purchased parts and PCB shown as reference solids.',font=sm,fill='#46525c')
render(items,(40,135,690,560));d.text((40,730),'BPM tray, three digits at 8 mm pitch; bezel lifted 5 mm for clarity.',font=sm,fill='#17232c')
br=trimesh.load_mesh(R/'selectors-r6/settings_bracket/settings_bracket.stl');br.apply_translation([-9.8,-12.3,39.7])
render([(br,(120,155,178)),(box([16,23,1.6],[0,0,38.9]),(86,173,139)),(box([13,3.6,3.5],[0,0,41.45]),(70,75,80))],(840,150,570,520));d.text((800,730),'Same bracket fits both explicit selector breakout boards.',font=sm,fill='#17232c');d.text((40,795),'Housing/lid hardware, leads and insulation omitted here; checked separately. No physical fit or powered release.',font=sm,fill='#46525c');d=ImageDraw.Draw(img)
d.text((40,25),'TBH04 | BPM and selector carriers',font=f,fill='#17232c')
d.text((40,65),'Modeled fit candidates; exact printed meshes. Purchased parts and PCB shown as reference solids.',font=sm,fill='#46525c')
d.text((40,730),'BPM tray, three digits at 8 mm pitch; bezel lifted 5 mm for clarity.',font=sm,fill='#17232c')
d.text((800,730),'Same bracket fits both explicit selector breakout boards.',font=sm,fill='#17232c')
d.text((40,795),'Housing/lid hardware, leads and insulation omitted here; checked separately. No physical fit or powered release.',font=sm,fill='#46525c')
img.save(R/'preview.png')
