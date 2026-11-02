"""Screen local rear sites for four remote supervisor CT capacitors.

Courtyard/copper screen only; native routing and renewed installed receiving
remain mandatory. No existing CAD file is changed.
"""
import json
import math
from pathlib import Path
from shapely.geometry import box,Point
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import read_sexpr,children,first
from hardware.fabrication.route_nf_surface import shape,sha,is_logic_net

ROOT=Path(__file__).resolve().parent
TARGETS=[('C37','U25'),('C35','U26'),('C10','U20'),('C8','U21')]


def run():
    capture_path=ROOT/'staging/nf-watchdog-routed-inputs-168/capture.json'
    c=json.loads(capture_path.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'))
    t=read_sexpr(source.read_text());obs=[];local={};poses={}
    for fp in children(t,'footprint'):
        ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
        at=first(fp,'at');x,y=map(float,at[1:3]);ang=float(at[3]) if len(at)>3 else 0
        pts=[]
        for tag in ['fp_rect','fp_line']:
            for n in children(fp,tag):
                if str(first(n,'layer')[1]).endswith('.CrtYd'):
                    pts += [list(map(float,first(n,k)[1:3])) for k in ['start','end']]
        if not pts:
            assert ref in {"H101","H102"} and (x,y) in {(61.,21.),(90.,21.)}
            continue
        b=box(min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))
        local[ref]=b;poses[ref]=(x,y,ang)
        if first(fp,'layer')[1]=='B.Cu' or any(p[2]=='thru_hole' for p in children(fp,'pad')):
            obs.append(translate(rotate(b,-ang,origin=(0,0)),x,y))
    obs += [box(x-4.45,0,x+4.45,39) for x in [38,138]]
    obs += [Point(x,21).buffer(3.9) for x in [61,90]]
    obs += [shape(z['polygons']) for z in c['zones'] if z['keepout'] and z['layer']=='B.Cu']
    cu=[(o,shape(o['layers']['B.Cu'])) for o in c['objects'] if o['layers'].get('B.Cu')]
    ct=STRtree([g for o,g in cu]);results=[];removed_ids=set()
    for ref,owner in TARGETS:
        ot=STRtree(obs)
        pads=sorted([o for o in c['objects'] if o.get('ref')==ref],key=lambda p:p['pin'])
        assert [p['pin'] for p in pads]==['1','2']
        target=next(o for o in c['objects'] if o.get('ref')==owner and o.get('pin')=='5')
        ground=next(o for o in c['objects'] if o.get('ref')==owner and o.get('pin')=='2')
        assert pads[0]['net']==target['net'] and pads[1]['net']==ground['net'] and ground['net']!='/AGND'
        ox,oy,oa=poses[ref]
        pg=[rotate(translate(shape(p['layers']['F.Cu']),-ox,-oy),oa,origin=(0,0)) for p in pads]
        choices=[];congested=[];screen_counts=[0,0,0];tx,ty=target['position_mm']
        for ang in [0,90,180,270]:
            bb=rotate(local[ref],-ang,origin=(0,0));polys=[rotate(p,-ang,origin=(0,0)) for p in pg]
            for ix in range(round((tx-7)*4),round((tx+7)*4)+1):
                for iy in range(round((ty-7)*4),round((ty+7)*4)+1):
                    x,y=ix/4,iy/4;b=translate(bb,x,y)
                    if not box(2,2,147,37).covers(b):continue
                    if any(b.distance(obs[int(i)])<.15 for i in ot.query(b.buffer(.15))):continue
                    screen_counts[0]+=1
                    pp=[translate(p,x,y) for p in polys];ok=True;conflicts={}
                    for pad,g in zip(pads,pp):
                        for i in ct.query(g.buffer(.21)):
                            o,h=cu[int(i)]
                            if o['uuid'] in removed_ids:continue
                            if o['net']!=pad['net'] and g.distance(h)<.21:screen_counts[1]+=1;ok=False;conflicts[o['uuid']]=o
                            if o['kind']=='PCB_VIA' and g.distance(Point(o['position_mm']))<.26:screen_counts[2]+=1;ok=False;conflicts[o['uuid']]=o
                    if not ok and not (len(conflicts)<=3 and all(o['kind']=='PCB_TRACK' and is_logic_net(o['net']) for o in conflicts.values())):
                        continue
                    xy=[(p.centroid.x,p.centroid.y) for p in pp]
                    distance=math.dist(xy[0],target['position_mm']);ret=math.dist(xy[1],ground['position_mm'])
                    score=distance+ret+4*len(conflicts)
                    choices.append(dict(ref=ref,owner=owner,anchor_mm=[x,y],rotation_deg=ang,side='B',projected_CT_pin_distance_mm=distance,projected_return_pin_distance_mm=ret,score=score,courtyard_bounds_mm=list(b.bounds),displaced_logic_tracks=[dict(uuid=o['uuid'],net=o['net'],start_mm=o['position_mm'],end_mm=o['end_mm'],width_mm=o['width_mm']) for o in conflicts.values()]))
        print(ref,'screen counts',screen_counts,flush=True)
        choices.sort(key=lambda r:r['score'])
        if not choices:
            print('Least obstructed:',sorted(congested)[:5],flush=True)
            return
        choice=choices[0];results.append(dict(selected=choice,alternative_count=len(choices),alternatives=choices[1:10]))
        obs.append(box(*choice['courtyard_bounds_mm']))
        removed_ids.update(r['uuid'] for r in choice['displaced_logic_tracks'])
        print(ref,choice,flush=True)
    output=ROOT/'staging/nf-ct-placement-search-01';output.mkdir(exist_ok=False)
    (output/'plan.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in (capture_path,source,Path(__file__))},placements=results,
        grid_mm=.25,courtyard_gap_mm=.15,foreign_copper_gap_mm=.21,rear_complete_height_proposal_mm=1.9,
        native_review_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')


if __name__=='__main__':run()
