"""Native STL projection for engineering review; no native GUI."""
from pathlib import Path
import numpy as np,trimesh
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
img=Image.new('RGB',(1500,850),'#f4f6f8');d=ImageDraw.Draw(img);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',23)
items=[(trimesh.load_mesh(R/'native/shell_variant/shell_variant.stl'),(148,164,178))]
for y in [45,145]:
 for name,dy,color in [('pod',y-30,(227,154,68)),('guard',y-22.75,(72,110,128))]:
  m=trimesh.load_mesh(R/f'native/{name}/{name}.stl');m.apply_translation([0,dy,0]);items.append((m,color))
cam=np.array([-.8,-.5,.48]);cam/=np.linalg.norm(cam);right=np.cross([0,0,1],cam);right/=np.linalg.norm(right);up=np.cross(cam,right);basis=np.array([right,up,cam]).T
pts=np.concatenate([m.vertices@basis for m,_ in items]);lo=pts.min(0);hi=pts.max(0);scale=min(1350/(hi[0]-lo[0]),600/(hi[1]-lo[1]));faces=[]
for m,c in items:
 pts=m.vertices@basis;pts[:,0]=70+(pts[:,0]-lo[0])*scale;pts[:,1]=140+(hi[1]-pts[:,1])*scale
 light=np.array([-.5,-.4,.76]);shade=.55+.45*np.maximum(0,m.face_normals@light)
 for i,f in enumerate(m.faces):
  if m.face_normals[i]@cam>0:faces.append((pts[f,2].mean(),pts[f,:2],tuple(int(v*shade[i])for v in c)))
for _,p,c in sorted(faces,key=lambda a:a[0]):d.polygon([tuple(v)for v in p],fill=c)
d.text((40,30),'TBH06 external fan-pod alternative | native shell/pod/guard STL geometry',font=font,fill='#17232c')
d.text((40,70),'Separate shell variant. Fan bodies, mesh, hardware and PCBs omitted in this view.',font=font,fill='#475764')
d.text((40,785),'359 mm total modeled width with bolt heads. Geometry candidate; airflow/thermal release remains open.',font=font,fill='#17232c')
img.save(R/'preview.png')
