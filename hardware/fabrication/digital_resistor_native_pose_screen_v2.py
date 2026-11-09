"""Screen native rotated front- or back-side resistor poses against native and proposed copper.

Preserve pad assignments and all other components; use native rotation templates.
Mechanical, pad-copper and drill guards match the existing placement workflow.
"""
import copy,itertools,math
from shapely.affinity import translate
from shapely.geometry import Point,LineString,box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
import hardware.fabrication.route_nf_surface as surface

def polygons(g):
    return [dict(outer=list(g.exterior.coords),holes=[list(h.coords) for h in g.interiors])]

def candidates(capture,board,ref,fixed_routes,xs,ys,score,templates):
    fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(board,'footprint')}
    old=fps[ref];assert first(old,'layer')[1]=='B.Cu'
    origin=tuple(map(float,first(old,'at')[1:3]));court=box(*courtyard(old,'B.CrtYd'))
    oldpads=[o for o in capture['objects'] if o.get('ref')==ref];assert len(oldpads)==2 and all(set(o['layers'])=={'B.Cu'} for o in oldpads)
    work=copy.deepcopy(capture);work['objects']=[o for o in capture['objects'] if o.get('ref')!=ref]
    sides={r:first(f,'layer')[1][0] for r,f in fps.items()}
    profile=surface.shape(capture['outline']);mounts=[box(x-3.6,y-3.6,x+3.6,y+3.6) for x,y in [(4,4),(66,13),(110,25),(4,36),(110,44)]]
    base=CloseMarginViaScreen(work,signal_layers=surface.SIGNAL_LAYERS)
    drilled=[(Point(p),r) for _,p,r,_ in base.drilled]
    poses=[];counts=dict(screened=0,mechanical=0,pad_clear=0)
    for template in templates:
        assert template['ref']==ref and template['side'] in ('F','B')
        side=template['side'];face=side+'.Cu'
        assert first(template['footprint'],'layer')[1]==face
        court=box(*courtyard(template['footprint'],side+'.CrtYd'))
        courts=[box(*courtyard(f,side+'.CrtYd')) for r,f in fps.items() if r!=ref and sides[r]==side]
        tht=[box(*pad_box(f,p,.5)) for r,f in fps.items() if r!=ref and sides[r]!=side for p in children(f,'pad') if p[2]=='thru_hole']
        geometry=[(o['net'],surface.shape(o['layers'][face])) for o in work['objects'] if o['layers'].get(face)]
        drilled=[(Point(p),r) for _,p,r,_ in base.drilled]
        for r in fixed_routes:
            geometry += [(r['net'],LineString(path).buffer(.1,quad_segs=64)) for layer,path in r['runs'] if layer==face]
            geometry += [(r['net'],Point(p).buffer(.3,quad_segs=64)) for p in r['new_vias_mm']]
            drilled += [(Point(p),.15) for p in r['new_vias_mm']]
        tree=STRtree([g for n,g in geometry])
        for x,y in itertools.product(xs,ys):
            counts['screened']+=1;dx,dy=x-origin[0],y-origin[1];cc=translate(court,x,y)
            if not profile.covers(cc) or cc.distance(profile.boundary)<.5-1e-8:continue
            if any(cc.distance(g)<.15-1e-8 for g in mounts) or any(cc.distance(g)<.3-1e-8 for g in courts):continue
            if any(cc.intersection(g).area>1e-10 for g in tht):continue
            counts['mechanical']+=1;pads=[]
            for nativepad in template['pads']:
                oldpad=next(p for p in oldpads if p['pin']==nativepad['pin'])
                assert oldpad['uuid']==nativepad['uuid'] and oldpad['net']==nativepad['net']
                g=translate(surface.shape(nativepad['polygons']),x,y);net=oldpad['net']
                if any(other!=net and g.distance(obstacle)<.21-1e-8 for i in tree.query(g.buffer(.22)) for other,obstacle in [geometry[int(i)]]):break
                if any(point.distance(g)-radius<.16-1e-8 for point,radius in drilled):break
                pad=copy.deepcopy(oldpad);pad['position_mm']=[nativepad['position_mm'][0]+x,nativepad['position_mm'][1]+y];pad['layers']={face:polygons(g)};pad['group']=None;pad.pop('orientation_degrees',None);pads.append(pad)
            if len(pads)!=2:continue
            counts['pad_clear']+=1;fp=copy.deepcopy(template['footprint']);first(fp,'at')[1:3]=[x,y]
            pose=dict(ref=ref,side=side,angle=template['angle'],native_template=template['file'],position_mm=[x,y],translation_mm=[dx,dy],footprint=fp,pads=pads)
            pose['score']=score(pose);poses.append(pose)
    return sorted(poses,key=lambda p:p['score']),counts,work
