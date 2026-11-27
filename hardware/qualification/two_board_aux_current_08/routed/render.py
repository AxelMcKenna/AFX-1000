import json
from PIL import Image,ImageDraw
from shapely.geometry import Polygon,box
from .verify import HERE

def run():
 out=HERE/'native-04';cap=json.loads((out/'local-native-geometry.json').read_text());review=json.loads((out/'review.json').read_text());old={u for g in review['before_groups'] for u in g['members']};im=Image.new('RGB',(1500,1500),'white');d=ImageDraw.Draw(im);x,y,w,h=cap['viewport_mm'];scale=1400/w
 def pt(p):return (50+(p[0]-x)*scale,50+(p[1]-y)*scale)
 def poly(p,color):
  g=Polygon(p['outer'],p['holes']).intersection(box(x,y,x+w,y+h))
  gs=list(g.geoms) if hasattr(g,'geoms') else [g]
  for q in gs:
   if q.geom_type!='Polygon' or q.is_empty:continue
   d.polygon([pt(p) for p in q.exterior.coords],fill=color)
   for r in q.interiors:d.polygon([pt(p) for p in r.coords],fill='white')
 for p in cap['reference_polygons']:poly(p,'#e9f0df')
 colors={'PWR_AGND':'#217b3d','/P_power_supply/AUX_PREREG_SW':'#d56b08','/P_power_supply/AUX_PREREG5':'#315da8','/P_power_supply/VIN_IC':'#b12935','/P_power_supply/AUX_PREREG_FB':'#7c338d'}
 drills=[];labels=[]
 for o in cap['objects']:
  for p in o['polygons']:poly(p,'#999999' if o['uuid'] in old else colors.get(o['net'],'#222222'))
  if o['kind']=='PCB_VIA':
   xx,yy=pt(o['position_mm']);r=o['drill_mm']/2*scale;drills.append((xx-r,yy-r,xx+r,yy+r))
  if o.get('ref','').startswith(('P_U900','P_C900','P_L900','P_C901','P_R900','P_R901')):
   p=Polygon(o['polygons'][0]['outer']).centroid;xx,yy=pt([p.x,p.y]);labels.append((xx,yy,o['pin']))
 for rect in drills:d.ellipse(rect,fill='white')
 for xx,yy,pin in labels:d.text((xx,yy),pin,fill='white',anchor='mm')
 d.text((50,15),'Native B.Cu: red VIN; orange SW; blue 5V; purple FB; green GND. Pale fill: native In6 GND.',fill='black')
 d.text((50,1465),'Isolated candidate; supervisor DRC conflict and overall electrical qualification remain open.',fill='black')
 im.save(out/'local-native-copper.png')
if __name__=='__main__':run()
