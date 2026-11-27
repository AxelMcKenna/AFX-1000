"""Render a review figure from proposal coordinates; no CAD writes."""
import json,math
from pathlib import Path
from PIL import Image,ImageDraw
from shapely.geometry import box
from shapely.affinity import rotate,translate
from .individual import HERE,geometry

def run(root):
    _,_,_,obs,_=geometry(root);o=json.loads((HERE/'individual-placement.json').read_text());paths=json.loads((HERE/'path-screen.json').read_text())
    image=Image.new('RGB',(1800,640),'white');d=ImageDraw.Draw(image)
    for idx,(group,region) in enumerate([('buck',(185,138,205,158)),('held',(130,157,161,182)),('main_detector',(92,156,110,174))]):
        x0,y0,x1,y1=region;s=min(560/(x1-x0),550/(y1-y0));ox=idx*600+20;oy=65
        def xy(pt):return ox+(pt[0]-x0)*s,oy+(pt[1]-y0)*s
        d.text((ox,15),group+' — B.Cu / courtyard proposal',fill='black')
        d.text((ox,35),'Gray: existing obstacles. Lines are unrouted connection screens.',fill='black')
        geom=obs['B.Cu'].intersection(box(*region))
        def drawgeom(g):
            if g.geom_type=='Polygon':
                d.polygon([xy(p) for p in g.exterior.coords],fill='#dedede')
                for ring in g.interiors:d.polygon([xy(p) for p in ring.coords],fill='white')
            elif hasattr(g,'geoms'):
                for gg in g.geoms:drawgeom(gg)
        drawgeom(geom)
        chosen=o['groups'][group]['chosen'];refs={p['ref'] for p in chosen['parts']}
        for row in paths['paths']:
            if row['from'].split('.')[0] in refs and row['to'].split('.')[0] in refs:
                bad=row['foreign_existing_copper_hits'] or row['foreign_proposed_pad_hits'];d.line([xy(p) for p in row['points_mm']],fill='#d22b2b' if bad else '#4e82bc',width=2)
        for p in chosen['parts']:
            g=translate(rotate(box(*o['footprints'][p['ref']]['bounds_mm']),-p['rotation_deg'],origin=(0,0)),*p['at_mm']);pts=[xy(v) for v in g.exterior.coords];d.line(pts,fill='#146b38',width=2);d.text(xy(p['at_mm']),p['ref'],fill='#003e19',anchor='mm')
        d.text((ox,610),'Not routed; no thermal, fabrication or housing fit qualification.',fill='#9e2424')
    image.save(HERE/'individual-placement.png')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
