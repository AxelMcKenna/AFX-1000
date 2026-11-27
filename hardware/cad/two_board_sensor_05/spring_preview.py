"""Exact native meshes shown with nominal sensor-board/package interface."""
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
carrier=trimesh.load_mesh(R/'verified-r3/sensor_carrier/sensor_carrier.stl');carrier.apply_translation([295.8,65.5,17.6])
cap=trimesh.load_mesh(R/'verified-r3/sensor_cap/sensor_cap.stl');cap.apply_translation([0,0,-7.2]);cap.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[0,1,0]));cap.apply_translation([295.8,68,35.6])
bracket=trimesh.load_mesh(R/'spring-verified-r2/spring_bracket/spring_bracket.stl');bracket.apply_translation([303,66,14.6])
arm=trimesh.load_mesh(R/'spring-verified-r2/lever_arm_spring/lever_arm_spring.stl');arm.apply_translation([305,77,21.6])
board=trimesh.creation.box([1.6,20,18]);board.apply_translation([300.5,82,30.6])
package=trimesh.creation.box([1.75,6.4,6.4]);package.apply_translation([302.175,82,31.6])
image=Image.new('RGB',(1500,950),'#f4f6f8');d=ImageDraw.Draw(image);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',22)
def render(items,cam,vp):
 cam=np.array(cam);cam/=np.linalg.norm(cam);right=np.cross([0,0,1],cam);right/=np.linalg.norm(right);up=np.cross(cam,right);basis=np.array([right,up,cam]).T
 ps=np.concatenate([np.asarray(m.vertices)@basis for m,c in items]);lo,hi=ps.min(0),ps.max(0);scale=min(vp[2]/(hi[0]-lo[0]),vp[3]/(hi[1]-lo[1]));faces=[]
 for m,col in items:
  pts=np.asarray(m.vertices)@basis;pts[:,0]=vp[0]+(pts[:,0]-lo[0])*scale;pts[:,1]=vp[1]+(hi[1]-pts[:,1])*scale
  shade=.55+.45*np.maximum(0,m.face_normals@np.array([.5,-.2,.84]))
  for i,face in enumerate(m.faces):
   if m.face_normals[i]@cam>0:faces.append((pts[face,2].mean(),pts[face,:2],tuple(int(c*shade[i])for c in col)))
 for _,poly,c in sorted(faces,key=lambda x:x[0]):d.polygon([tuple(p)for p in poly],fill=c)
d.text((35,25),'TBH05 sensor carrier candidate | checked native geometry',font=font,fill='#17232c')
d.text((35,60),'Native checked spring bracket and arm; sensor PCB has passed ERC/DRC. Physical qualification pending.',font=font,fill='#475764')
render([(carrier,(224,159,75)),(cap,(100,145,185)),(bracket,(145,150,155)),(arm,(105,180,155)),(board,(50,115,80)),(package,(60,60,65))],[-.8,-.5,.45],(40,150,680,650))
render([(carrier,(224,159,75)),(cap,(100,145,185))],[.8,-.5,.45],(800,170,620,600))
d.text((35,855),'Left: board, carrier and replacement lever. Right: carrier and removable top cap.',font=font,fill='#17232c')
d.text((35,895),'Fasteners, wiring, spring and magnet omitted. Nominal fit; print and measure before assembly.',font=font,fill='#475764')
image.save(R/'spring-preview.png')
