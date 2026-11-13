"""Display actual saved copper and reference, independently of planner centerlines."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
from shapely.ops import unary_union
from ..routed.plan import sha,shape
from .verify import H,SRC,OUT,nmshape

def render():
 c=json.loads((SRC/'capture-01/capture.json').read_text());p=json.loads((H/'plan.json').read_text());g=json.loads((OUT/'geometry.json').read_text());assert g['source_board_sha256']==sha(OUT/'power_protection.kicad_pcb');new={z['uuid']:z for z in g['zones']};old={z['uuid']:z for z in c['zones']};im=Image.new('RGB',(1500,1100),'white');d=ImageDraw.Draw(im)
 for side,layer in enumerate(['F.Cu','B.Cu']):
  panel=Image.new('RGB',(750,1040),'white');d=ImageDraw.Draw(panel);xy=lambda q:(30+(q[0]-184)*32,65+(q[1]-115)*32)
  def draw(poly,color):
   if poly.is_empty:return
   if poly.geom_type=='Polygon':
    d.polygon([xy(q) for q in poly.exterior.coords],fill=color)
    for ring in poly.interiors:d.polygon([xy(q) for q in ring.coords],fill='white')
   elif hasattr(poly,'geoms'):
    for v in poly.geoms:draw(v,color)
  ref=unary_union([nmshape(new[uid]['polygons_nm']) if uid in new else shape(old[uid]['polygons']) for uid in p['reference_zone_uuids'][layer]]);draw(ref,'#e4ecf4')
  for o in c['objects']:
   if layer in o['layers']:draw(shape(o['layers'][layer]),'#aeb9c4')
  for o in g['objects']:
   if layer in o['layers_nm']:draw(nmshape(o['layers_nm'][layer]),'#9052aa' if o['net']!="PWR_AGND" else '#2c78ad')
  for v in p['new_vias']:
   x,y=xy(v['position_mm']);d.ellipse((x-4.8,y-4.8,x+4.8,y+4.8),fill='white',outline='black')
  label='P_U101.1' if layer=='F.Cu' else 'P_C900.1';o=next(o for o in c['objects'] if o.get('ref','')+'.'+o.get('pin','')==label);x,y=xy(o['position_mm']);d.text((x-45,y+18),label,fill='black');d.rectangle((0,0,750,60),fill='white');d.text((25,15),layer+' | actual saved copper, board-coordinate projection',fill='black')
  im.paste(panel,(side*750,0))
 d=ImageDraw.Draw(im);d.line((750,0,750,1100),fill='black',width=2);d.rectangle((0,1040,1500,1100),fill='white');d.text((25,1055),'Purple: VIN | Blue: paired return | Grey: retained copper | Pale blue: actual adjacent ground reference',fill='black');d.text((25,1075),'Isolated candidate only. Four DSE errors unwaived; current/thermal/transient qualification remains open.',fill='black');im.save(OUT/'paired-vin.png');(OUT/'visual-provenance.json').write_text(json.dumps({'source_board_sha256':sha(OUT/'power_protection.kicad_pcb'),'geometry_sha256':sha(OUT/'geometry.json'),'renderer_sha256':sha(Path(__file__)),'image_sha256':sha(OUT/'paired-vin.png'),'qualified':False},indent=2)+'\n')
if __name__=='__main__':render()
