"""Place DC01 bypass, bulk and current-reference parts beside their owners.

This is a bounded placement screen. Native clearance, local routing, receiving,
PDN and thermal review remain mandatory; distance alone is not qualification.
"""
import argparse,copy,json,math,sys
from pathlib import Path
from shapely.geometry import Polygon,box
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard,transform
from hardware.fabrication.digital_core_layout import pad_box
from hardware.fabrication.audit_candidate import sha,native_evidence_errors

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'staging/digital-placement-native-05'
PLAN=ROOT/'staging/digital-power-cell-plan-01'
OUT=ROOT/'staging/digital-power-cell-placement-01'
ROTATIONS={f'U200{i}':270 for i in range(1,4)}
# ref, owner, pin, same-face intent, maximum pin-centre displacement (project allocation).
TARGETS=[
    *[(f'C{1011+i}','U1001',str(22+i),'B',3.5) for i in range(10)],
    ('R3012','U3001','4','F',3.5),
    *[(f'C200{i}',f'U200{i}','9','B',3.5) for i in range(1,4)],
    *[(f'C{3001+2*i}',f'U{3001+i}','32','F',3.5) for i in range(4)],
    ('C3009','U3005','1','F',3.5),('C3010','U3005','24','F',3.5),
    ('C3011','U3006','6','F',3.5),('C3012','U3007','6','F',3.5),
    *[(f'R{3001+i}',f'U{3001+i}','31','F',3.5) for i in range(4)],
    ('C1002','U1001','39','B',3.5),('C1004','U1001','21','B',3.5),('C1006','U1001','38','B',3.5),
    *[(f'C{3002+2*i}',f'U{3001+i}','32','F',7.0) for i in range(4)],
    ('C1001','U1001','39','B',7.0),('C1003','U1001','21','B',7.0),('C1005','U1001','38','B',7.0),
    ('C2004','U2002','9','B',7.0),('C3013','J1001','1','B',7.0),('C3014','J1001','1','B',7.0),
]

def refs(tree):
    return {next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(tree,'footprint')}

def legal(shape,side,occupied,domain):
    if not domain.covers(shape):return False
    for s,g,gap,label in occupied:
        if s!=side:continue
        if shape.distance(g)<gap-1e-8 or (gap==0 and shape.intersection(g).area>1e-10):return False
    return True


def passive_site(fp,side,target,limit,occupied,domain):
    pads={str(p[1]):p for p in children(fp,'pad')};assert set(pads)=={'1','2'}
    assert all(abs(float(first(p,'at')[2]))<1e-8 for p in pads.values())
    local=copy.deepcopy(fp);first(local,'at')[1:]=[0,0,0]
    bounds=courtyard(local,first(local,'layer')[1][0]+'.CrtYd')
    assert abs(bounds[1]+bounds[3])<1e-8
    px=float(first(pads['1'],'at')[1]);tx,ty=target;choices=[]
    for angle in [0,90,180,270]:
        ca=math.cos(math.radians(angle));sa=math.sin(math.radians(angle))
        xy=[(x*ca+y*sa,-x*sa+y*ca) for x in [bounds[0],bounds[2]] for y in [bounds[1],bounds[3]]]
        b=[min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)]
        for ix in range(math.floor((tx-limit-2)*4),math.ceil((tx+limit+2)*4)+1):
            for iy in range(math.floor((ty-limit-2)*4),math.ceil((ty+limit+2)*4)+1):
                x,y=ix/4,iy/4;dist=math.hypot(x+px*ca-tx,y-px*sa-ty)
                if dist<=limit:choices.append((dist,x,y,angle,b))
    obs=[(g,gap,label) for s,g,gap,label in occupied if s==side];index=STRtree([o[0] for o in obs])
    for dist,x,y,angle,b in sorted(choices,key=lambda r:r[:4]):
        shape=box(b[0]+x,b[1]+y,b[2]+x,b[3]+y)
        if not domain.covers(shape):continue
        if any(shape.distance(obs[int(i)][0])<obs[int(i)][1]-1e-8 or (obs[int(i)][1]==0 and shape.intersection(obs[int(i)][0]).area>1e-10) for i in index.query(shape.buffer(.3))):continue
        return dict(side=side,anchor_mm=[x,y],rotation_deg=angle,planned_pin_distance_mm=dist,courtyard_bounds_mm=list(shape.bounds))
    return None


def plan():
    pcb=SOURCE/'digital_core.kicad_pcb';review=SOURCE/'review.json'
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'),json.loads(review.read_text()))
    tree=read_sexpr(pcb.read_text());fps=refs(tree);original=copy.deepcopy(fps)
    assert not children(tree,'segment') and not children(tree,'via')
    moving={r[0] for r in TARGETS}|set(ROTATIONS);fixed={r:f for r,f in fps.items() if r not in moving}
    domain=Polygon([(0,0),(64,0),(64,3),(104,3),(104,9),(114,9),(114,60),(0,60)]).buffer(-.5)
    occupied=[]
    for ref,fp in fixed.items():
        side=first(fp,'layer')[1][0];occupied.append((side,box(*courtyard(fp,side+'.CrtYd')),.3,ref))
        if ref.startswith('H'):
            x,y=map(float,first(fp,'at')[1:3]);occupied.extend((s,box(x-3.6,y-3.6,x+3.6,y+3.6),.15,ref) for s in ['F','B'])
        for pad in children(fp,'pad'):
            if pad[2]=='thru_hole':occupied.append(('B' if side=='F' else 'F',box(*pad_box(fp,pad,.5)),0,ref+' solder'))
    ic_rows=[];preselected={}
    for i in range(1,4):
        ref=f'U200{i}';cap=f'C200{i}';fp=fps[ref];ox,oy=map(float,first(fp,'at')[1:3]);choices=[]
        for ix in range(8,221):
            for iy in range(8,113):
                x,y=ix/2,iy/2
                if math.dist((x,y),(ox,oy))>110:continue
                for angle in [90,270,0,180]:choices.append((math.dist((x,y),(ox,oy))+.01*(angle!=90),x,y,angle))
        chosen=None;legal_sites=0;nearest=[]
        ic_obs=[(g,gap) for side,g,gap,label in occupied if side=='B'];ic_index=STRtree([g for g,gap in ic_obs])
        for _,x,y,angle in sorted(choices):
            first(fp,'at')[1:]=[x,y,angle];shape=box(*courtyard(fp,'B.CrtYd'))
            if not domain.covers(shape):continue
            if any(shape.distance(ic_obs[int(k)][0])<ic_obs[int(k)][1]-1e-8 or (ic_obs[int(k)][1]==0 and shape.intersection(ic_obs[int(k)][0]).area>1e-10) for k in ic_index.query(shape.buffer(.3))):continue
            legal_sites+=1
            pin=next(p for p in children(fp,'pad') if p[1]=='9');target=transform(fp,first(pin,'at')[1:3])
            site=passive_site(fps[cap],'B',target,3.5,occupied+[('B',shape,.3,ref)],domain)
            if site is None:site=passive_site(fps[cap],'F',target,3.5,occupied+[('B',shape,.3,ref)],domain)
            if site:
                chosen=dict(ref=ref,side='B',anchor_mm=[x,y],rotation_deg=angle,before_anchor_mm=[ox,oy],courtyard_bounds_mm=list(shape.bounds))
                occupied.append(('B',shape,.3,ref));occupied.append((site['side'],box(*site['courtyard_bounds_mm']),.3,cap));preselected[cap]=site;break
        print('Legal IC sites tested',ref,legal_sites,flush=True)
        assert chosen,('No IC/decoupler joint site',ref)
        ic_rows.append(chosen);print('Joint cell',ref,chosen['anchor_mm'],chosen['rotation_deg'],flush=True)
    rows=[]
    for ref,owner,pin,side,limit in TARGETS:
        fp=fps[ref];target=next(p for p in children(fps[owner],'pad') if str(p[1])==pin)
        pads={str(p[1]):p for p in children(fp,'pad')};assert first(pads['1'],'net')[-1]==first(target,'net')[-1]
        target_xy=transform(fps[owner],first(target,'at')[1:3])
        selected=preselected.get(ref) or passive_site(fp,side,target_xy,limit,occupied,domain)
        if selected is None:selected=passive_site(fp,'F' if side=='B' else 'B',target_xy,limit,occupied,domain)
        assert selected,('No local site',ref,owner,pin,limit)
        old_owner=original[owner];old_target=next(p for p in children(old_owner,'pad') if str(p[1])==pin)
        before=math.dist(transform(original[ref],first(pads['1'],'at')[1:3]),transform(old_owner,first(old_target,'at')[1:3]))
        selected.update(ref=ref,owner=owner,owner_pin=pin,before_pin_distance_mm=before,maximum_project_pin_distance_mm=limit)
        if ref not in preselected:occupied.append((selected['side'],box(*selected['courtyard_bounds_mm']),.3,ref))
        rows.append(selected);print(ref,round(before,2),'->',round(selected['planned_pin_distance_mm'],2),'mm',flush=True)
    PLAN.mkdir(exist_ok=False)
    (PLAN/'plan.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,review,Path(__file__),ROOT/'digital_core_layout.py']},placements=rows,IC_placements=ic_rows,
        same_face_courtyard_gap_mm=.3,opposite_THT_solder_reserve_mm=.5,edge_gap_mm=.5,
        local_power_routing_required=True,full_receiving_and_PDN_qualified=False,fabrication_released=False),indent=2)+'\n')

def apply():
    assert sys.platform=='linux'
    import pcbnew
    pp=PLAN/'plan.json';data=json.loads(pp.read_text());assert all(sha(Path(p))==h for p,h in data['source_sha256'].items())
    pcb=SOURCE/'digital_core.kicad_pcb';board=pcbnew.LoadBoard(str(pcb));fps={f.GetReference():f for f in board.GetFootprints()}
    for row in data['IC_placements']:
        f=fps[row['ref']];f.SetOrientationDegrees(row['rotation_deg']);f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in row['anchor_mm']]))
    rows=[]
    for row in data['placements']:
        f=fps[row['ref']]
        if f.IsFlipped()!=(row['side']=='B'):f.Flip(f.GetPosition(),False)
        f.SetOrientationDegrees(row['rotation_deg']);f.SetPosition(pcbnew.VECTOR2I(*[pcbnew.FromMM(x) for x in row['anchor_mm']]))
        target=next(p for p in fps[row['owner']].Pads() if p.GetNumber()==row['owner_pin']);pad=next(p for p in f.Pads() if p.GetNumber()=='1')
        assert pad.GetNetname()==target.GetNetname()
        dist=(pad.GetPosition()-target.GetPosition()).EuclideanNorm()/1e6
        assert abs(dist-row['planned_pin_distance_mm'])<.000003
        rows.append(dict(**row,native_pin_distance_mm=dist))
    OUT.mkdir(exist_ok=False);assert pcbnew.SaveBoard(str(OUT/pcb.name),board)
    (OUT/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [pcb,pp,Path(__file__)]},placements=rows,IC_placements=data['IC_placements'],
        native_review_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Applied',len(rows),'native local placements')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['plan','apply']);args=ap.parse_args();(plan if args.action=='plan' else apply)()
