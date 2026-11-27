"""Orthographic projection of native meshes; cyan volume is a cable envelope."""
from pathlib import Path
import numpy as np,trimesh
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
im=Image.new('RGB',(1400,900),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',23)
M=np.array([[.9,-.44,0],[.18,.37,-.91],[.40,.82,.40]])
def project(p):
 q=(np.array(p)-[225,48,0])@M.T;return(np.array([300,500])+q[:2]*12)
triangles=[]
for name,col in [('route_positive',(182,225,229)),('saddle_main_positive',(219,146,63)),('saddle_sensor_positive',(219,146,63)),('lid_main_positive',(80,126,177)),('lid_sensor_positive',(80,126,177))]:
 m=trimesh.load_mesh(R/'trial-r5'/name/(name+'.stl'))
 for t,n in zip(m.triangles,m.face_normals):
  light=.7+.3*abs(float(n@np.array([.3,-.5,.8])));color=tuple(int(v*light)for v in col);triangles.append((float(t.mean(axis=0)@M[2]),t,color))
for _,t,col in sorted(triangles,key=lambda x:x[0]):d.polygon([tuple(project(v))for v in t],fill=col)
for p,label,off in [([230,55,24.89],'D_J1010 mate',(-90,-80)),([259,66.92,31],'Main clamp',(-50,-80)),([289,79.6,29],'Sensor clamp',(0,-70)),([298.2,85.5,25.1],'AS5600 tails',(20,10)),([250,57,8.35],'D_H2 mount',(-40,55)),([294,88,8.35],'D_H5 mount',(10,55))]:
 xy=project(p);tx=xy+off;d.line([tuple(xy),tuple(tx)],fill='#555555',width=2);d.text(tuple(tx),label,font=font,fill='black')
d.text((40,25),'Corrected sensor harness | main clamp clears latest pot receiving envelope',font=font,fill='black')
d.text((40,815),'Cyan: cable/mate placement envelope. Orange: lower saddles. Blue: clamp lids.',font=font,fill='black')
d.text((40,850),'Physical grip, mating, full bus capacitance and waveform acceptance remain open.',font=font,fill='black')
im.save(R/'preview-r5.png')
