"""Projection of native final copper/reference capture; no CAD editing or mesh repair."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;c=json.loads((R/'capture-after-r4/capture.json').read_text());b=json.loads((R/'capture-baseline/capture.json').read_text());r=json.loads((R/'candidate-r4/routing.json').read_text());oldzones={z['uuid']for z in b['zones']}
im=Image.new('RGB',(1500,1000),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',20)
for i,(trace,plane)in enumerate([('In3.Cu','In4.Cu'),('B.Cu','In6.Cu')]):
 ox=40+i*740;oy=120
 panel=Image.new('RGB',(675,765),'white');pd=ImageDraw.Draw(panel)
 def xy(p):return((p[0]-169)*25,(p[1]-65)*25)
 d.text((ox,65),f'{trace} signals; actual adjacent {plane} ground fill',font=font,fill='black')
 for z in c['zones']:
  if z['layer']!=plane or z['net']!='LINK_AGND':continue
  for poly in z['polygons']:
   pd.polygon([xy(p)for p in poly['outer']],fill='#b7dcc1'if z['uuid']not in oldzones else'#eeeeee')
   for h in poly['holes']:pd.polygon([xy(p)for p in h],fill='white')
 for o in c['objects']:
  for poly in o['layers'].get(trace,[]):
   color={'LINK_SCL':'#c52d24','LINK_SDA':'#2455bd','LINK_AGND':'#366443'}.get(o['net'],'#999999');pd.polygon([xy(p)for p in poly['outer']],fill=color)
 for y,label in [(77,'7: rail health'),(92,'1: control return')]:
  pd.text(xy([169.3,y+.9]),label,font=font,fill='black')
 for x in [170,180,190]:pd.text(xy([x,65]),str(x),font=font,fill='black')
 im.paste(panel,(ox,oy));d.rectangle([ox,oy,ox+675,oy+765],outline='#777777',width=1)
d.rectangle([0,0,1500,45],fill='white');d.text((35,12),'I2C routing candidate r4 | native geometry and filled reference projection',font=font,fill='black')
d.rectangle([0,910,1500,1000],fill='white');d.text((35,925),'Red SCL; blue SDA; green added ground. Control return at A_J402.1 plus local signal-transition stitches; pin7 excluded.',font=font,fill='black');d.text((35,960),'Geometric reference screen only. Stackup, high-current/noise and physical bus acceptance remain open.',font=font,fill='black');im.save(R/'preview-r4.png')
