import json
from pathlib import Path
from PIL import Image,ImageDraw
from shapely.geometry import box
from hardware.qualification.two_board_aux_current_08.routed.plan import shape
h=Path('hardware/qualification/two_board_aux_current_08/ldo_local');c=json.loads((h/'capture-01/capture.json').read_text());p=json.loads((h/'direct-return-plan.json').read_text());im=Image.new('RGB',(1100,1000),'white');d=ImageDraw.Draw(im);xy=lambda v:(20+(v[0]-182)*65,30+(v[1]-121)*65)
def draw(g,color):
 if g.is_empty:return
 if g.geom_type=='Polygon':
  d.polygon([xy(v) for v in g.exterior.coords],fill=color)
  for r in g.interiors:d.polygon([xy(v) for v in r.coords],fill='white')
 else:
  for x in g.geoms:draw(x,color)
for z in c['zones']:
 if z['uuid'] in p['reference_zone_uuids']:draw(shape(z['polygons']),'#d7e4f2')
for o in c['objects']:
 if 'F.Cu' not in o['layers']:continue
 g=shape(o['layers']['F.Cu']);draw(g,'#538ab3' if o['net']=='PWR_AGND' else '#b1a8b8')
 if o.get('ref','').startswith('P_') and 183<o['position_mm'][0]<198 and 122<o['position_mm'][1]<135:d.text(xy(o['position_mm']),o['ref']+'.'+o['pin'],fill='black')
from hardware.qualification.two_board_aux_current_08.vin_escape.verify import saved_fill,nmshape
from hardware.electronics.common.sexpr import read_sexpr,children,first
t=read_sexpr((h/'native-07/power_protection.kicad_pcb').read_text());z=next(z for z in children(t,'zone') if first(z,'uuid')[1]=='6426ba88-8fe7-5dbe-a480-447525689bde');draw(saved_fill(z),'#b6e9dd')
for x in [188.275,186.725]:draw(box(x-.45,126.125,x+.45,127.075),'#bc6bd0')
for o in json.loads((h/'native-07/added-copper-geometry.json').read_text())['objects']:draw(nmshape(o['layers_nm']['F.Cu']),'#007550' if o['net']=='PWR_AGND' else '#e35935')
d.text((20,10),'C907 local bypass: native copper + In1 reference patch (green); isolated/unqualified',fill='black')
im.save(h/'native-07/local-return.png')
