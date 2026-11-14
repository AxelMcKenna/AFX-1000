"""Static projection of the exact delivery STL triangles; no CAD runtime."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import trimesh
R=Path(__file__).resolve().parent;P=R/'retention-package/print'
img=Image.new('RGB',(1600,950),'#f4f6f8');d=ImageDraw.Draw(img)
f=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',24);small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18)
camera=np.array([.75,-.6,.35]);camera/=np.linalg.norm(camera);right=np.cross([0,0,1],camera);right/=np.linalg.norm(right);up=np.cross(camera,right);basis=np.array([right,up,camera]).T
bracket=trimesh.load_mesh(P/'retained_bracket.stl');bracket.apply_translation([303,66,14.6])
guard=trimesh.load_mesh(P/'pivot_guard.stl');guard.apply_translation([322,65,17.6])
arm=trimesh.load_mesh(P/'lever_arm_r6.stl');arm.apply_translation([305,78,21.6])
def render(items,vp):
 allpts=np.concatenate([np.asarray(m.vertices)@basis for m,c in items]);lo,hi=allpts.min(0),allpts.max(0);scale=min(vp[2]/(hi[0]-lo[0]),vp[3]/(hi[1]-lo[1]));faces=[]
 for m,col in items:
  pts=np.asarray(m.vertices)@basis;pts[:,0]=vp[0]+(pts[:,0]-lo[0])*scale;pts[:,1]=vp[1]+(hi[1]-pts[:,1])*scale
  light=np.array([.5,-.2,.84]);shade=.55+.45*np.maximum(0,m.face_normals@light)
  for i,face in enumerate(m.faces):
   if m.face_normals[i]@camera>0:faces.append((pts[face,2].mean(),pts[face,:2],tuple(int(c*shade[i])for c in col)))
 for _,poly,c in sorted(faces,key=lambda x:x[0]):d.polygon([tuple(p)for p in poly],fill=c)
d.text((45,30),'TBH03 lever retention | exact delivered STL geometry',font=f,fill='#17232c')
d.text((45,70),'Unpowered fit prototype. Housing and r6 arm unchanged; shaft and fasteners not shown.',font=small,fill='#475764')
render([(bracket,(124,151,173)),(guard,(231,164,74)),(arm,(91,183,158))],(55,140,650,610))
d.text((45,790),'Installed geometry: blue bracket, amber removable bearing cap/guard, green arm',font=small,fill='#17232c')
render([(trimesh.load_mesh(P/'pivot_guard.stl'),(231,164,74))],(880,150,560,370))
d.text((850,555),'Guard: shared right M3 mounts; positive shaft-end stop',font=small,fill='#17232c')
for j,n in enumerate(['left_shim_9','right_shim_9']):render([(trimesh.load_mesh(P/(n+'.stl')),(124,151,173))],(880+j*280,635,200,135))
d.text((850,810),'Thrust shims: nominal 0.9 mm; select by measured endplay',font=small,fill='#17232c')
d.text((45,885),'Print coupon first. Verify 0.10–0.30 mm endplay and free 0–35° motion before hand assembly.',font=small,fill='#475764')
img.save(R/'preview-r5.png')
