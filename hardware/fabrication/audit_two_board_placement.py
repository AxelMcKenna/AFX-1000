"""Independent continuous-envelope checks of TB04 or a successor placement."""
import argparse
import json
from collections import Counter
from pathlib import Path
from shapely.geometry import Polygon, box, Point
from shapely.strtree import STRtree
from hardware.fabrication.two_board_placement import REPO,ROOT,sha


def audit(folder):
    c=json.loads((folder/'capture.json').read_text());p=json.loads((folder/'placement.json').read_text())
    issues=[];sources=0
    for data in [c,p]:
        for name,h in data['source_sha256'].items():
            sources+=1
            if sha(REPO/name)!=h:issues.append(['source_hash',name])
    assert set(p['poses'])=={v['id'] for v in c['parts']}
    contexts=[q for q in c['context'] if not q['id'].startswith('inlet_')]
    # Independently add the four explicit panel PCB slabs; component bodies are
    # already in the retained context. Their exact underside construction is open.
    ap=json.loads((ROOT/'staging/assembly-layout-04/allocation.json').read_text())
    for name,x,y,z,dx,dy,t,*_ in ap['additional_panel_PCBS']:
        contexts.append(dict(id=name,xy=[x,y,x+dx,y+dy],z=[z,z+t]))
    polys={'signal_main':Polygon(c['signal_polygon']),'power_protection':Polygon(c['power_polygon'],c['power_holes'])}
    receivers=[];land_extents=[]
    for row in c['parts']:
        pose=p['poses'][row['id']];x,y=pose['xy'];b=row['body_relative_xy']
        poly=box(b[0]+x,b[1]+y,b[2]+x,b[3]+y)
        z=c['signal_Z'] if row['target_board']=='signal_main' else c['power_Z']
        interval=[z-.2+1.44,z+.2+1.76+row['height_mm']] if row['side']=='F' else [z-.2-row['height_mm'],z+.2]
        receivers.append(dict(id=row['id'],owner=row['id'],board=row['target_board'],kind='body',side=row['side'],poly=poly,z=interval))
        if not (row['role']=='input_protection' and row['ref'] in ['J1','S1']) and not polys[row['target_board']].buffer(-.5).covers(poly):
            issues.append(['body_edge_receiving',row['id']])
        for i,t in enumerate(row['tails_relative_xy']):
            assert row['side']=='F','Opposite-side THT must be explicitly transformed'
            poly=box(t[0]+x,t[1]+y,t[2]+x,t[3]+y)
            receivers.append(dict(id=row['id']+'.tail'+str(i),owner=row['id'],board=row['target_board'],kind='tail',side='B',poly=poly,z=[z-.2-row['tail_projection_mm'],z+.2]))
        if row['mechanical']:
            poly=box(b[0]+x,b[1]+y,b[2]+x,b[3]+y)
            receivers.append(dict(id=row['id']+'.through_mount',owner=row['id'],board=row['target_board'],kind='mount',side='B',poly=poly,z=[2.8,z+.2]))
    for i,(x,y) in enumerate(c['power_mount_centres']):
        for side,z in [('F',[c['power_Z']-.2+1.44,c['power_Z']+.2+1.76+2.31]),('B',[2.8,c['power_Z']+.2])]:
            receivers.append(dict(id=f'NEW_H{i}_{side}',owner=f'NEW_H{i}',board='power_protection',kind='mount',side=side,poly=Point(x,y).buffer(3.6,quad_segs=32),z=z))
        if not polys['power_protection'].buffer(-.5).covers(Point(x,y).buffer(3.6)):issues.append(['mount_edge',i])
    # Broad-phase tree only chooses pairs. Exact continuous intersections decide.
    shapes=[r['poly'] for r in receivers];tree=STRtree(shapes);same=[];cross=[];ctx=[];floor=[]
    for i,a in enumerate(receivers):
        if a['kind']!='mount' and a['z'][0]<3.05-1e-8:floor.append(a['id'])
        for j in tree.query(a['poly'].buffer(.3,join_style=2)):
            if j<=i:continue
            b=receivers[int(j)]
            if a['owner']==b['owner']:continue
            if a['board']==b['board']:
                if a['side']!=b['side']:continue
                margin=.3
            else:
                margin=.25
                if min(a['z'][1]+margin,b['z'][1])-max(a['z'][0]-margin,b['z'][0])<=1e-8:continue
            if a['poly'].buffer(margin,join_style=2).intersection(b['poly']).area>1e-8:
                (same if a['board']==b['board'] else cross).append([a['id'],b['id']])
        for q in contexts:
            if min(a['z'][1]+.25,q['z'][1])-max(a['z'][0]-.25,q['z'][0])>1e-8 and a['poly'].buffer(.25,join_style=2).intersection(box(*q['xy'])).area>1e-8:
                ctx.append([a['id'],q['id']])
    # Verify fixed exterior inlet PCB poses; every pin mapping is still present.
    exterior=[]
    for row in c['parts']:
        if row['role']=='input_protection' and row['ref'] in ['J1','S1']:
            exterior.append(dict(ref=row['ref'],xy_unchanged=p['poses'][row['id']]['xy']==row['source_world_xy'],board_underside_Z_unchanged=c['power_Z']==7.9))
    result=dict(source_sha256={str(q.relative_to(REPO)):sha(q) for q in [Path(__file__),folder/'capture.json',folder/'placement.json',ROOT/'staging/assembly-layout-04/allocation.json']},
        checked_source_bindings=sources,source_errors=issues,part_counts=dict(Counter(r['role'] for r in c['parts'])),
        all_known_parts_present=len(p['poses'])==len(c['parts']),electrical_parts=sum(not r['mechanical'] for r in c['parts']),
        same_board_receiver_findings=same,cross_board_receiver_findings=cross,context_findings=ctx,floor_findings=floor,
        exterior_inlet_pose_checks=exterior,total_receivers=len(receivers),
        complete_fit_verified=False,native_DRC_run=False,electrical_routing_qualified=False,fabrication_released=False)
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--label',default='two-board-placement-04');args=ap.parse_args()
    folder=ROOT/'staging'/args.label;target=folder/'independent-placement-audit.json';assert not target.exists()
    result=audit(folder);target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','part_counts']},indent=2))
