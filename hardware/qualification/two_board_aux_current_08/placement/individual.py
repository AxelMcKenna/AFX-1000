"""Conservative unoccupied rectangle search against frozen native TBP72 geometry."""
import argparse,hashlib,json,math
from pathlib import Path
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
from shapely.affinity import rotate,translate,scale
from shapely.prepared import prep
from hardware.electronics.common.sexpr import read_sexpr,children,first
HERE=Path(__file__).resolve().parent

def polygons(xs):return [Polygon(x['outer'],x.get('holes',[])) for x in xs]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def geometry(root):
    stage=root/'hardware/fabrication/staging'
    bp=stage/'two-board-power-aux-local-distribution-native-03/power_protection.kicad_pcb'
    cp=stage/'two-board-power-routing-inputs-aux-local-distribution-03/capture.json'
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
    return cap,board,area,unions,target

def parts():
    import csv
    m=json.loads((HERE/'footprints.json').read_text());assign={r:p['footprint'] for p in m['parts'] for r in p['references']}
    bom={r['reference']:r for r in csv.DictReader((HERE.parent/'held_rail/candidate-bom.csv').open())}
    refs=['P_U900','P_L900','P_C900','P_C901','P_R900','P_R901','E_U900','E_R900','E_C900','P_U901','P_R902','P_C902','P_C903','P_C904','P_R903','P_C905','P_U902','P_C906']
    out={}
    for ref in refs:
        fp=assign.get(ref,bom[ref]['footprint']);lib,name=fp.split(':');p=(HERE/'AUX_READY.pretty'/f'{name}.kicad_mod') if lib=='AUX_READY' else HERE.parent/'held_rail/authored/libraries'/f'{lib}.pretty'/f'{name}.kicad_mod'
        f=read_sexpr(p.read_text());points=[]
        for tag in ['fp_line','fp_rect']:
            for e in children(f,tag):
                if first(e,'layer')[1]=='F.CrtYd':
                    points.extend([list(map(float,first(e,t)[1:3])) for t in ['start','end']])
        xs,ys=zip(*points);out[ref]={'footprint':fp,'source_sha256':sha(p),'bounds_mm':[min(xs),min(ys),max(xs),max(ys)],'pads':{q[1]:[float(x) for x in first(q,'at')[1:3]] for q in children(f,'pad')}}
    return out

def screen(root):
    cap,board,area,obstacles,target=geometry(root);pp=parts()
    # Engineering templates, deliberately separated high-di/dt buck and held reservoir cells.
    templates={
      'buck':{'P_U900':(0,0,0),'P_C900':(-4.1,-.5,180),'P_L900':(4.1,-.5,180),'P_C901':(4.1,3.9,0),'P_R900':(-2.7,3.8,90),'P_R901':(0,4,270)},
      'held':{'P_C902':(0,0,0),'P_C905':(0,5.6,0),'P_R902':(0,-5.1,180),'P_U901':(-7,2.8,180),'P_C903':(-5.6,6.6,270),'P_C904':(-11.65,3.75,180),'P_R903':(-11.2,.7,180),'P_U902':(-7,-1.2,0),'P_C906':(-7,-3.25,0)},
      'main_detector':{'E_U900':(0,0,0),'E_C900':(-3,0,180),'E_R900':(0,2.2,0)}
    }
    result={};chosen=[]
    for group,layout in templates.items():
        local=[]
        for ref,(x,y,angle) in layout.items():local.append((ref,translate(rotate(box(*pp[ref]['bounds_mm']),-angle,origin=(0,0)),x,y)))
        overlaps=[(a,b) for i,(a,ga) in enumerate(local) for b,gb in local[i+1:] if ga.distance(gb)<.2]
        if overlaps:raise ValueError((group,'template overlaps',overlaps))
        cell=unary_union([g for r,g in local]);found=[]
        aim=target if group=='buck' else (next(p['at_mm'] for p in result['buck']['chosen']['parts'] if p['ref']=='P_C901') if group=='held' and result.get('buck',{}).get('chosen') else [97.9,160.8])
        grid=sorted((math.dist([xi*.5,yi*.5],aim),xi*.5,yi*.5) for xi in range(60,650) for yi in range(220,362) if math.dist([xi*.5,yi*.5],aim)<=100)
        busy={layer:prep(unary_union([obs]+[g.buffer(.25) for l,g in chosen if l==layer])) for layer,obs in obstacles.items()}
        inside=prep(area);shapes={(layer,r):rotate(scale(cell,xfact=-1 if layer=='B.Cu' else 1,yfact=1,origin=(0,0)),-r,origin=(0,0)) for layer in obstacles for r in [0,90,180,270]};attempts=0
        for distance,x,y in grid:
            for layer in ['B.Cu','F.Cu']:
                for rot in [0,90,180,270]:
                    shape=shapes[layer,rot]
                    attempts+=1;g=translate(shape,x,y)
                    if inside.contains(g) and not busy[layer].intersects(g):found.append((distance,layer,x,y,rot,g));break
                if found:break
            if found:break
        found.sort(key=lambda f:f[0]);best=found[0] if found else None
        result[group]={'tested_pose_count':attempts,'passing_grid_count':len(found),'template':layout,'chosen':None}
        if best:
            dist,layer,x,y,rot,g=best;chosen.append((layer,g)); placed=[]
            for ref,(dx,dy,ang) in layout.items():
                dx=(-dx if layer=='B.Cu' else dx);ang=(-ang if layer=='B.Cu' else ang)
                rr=math.radians(rot);px=x+dx*math.cos(rr)+dy*math.sin(rr);py=y-dx*math.sin(rr)+dy*math.cos(rr)
                placed.append(dict(ref=ref,at_mm=[px,py],rotation_deg=(ang+rot)%360,kicad_orientation_degrees_after_left_right_flip=(ang+rot+(180 if layer=='B.Cu' else 0))%360,layer=layer,footprint=pp[ref]['footprint']))
            result[group]['chosen']={'anchor_mm':[x,y],'rotation_deg':rot,'layer':layer,'distance_to_target_mm':dist,'parts':placed}
    o={'status':'individual_courtyard_screen_only','pcb_modified':False,'source_sha256':{k:v for k,v in cap['source_sha256'].items() if k.endswith('power_protection.kicad_pcb')},'groups':result,'footprints':pp,'qualified_routing':False,'qualified_housing_fit':False}
    (HERE/'individual-placement.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps({k:{'passing':v['passing_grid_count'],'chosen':v['chosen']} for k,v in result.items()},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);screen(p.parse_args().root)
