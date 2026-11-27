"""Actual saved B.Cu route and adjacent reference evidence."""
import json
from PIL import Image,ImageDraw
from shapely.ops import unary_union
from .verify import H,BASE,OUT,sha,shape,nmshape

def render():
 c=json.loads((H/'capture-01/capture.json').read_text());p=json.loads((H/'plan.json').read_text());g=json.loads((OUT/'added-copper-geometry.json').read_text());assert g['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');im=Image.new('RGB',(800,1400),'white');d=ImageDraw.Draw(im);xy=lambda q:(30+(q[0]-183)*38,60+(q[1]-117)*38)
 def draw(poly,col):
  if poly.is_empty:return
  if poly.geom_type=='Polygon':
   d.polygon([xy(q) for q in poly.exterior.coords],fill=col)
   for hole in poly.interiors:d.polygon([xy(q) for q in hole.coords],fill='white')
  else:
   for v in poly.geoms:draw(v,col)
 for z in c['zones']:
  if z['uuid'] in p['reference_zone_uuids']:draw(shape(z['polygons']),'#e2ecf6')
 for o in c['objects']:
  if 'B.Cu' in o['layers']:draw(shape(o['layers']['B.Cu']),'#aebbc8')
 for o in g['objects']:draw(nmshape(o['layers_nm']['B.Cu']),'#9852b3')
 d.text((20,15),'B.Cu main LDO capacitor feed | actual saved copper, board-coordinate projection',fill='black');d.text((20,1360),'Purple: new 5 V route | blue: adjacent ground reference | grey: original copper',fill='black');d.text((20,1380),'Isolated candidate. DSE/current/thermal/timing qualification remains open.',fill='black');im.save(OUT/'main-ldo-feed.png');(OUT/'visual-provenance.json').write_text(json.dumps({'script_sha256':sha(H/'render.py'),'board_sha256':sha(OUT/'power_protection.kicad_pcb'),'geometry_sha256':sha(OUT/'added-copper-geometry.json'),'image_sha256':sha(OUT/'main-ldo-feed.png')},indent=2)+'\n')
if __name__=='__main__':render()
