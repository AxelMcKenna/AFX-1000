"""Source-bound top-view diagram of D_H4 traces/vias and bearing clearance."""
import json,hashlib,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hardware.fabrication import assembly_layout as al
from hardware.electronics.common import sexpr as sx
H=Path(__file__).resolve().parent;R=H.parents[4]
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(n):return ImageFont.truetype(fontpath,n)
canvas=Image.new('RGB',(1240,850),'#f5f7fa');d=ImageDraw.Draw(canvas)
d.text((35,24),'D_H4 mounting clearance',font=font(30),fill='#142539')
d.text((35,67),'Native F.Cu tracks and vias at mount (188, 80) mm',font=font(20),fill='#35475a')
files=[];summary={}
for i,rev in enumerate(['r98','r107']):
 p=R/f'hardware/cad/two_board_sensor_05/signal_dac/native-{rev}/signal_main.kicad_pcb';files.append(p);tree,_=al.outline(p)
 panel=Image.new('RGB',(570,610),'white');g=ImageDraw.Draw(panel);scale=50.;xy=lambda x,y:((x-183.4)*scale,(y-74.5)*scale)
 def disk(x,y,r,fill,outline=None,width=1):
  a,b=xy(x-r,y-r),xy(x+r,y+r);g.ellipse((*a,*b),fill=fill,outline=outline,width=width)
 for k in range(184,195):
  x,_=xy(k,75);g.line((x,0,x,610),fill='#eef1f4')
 for k in range(75,87):
  _,y=xy(184,k);g.line((0,y,570,y),fill='#eef1f4')
 disk(188,80,2.4,'#fff4db','#d48b10',3)
 disk(188,80,2.25,'#f8e3af')
 for node in sx.children(tree,'segment'):
  if sx.first(node,'layer')[1]!='F.Cu':continue
  start,end=[tuple(map(float,sx.first(node,k)[1:3]))for k in ['start','end']];net=str(sx.first(node,'net')[1]);color='#087cbb' if net=='LINK_SDA' else '#bec9d4'
  g.line([xy(*start),xy(*end)],fill=color,width=max(1,round(float(sx.first(node,'width')[1])*scale)))
 for node in sx.children(tree,'via'):
  if 'F.Cu' not in sx.first(node,'layers')[1:]:continue
  x,y=map(float,sx.first(node,'at')[1:3]);rad=float(sx.first(node,'size')[1])/2;net=str(sx.first(node,'net')[1]);color='#c42c84' if net=='/D_LED/LED_39' else '#9eabb7'
  disk(x,y,rad,color);disk(x,y,float(sx.first(node,'drill')[1])/2,'white')
 disk(188,80,1.2,'#e3e8ed','#41576e',2)
 x,y=xy(188,80);g.line((x-10,y,x+10,y),fill='#41576e',width=1);g.line((x,y-10,x,y+10),fill='#41576e',width=1)
 g.rectangle((0,0,569,609),outline='#b3c0cd',width=2)
 left=35+i*600;canvas.paste(panel,(left,150));d.text((left,115),rev+' — '+('original bearing overlap' if i==0 else 'repaired route and via'),font=font(21),fill='#142539')
 g0=(left+22,722);d.line((g0[0],g0[1],g0[0]+50,g0[1]),fill='#263b4d',width=3);d.text((g0[0]+58,g0[1]-13),'1 mm',font=font(18),fill='#263b4d')
 summary[rev]={'pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
d.text((35,778),'Blue: SDA    Pink: LED_39 via    Orange: 2.4 mm receiving radius',font=font(20),fill='#263b4d')
d.text((35,813),'Pads, fills and solder mask omitted. This diagram does not replace the native copper audit.',font=font(17),fill='#516272')
canvas.save(H/'mount-preview.png')
summary.update(source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),*files]},preview_sha256=hashlib.sha256((H/'mount-preview.png').read_bytes()).hexdigest(),visualization_scope='Top-view traces/vias only; not all copper or physical qualification')
(H/'mount-preview.json').write_text(json.dumps(summary,indent=2)+'\n')
