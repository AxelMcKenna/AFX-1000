"""Functional-anchor placement using actual captured courtyard geometry."""

import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
GAP=.2
SIZE=(66.,34.)


def overlap(a,b,gap=0):
    return a[0]<b[0]+b[2]+gap-1e-8 and b[0]<a[0]+a[2]+gap-1e-8 and a[1]<b[1]+b[3]+gap-1e-8 and b[1]<a[1]+a[3]+gap-1e-8


def rotated(b,angle):
    points=[]
    for x in (b[0],b[2]):
        for y in (b[1],b[3]):
            points.append({0:(x,y),90:(y,-x),180:(-x,-y),270:(-y,x)}[angle])
    return [min(x[0] for x in points),min(x[1] for x in points),max(x[0] for x in points),max(x[1] for x in points)]


def cut(free,used):
    result=[]
    for b in free:
        if not overlap(b,used):
            result.append(b);continue
        x,y,w,h=b;ux,uy,uw,uh=used
        for q in [[x,y,ux-x,h],[ux+uw,y,x+w-ux-uw,h],[x,y,w,uy-y],[x,uy+uh,w,y+h-uy-uh]]:
            if q[2]>1e-8 and q[3]>1e-8:result.append(q)
    return [p for i,p in enumerate(result) if not any(i!=j and q[0]<=p[0]+1e-8 and q[1]<=p[1]+1e-8 and q[0]+q[2]>=p[0]+p[2]-1e-8 and q[1]+q[3]>=p[1]+p[3]-1e-8 and (p!=q or j<i) for j,q in enumerate(result))]


# Actual footprint anchors/angles; all component bodies remain FRONT.
ANCHORS={
 "J201":(5,17,0),"J202":(5,5,0),"J203":(5,27,0),
 "U201":(18,6.5,0),"U301":(18,27.5,0),
 "C203":(12,12.5,0),"C303":(12,21.1,0),
 "C201":(15.5,3.3,0),"C202":(21,3.3,0),"C301":(15.5,30.7,0),"C302":(21,30.7,0),
 "R201":(22,8.3,0),"R202":(20.4,11,0),"R203":(20.4,13.3,0),
 "R301":(22,25.7,0),"R302":(20.4,23.2,0),"R303":(20.4,20.9,0),
 "U3":(24.6,28,0),"C5":(25.85,30.7,0),
 "J4":(29,5.5,0),"U15":(25.5,14.5,0),
 "U2":(34,14,180),"C1":(32.5,18.4,0),"C2":(39,14.4,90),"C3":(31.3,10.8,0),
 "U1":(48.5,15,270),"X1":(48.5,5.5,180),"C20":(51.8,9.15,0),"C21":(47.6,9.15,0),"C4":(55.7,14.5,90),
 "J3":(60,7.5,90),"J2":(58.5,28.1,0),"J5":(47.7,25,0),
 "C23":(50,20.3,0),"C22":(55,20.3,0),"R23":(53.2,23.35,90),"R21":(56,23.35,90),"R22":(60,12.5,0),
 "U4":(34,22,0),"C6":(30.1,22.5,270),"C7":(33.1,26.6,270),
 "U6":(39.7,24,0),"C9":(38.7,19.8,90),"C10":(41.4,19.8,90),
 "U7":(35.9,25.5,0),"C11":(37,29.2,270),
 "U8":(37,5,0),"C12":(37.5,8.1,180),
 "U11":(36.7,10.7,0),"C16":(40.8,10.7,0),
 "U5":(42,27.4,90),"C8":(42,30.7,0),
 "U9":(25.2,24.5,0),"U10":(27.8,27.7,0),
 "U14":(27,20.5,0),"R1":(21,17,0),"R2":(28.9,17.5,90),
 "U16":(45.8,20.5,0),"C24":(44.5,25.9,270),
 "U12":(33.4,30.2,0),"C17":(30.6,29,90),
 "U13":(59.2,17.6,0),"C18":(61,20.5,0),
}
FOCUS={"C13":(25,22),"C14":(24,24),"C15":(28,30),"C19":(27,22),
 "R3":(33,29),"R4":(45,20),"R5":(35,22),"R6":(52.8,28.5),"R7":(35,24),"R8":(36,25),"R9":(36,10),
 "R10":(27,27),"R11":(25,23),"R12":(24,25),"R13":(27,20),"R14":(24,26),"R15":(26,27),"R16":(25,28),"R17":(27,28),"R20":(60,23.5),"R24":(35,17)}


def place(rows,mode):
    by={r["ref"]:r for r in rows}
    free=[[2.,2.,62.,30.]]
    placed={}
    def add(ref,x,y,angle):
        nonlocal free
        b=rotated(by[ref]["courtyard_bbox_mm"],angle)
        box=[x+b[0],y+b[1],b[2]-b[0],b[3]-b[1]]
        if box[0]<2-1e-8 or box[1]<2-1e-8 or box[0]+box[2]>64+1e-8 or box[1]+box[3]>32+1e-8:
            raise ValueError((ref,"edge",box))
        bad=[r for r,p in placed.items() if overlap(box,p["courtyard_rect_mm"],GAP)]
        if bad:raise ValueError((ref,"courtyard",bad,box))
        placed[ref]=dict(anchor_mm=[x,y],rotation_deg=angle,courtyard_rect_mm=box)
        free=cut(free,[box[0]-GAP,box[1]-GAP,box[2]+2*GAP,box[3]+2*GAP])
    for ref,(x,y,angle) in ANCHORS.items():add(ref,x,y,angle)
    remaining=[r for r in rows if r["ref"] not in placed]
    remaining.sort(key=lambda r:(r["ref"].startswith("C"),r["courtyard_area_mm2"]),reverse=True)
    for row in remaining:
        target=FOCUS.get(row["ref"],(34,18))
        choices=[]
        for angle in (0,90,180,270):
            b=rotated(row["courtyard_bbox_mm"],angle);w,h=b[2]-b[0],b[3]-b[1]
            for fx,fy,fw,fh in free:
                if w<=fw+1e-8 and h<=fh+1e-8:
                    # Both near-target and corner choices; no arbitrary half-pad shifts.
                    for x,y in {(fx,fy),(fx+fw-w,fy),(fx,fy+fh-h),(max(fx,min(fx+fw-w,target[0]-w/2)),max(fy,min(fy+fh-h,target[1]-h/2)))}:
                        distance=math.dist((x+w/2,y+h/2),target)
                        score=distance*(1 if mode==0 else .2)+min(fw-w,fh-h)*(1 if mode==1 else .05)
                        choices.append((score,y,x,angle,x-b[0],y-b[1]))
        if not choices:return None, row["ref"]
        *_,angle,x,y=min(choices)
        add(row["ref"],x,y,angle)
    return placed,None


def main():
    rows=json.loads((ROOT/"generated/footprint-inventory.json").read_text())["rows"]
    attempts=[]
    for mode in range(2):
        try:p,failed=place(rows,mode)
        except ValueError as error:
            (ROOT/"generated/placement-failure.json").write_text(json.dumps(dict(error=str(error)),indent=2)+"\n")
            raise
        attempts.append(dict(mode=mode,failed=failed))
        if p is not None:break
    (ROOT/"generated/packing-attempts.json").write_text(json.dumps(attempts,indent=2)+"\n")
    if p is None:raise ValueError("Unplaced: "+failed)
    out=dict(placements=p,board_mm=[66,34,1.6],world_datum_component_face_mm=[14,180.5,5.5],
        world_mapping="localX→+worldX;localY→+worldZ;FRONTparts→−worldY;PCB/backtails→+worldY",
        edge_margin_mm=2,courtyard_gap_mm=GAP,parts=len(p),
        electrical_anchor_review_complete=False, mechanical_fit_verified=False, mounting_implemented=False,
        backtail_receiving_max_mm=1, actual_THT_lead_trimming_required=True,
        physical_qualified=False,fabrication_released=False)
    (ROOT/"generated/placement.json").write_text(json.dumps(out,indent=2)+"\n")
    print("Placed",len(p),"actualcourtyardswithin66x34/2mmedges/.2gaps; notphysicalfit")


if __name__=="__main__":main()
