"""Conservative unoccupied rectangle search against frozen native TBP72 geometry."""
import argparse,hashlib,json,math
from pathlib import Path
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,children,first
HERE=Path(__file__).resolve().parent

def polygons(xs):return [Polygon(x['outer'],x.get('holes',[])) for x in xs]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(root):
    stage=root/'hardware/fabrication/staging'
    bp=stage/'two-board-power-aux-ground-reuse-native-01/power_protection.kicad_pcb'
    cp=stage/'two-board-power-routing-inputs-aux-ground-reuse-01/capture.json'
    cap=json.loads(cp.read_text());board=read_sexpr(bp.read_text())
    assert any(k.endswith('/power_protection.kicad_pcb') and v==sha(bp) for k,v in cap['source_sha256'].items()), 'Stale capture'
    target=None
    outline=unary_union(polygons(cap['outline'])); area=outline.intersection(box(28,109,327,182)).buffer(-.5)
    occupied={'F.Cu':[],'B.Cu':[]}; missing=[];refs=[]
    for f in children(board,'footprint'):
        ref=next(x[2] for x in children(f,'property') if x[1]=='Reference'); layer=first(f,'layer')[1]
        at=first(f,'at');
        if ref=='P_U102': target=[float(at[1]),float(at[2])]
        angle=float(at[3]) if len(at)>3 else 0; points=[]
        for tag in ['fp_line','fp_rect','fp_poly','fp_arc','fp_circle']:
            for e in children(f,tag):
                if not first(e,'layer')[1].endswith('CrtYd'):continue
                if tag=='fp_arc': raise ValueError('Unsupported courtyard arc; extend conservative envelope before screening')
                if tag=='fp_circle':
                    cx,cy=map(float,first(e,'center')[1:3]);ex,ey=map(float,first(e,'end')[1:3]);r=math.hypot(ex-cx,ey-cy)
                    points.extend([(cx-r,cy-r),(cx+r,cy+r)]);continue
                if tag=='fp_poly': points.extend([tuple(map(float,z[1:3])) for z in first(e,'pts')[1:]])
                else:
                    for t in ['start','end','mid','center']:
                        for z in children(e,t):points.append(tuple(map(float,z[1:3])))
        if not points:
            missing.append(ref)
            # Fail closed for unknown package shape: reserve a 10-mm-radius envelope.
            geom=Point(float(at[1]),float(at[2])).buffer(10)
        else:
            xs,ys=zip(*points);geom=translate(rotate(box(min(xs),min(ys),max(xs),max(ys)),-angle,origin=(0,0)),float(at[1]),float(at[2]))
        occupied[layer].append(geom); refs.append((ref,layer,geom))
    for o in cap['objects']:
        for layer in occupied:occupied[layer].extend(polygons(o['layers'].get(layer,[])))
        drill=o.get('drill_mm',0); drill=max(drill) if isinstance(drill,list) else drill
        if drill>0:
            for layer in occupied:occupied[layer].append(Point(*o['position_mm']).buffer(drill/2+.5))
    for z in cap['zones']:
        if z['keepout']:
            # Deliberately reserve every rule-area outline on both surfaces.
            for layer in occupied:occupied[layer].extend(polygons(z['authored_outline']))
        elif z['layer'] in occupied:occupied[z['layer']].extend(polygons(z['polygons']))
    unions={k:unary_union(v).buffer(.25) for k,v in occupied.items()}
    assert target is not None
    candidates={}
    # Whole block reserved, including interpart routing allowance; no traces authored.
    for kind,w,h in [('bulk_pair',9.12,10.7),('regulator_chain',22,12),('combined',24,20)]:
        found=[]
        for layer,obs in unions.items():
            po=prep(obs);pa=prep(area)
            for turn in [0,90]:
                ww,hh=(w,h) if turn==0 else (h,w)
                for xi in range(28*2,327*2):
                    x=xi/2
                    for yi in range(109*2,182*2):
                        y=yi/2;r=box(x-ww/2,y-hh/2,x+ww/2,y+hh/2)
                        if pa.contains(r) and not po.intersects(r):
                            found.append(dict(layer=layer,center_mm=[x,y],rotation_deg=turn,envelope_mm=[ww,hh],distance_to_P_U102_mm=math.dist([x,y],target)))
        found.sort(key=lambda r:r['distance_to_P_U102_mm'])
        selected=[]
        for f in found:
            if all(f['layer']!=s['layer'] or math.dist(f['center_mm'],s['center_mm'])>max(w,h) for s in selected):selected.append(f)
            if len(selected)==6:break
        candidates[kind]={'passing_grid_count':len(found),'candidates':selected}
    out=dict(status='envelope_screen_only',pcb_modified=False,physical_fit_qualified=False,source_sha256={str(bp.relative_to(root)):sha(bp),str(cp.relative_to(root)):sha(cp)},screen={'step_mm':.5,'obstacle_buffer_mm':.25,'outline_inset_mm':.5,'missing_courtyard_reservation_radius_mm':10,'scope':'power-board x28..327 y109..182 only; all native surface copper, footprint courtyard bounds, drills, rule areas'},missing_courtyards=missing,candidates=candidates)
    out['target_P_U102_mm']=target
    svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="90 106 150 80"><rect x="90" y="106" width="150" height="80" fill="white"/>']
    for g in unions['B.Cu'].intersection(box(90,108,240,183)).simplify(.02).geoms:
        svg.append(g.svg(scale_factor=.02).replace('#66cc99','#d6d6d6'))
    for kind,color in [('bulk_pair','#197a37'),('regulator_chain','#1c57b8')]:
        for n,f in enumerate(candidates[kind]['candidates'][:2]):
            x,y=f['center_mm'];w,h=f['envelope_mm'];svg.append(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" fill="none" stroke="{color}" stroke-width=".3"/><text x="{x-w/2}" y="{y-h/2-.5}" font-size="1.5">{kind} {n+1}</text>')
    svg.append(f'<circle cx="{target[0]}" cy="{target[1]}" r=".8" fill="red"/><text x="{target[0]+1}" y="{target[1]}" font-size="2">P_U102 on F.Cu</text></svg>')
    (HERE/'placement-screen.svg').write_text(''.join(svg))
    (HERE/'placement-screen.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(candidates,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
