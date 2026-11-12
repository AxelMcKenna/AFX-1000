"""Native input-stage copper over adjacent filled ground references."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;c=json.loads((R/'capture-r6/capture.json').read_text());b=json.loads((R.parent/'i2c_routing/capture-after-r4/capture.json').read_text());old={z['uuid']for z in b['zones']}
im=Image.new('RGB',(1600,850),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18)
for i,(trace,ref)in enumerate([('F.Cu','In1.Cu'),('B.Cu','In6.Cu'),('In3.Cu','In4.Cu')]):
 p=Image.new('RGB',(500,650),'white');draw=ImageDraw.Draw(p)
 def xy(v):return((v[0]-45)*17.5,(v[1]-52)*22)
 for z in c['zones']:
  if z['layer']!=ref or z['net']!='LINK_AGND':continue
  for poly in z['polygons']:
   draw.polygon([xy(v)for v in poly['outer']],fill='#eeeeee'if z['uuid']in old else'#b7dcc1')
   for hole in poly['holes']:draw.polygon([xy(v)for v in hole],fill='white')
 for o in c['objects']:
  net=o['net'];col='#a0a0a0'
  if net.startswith('/A_INPUT/'):
   col='#c9372e'if'BUF_IN'in net else'#d48920'if'BUF_OUT'in net else'#295bb4'
  elif net=='LINK_AGND':col='#355b3f'
  for poly in o['layers'].get(trace,[]):draw.polygon([xy(v)for v in poly['outer']],fill=col)
 for x in [45,55,65]:draw.text(xy([x,52]),str(x),font=font,fill='black')
 ox=20+530*i;im.paste(p,(ox,100));d.rectangle([ox,100,ox+500,750],outline='#777777');d.text((ox,65),trace+' signals; '+ref+' ground projection',font=font,fill='black')
d.text((20,18),'Analog input routing candidate r6 | actual native copper and return-plane geometry',font=font,fill='black');d.text((20,780),'Red: amplifier input nodes. Orange: output nodes. Blue: other input-stage nets. Green: added ground reference.',font=font,fill='black');d.text((20,815),'Geometry/connectivity evidence only. Parasitics, analog noise/stability and complete-board qualification remain open.',font=font,fill='black');im.save(R/'preview-r6.png')
