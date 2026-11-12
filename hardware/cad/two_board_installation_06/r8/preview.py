"""Native STL projection for engineering review; no native GUI."""
from pathlib import Path
import numpy as np,trimesh
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
img=Image.new('RGB',(1500,850),'#f4f6f8');d=ImageDraw.Draw(img);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',23)
items=[(trimesh.load_mesh(R/'native/supports/supports.stl'),(80,140,175)),(trimesh.load_mesh(R/'native-terminal/harness/harness.stl'),(230,105,35))]
cam=np.array([-.4,-.3,1.4]);cam/=np.linalg.norm(cam);right=np.cross([0,0,1],cam);right/=np.linalg.norm(right);up=np.cross(cam,right);basis=np.array([right,up,cam]).T
pts=np.concatenate([m.vertices@basis for m,_ in items]);lo=pts.min(0);hi=pts.max(0);scale=min(1350/(hi[0]-lo[0]),600/(hi[1]-lo[1]));faces=[]
for m,c in items:
 pts=m.vertices@basis;pts[:,0]=70+(pts[:,0]-lo[0])*scale;pts[:,1]=140+(hi[1]-pts[:,1])*scale
 light=np.array([-.5,-.4,.76]);shade=.55+.45*np.maximum(0,m.face_normals@light)
 for i,f in enumerate(m.faces):
  if m.face_normals[i]@cam>0:faces.append((pts[f,2].mean(),pts[f,:2],tuple(int(v*shade[i])for v in c)))
for _,p,c in sorted(faces,key=lambda a:a[0]):d.polygon([tuple(v)for v in p],fill=c)
d.text((40,30),'TBH06 r8 internal supports and terminal wires | native STL geometry',font=font,fill='#17232c')
d.text((40,70),'Blue: two bolt-retained brackets and three closed routing eyes. Orange: wire envelopes.',font=font,fill='#475764')
d.text((40,785),'External lead-bay routing and physical receiving remain open. Shell/PCB omitted for visibility.',font=font,fill='#17232c')
img.save(R/'preview.png')
