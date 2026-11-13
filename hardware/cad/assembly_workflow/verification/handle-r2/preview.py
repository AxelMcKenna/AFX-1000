"""Project verified native meshes for assembled and handle-withdrawn review."""
import json
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
from hardware.cad.assembly_workflow import workflow as w
H=Path(__file__).resolve().parent

def run():
    _,parts,_,_=w.load_manifest(H/'selected-candidate.json')
    items=[];evidence={}
    for name,color in [('sensor_lever_nominal',(80,133,167)),('cap_handle_r2',(51,159,145)),('cap_handle_screw_r2',(164,172,183))]:
        identity,folder=w.job('component',parts[name],parts);result=w.cached(identity,folder)
        assert result and result['passed'];w.assert_current(identity)
        file=folder/'geometry.stl';items.append((name,trimesh.load_mesh(file),color));evidence[w.relative(file)]=w.sha(file)
    cam=np.array([.6,-1.,.75]);cam/=np.linalg.norm(cam);right=np.cross([0,0,1],cam);right/=np.linalg.norm(right);up=np.cross(cam,right);basis=np.array([right,up,cam]).T
    points=np.concatenate([m.vertices@basis for _,m,_ in items]+[(m.vertices+[0,0,8])@basis for name,m,_ in items if name=='cap_handle_r2'])
    lo,hi=points.min(0),points.max(0);scale=min(650/(hi[0]-lo[0]),670/(hi[1]-lo[1]))
    img=Image.new('RGB',(1600,1000),'#f3f6f8');draw=ImageDraw.Draw(img)
    font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',28);small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',20)
    draw.text((45,28),'Selected removable lever | verified native mesh projections',font=font,fill='#183445')
    draw.text((45,75),'Blue: lever body. Teal: handle. Grey: sourced screw receiving envelope.',font=small,fill='#405867')
    pixels=np.asarray(img).copy();depth=np.full((1000,1600),-np.inf)
    light=np.array([.3,-.5,.8]);light/=np.linalg.norm(light)
    for x,withdrawn in [(60,False),(850,True)]:
        faces=[]
        for name,m,color in items:
            if withdrawn and name=='cap_handle_screw_r2':continue
            move=np.array([0,0,8]) if withdrawn and name=='cap_handle_r2' else np.zeros(3)
            pts=(m.vertices+move)@basis;pts[:,0]=x+(pts[:,0]-lo[0])*scale;pts[:,1]=180+(hi[1]-pts[:,1])*scale
            shade=.55+.45*np.maximum(0,m.face_normals@light)
            for i,face in enumerate(m.faces):
                if m.face_normals[i]@cam>0:faces.append((pts[face],tuple(int(v*shade[i]) for v in color)))
        for pts,color in faces:
            x0,y0=pts[:,:2].min(0).astype(int);x1,y1=np.ceil(pts[:,:2].max(0)).astype(int)
            x0=max(0,x0);y0=max(0,y0);x1=min(1599,x1);y1=min(999,y1)
            if x1<x0 or y1<y0:continue
            a,b,c=pts;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-12:continue
            xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
            u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
            t=1-u-v;z=u*a[2]+v*b[2]+t*c[2]
            target=depth[y0:y1+1,x0:x1+1];visible=(u>=-1e-8)&(v>=-1e-8)&(t>=-1e-8)&(z>target)
            target[visible]=z[visible];pixels[y0:y1+1,x0:x1+1][visible]=color
    img=Image.fromarray(pixels);draw=ImageDraw.Draw(img)
    for x,withdrawn in [(60,False),(850,True)]:
        draw.text((x,130),'Handle lifted 8 mm; screw removed first' if withdrawn else 'Assembled nominal geometry',font=small,fill='#183445')
    draw.text((45,910),'Housing and other parts omitted for visibility. Thread strength, retention and full wired service remain unqualified.',font=small,fill='#405867')
    img.save(H/'preview.png')
    (H/'preview.json').write_text(json.dumps(dict(source_sha256={**evidence,w.relative(Path(__file__)):w.sha(Path(__file__))},
        image_sha256=w.sha(H/'preview.png'),physical_qualified=False),indent=2)+'\n')
if __name__=='__main__':run()
