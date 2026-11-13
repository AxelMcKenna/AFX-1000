"""Draw source-bound native capture geometry for DAC routing visual review."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;c=json.loads((R/'capture-r78/capture.json').read_text());b=json.loads((R.parent/'signal_input/capture-r7/capture.json').read_text());original={o['uuid']for o in b['objects']}
im=Image.new('RGB',(1800,1300),'white');d=ImageDraw.Draw(im);font=ImageFont.load_default(size=16)
for k,layer in enumerate(['F.Cu','B.Cu','In3.Cu','In5.Cu']):
 ox,oy=(k%2)*900,(k//2)*650
 def xy(p):return(ox+20+(p[0]-99)*18,oy+45+(p[1]-55)*17)
 d.text((ox+20,oy+10),layer+' | gray original, blue new signal, green new ground',fill='black',font=font)
 if layer=='F.Cu':
  for z in c['zones']:
   if z['keepout']and z['layer']=='In1.Cu'and not z['prohibit_tracks']:
    for p in z['polygons']:d.polygon([xy(q)for q in p['outer']],fill='#ffedda')
 for o in c['objects']:
  if not o['layers'].get(layer):continue
  color='#b0b0b0'if o['uuid']in original else('#279b50'if o['net']=='LINK_AGND'else'#285db4')
  for p in o['layers'][layer]:
   points=[xy(q)for q in p['outer']]
   if all(ox<=x<ox+900 and oy+40<=y<oy+645 for x,y in points):d.polygon(points,fill=color)
 for ref in ['A_U301','A_U302','A_U303','A_U304','A_U305','A_R303','A_R308']:
  os=[o for o in c['objects']if o.get('ref')==ref]
  at=[sum(o['position_mm'][i]for o in os)/len(os)for i in [0,1]];d.text(xy(at),ref,fill='#a02020',font=font)
 d.rectangle((ox,oy,ox+899,oy+649),outline='#999999')
im.save(R/'preview-r78.png')
paths=[Path(__file__),R/'capture-r78/capture.json',R.parent/'signal_input/capture-r7/capture.json',R/'native-r78/signal_main.kicad_pcb',R/'preview-r78.png'];(R/'preview-r78.json').write_text(json.dumps({'source_sha256':{str(p.relative_to(R.parents[3])):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'render_kind':'PIL drawing of exact Linux KiCad captured polygons','window_mm':[99,55,147,90],'not_a_copper_or_mechanical_acceptance_test':True},indent=2)+'\n')
