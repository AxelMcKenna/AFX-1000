"""Render captured native local copper in board-coordinate projection."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
from ..routed.plan import sha,shape
from .verify import nmshape
H=Path(__file__).resolve().parent;OUT=H/'native-01'
def render():
 c=json.loads((H/'capture-02/capture.json').read_text());p=json.loads((H/'plan.json').read_text());g=json.loads((OUT/'added-copper-geometry.json').read_text());assert g['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');im=Image.new('RGB',(1440,1000),'white');d=ImageDraw.Draw(im);xy=lambda q:(40+(q[0]-136)*20,70+(q[1]-137)*20)
 def draw(poly,color):
  if poly.is_empty:return
  if poly.geom_type=='Polygon':
   d.polygon([xy(q) for q in poly.exterior.coords],fill=color)
   for ring in poly.interiors:d.polygon([xy(q) for q in ring.coords],fill='white')
  elif hasattr(poly,'geoms'):
   for v in poly.geoms:draw(v,color)
 for z in c['zones']:
  if z['uuid'] in p['reference_zone_uuids']:draw(shape(z['polygons']),'#e8edf5')
 for o in c['objects']:
  if 'B.Cu' in o['layers']:draw(shape(o['layers']['B.Cu']),'#b9c0c7')
 colors={'PWR_AGND':'#557db0','PWR_AUX_HELD3V3':'#238a60','/P_power_supply/AUX_HELD_IN':'#c34c43','/P_power_supply/AUX_PREREG5':'#9a5aa1'}
 for o in g['objects']:
  if 'B.Cu' in o['layers_nm']:draw(nmshape(o['layers_nm']['B.Cu']),colors[o['net']])
 for o in c['objects']:
  if o.get('ref') in ['P_C901','P_R902']:
   x,y=xy(o['position_mm']);d.text((x+4,y+2),o['ref']+'.'+o['pin'],fill='black')
 for v in p['new_vias']:
  x,y=xy(v['position_mm']);r=.15*48;d.ellipse((x-r,y-r,x+r,y+r),fill='white',outline='black')
 d.rectangle((0,0,1200,55),fill='white');d.text((25,15),'Isolated 5 V reservoir feed: actual native B.Cu, board-coordinate projection',fill='black');d.rectangle((0,930,1440,1000),fill='white');d.text((25,940),'Purple: new 0.8 mm 5 V feed | Grey: retained B.Cu | Pale blue: retained reference fill',fill='black');d.text((25,960),'VIN input, main LDO feed, held distribution and RESET remain pending. Four DSE errors unwaived.',fill='black');im.save(OUT/'feed-copper.png');(OUT/'visual-provenance.json').write_text(json.dumps({'board_sha256':sha(OUT/'power_protection.kicad_pcb'),'native_added_geometry_sha256':sha(OUT/'added-copper-geometry.json'),'capture_sha256':sha(H/'capture-02/capture.json'),'renderer_sha256':sha(Path(__file__)),'image_sha256':sha(OUT/'feed-copper.png'),'projection':'board coordinates, B.Cu copper; not component-body or bottom-view artwork','qualified':False},indent=2)+'\n')
if __name__=='__main__':render()
