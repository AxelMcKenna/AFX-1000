"""Orthographic review of exact native meshes; no CAD regeneration."""
import hashlib,json,math,re,struct
from pathlib import Path
from PIL import Image,ImageDraw
H=Path(__file__).resolve().parent;R=H.parents[3]
cap=R/'hardware/cad/two_board_print_01/captured.scad';buttons=json.loads(re.search(r'buttons\s*=\s*(.*?);',cap.read_text(),re.S).group(1));b=next(x for x in buttons if x[0]=='scene_0');theta=math.radians(-b[7])
def load(path,color):
 raw=path.read_bytes();out=[]
 for i in range(struct.unpack_from('<I',raw,80)[0]):
  row=struct.unpack_from('<12fH',raw,84+50*i);points=[]
  for j in (3,6,9):
   x,y,z=row[j:j+3];x-=b[5];y-=b[6];points.append((x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta),z-33.2))
  out.append((points,color))
 return out
holder=H/'native/holder_positive-r1/holder_positive.stl';cut=H/'native/removed-r1/removed.stl'
faces=load(holder,(130,155,177));removed=load(cut,(235,126,34))
image=Image.new('RGB',(1300,650),'white');draw=ImageDraw.Draw(image)
# View from local negative Y and below; painter depth is orthographic.
right=(.94,-.342,0);up=(.171,.47,.866);depth=(-.296,-.814,.5)
def dot(p,v):return sum(a*b for a,b in zip(p,v))
for index,mesh in enumerate([faces,faces+removed]):
 projected=[]
 for tri,color in mesh:
  a,b1,c=tri;u=[b1[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];norm=math.sqrt(dot(n,n))
  shade=.7+.3*abs(dot(n,depth)/norm) if norm else .7
  points=[(325+650*index+18*dot(p,right),390-18*dot(p,up)) for p in tri]
  projected.append((sum(dot(p,depth) for p in tri)/3,points,tuple(int(x*shade) for x in color)))
 for _,points,color in sorted(projected,key=lambda row:row[0],reverse=True):draw.polygon(points,fill=color)
 draw.text((70+650*index,65),['Relieved holder - underside','Orange: removed plastic volume'][index],fill=(25,35,45))
draw.text((70,555),'Exact native meshes; 4.155 mm3 removed. Mounts, lead bores and upper 0.5 mm seat layer preserved.',fill=(25,35,45))
draw.text((70,585),'Printed strength, retention and full-route/service qualification remain open.',fill=(120,55,25))
image.save(H/'holder-review.png')
paths=[Path(__file__),cap,holder,cut,H/'holder-review.png'];(H/'render-review.json').write_text(json.dumps({'view':'Orthographic underside native-mesh review; no geometry changes','source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2)+'\n')
