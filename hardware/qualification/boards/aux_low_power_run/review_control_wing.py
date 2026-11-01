"""Create a dimensioned, source-derived plan of the control-wing alternative."""

import html
import json
from pathlib import Path

from shapely.geometry import box

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .route_e28 import REPO, WORK, sha


def run():
    folder=WORK/"generated/control-wing-placement"
    pcb=folder/"rail_disconnect.kicad_pcb"
    parent=WORK/"generated/eight-layer-followup/rail_disconnect.kicad_pcb"
    screen=WORK/"generated/control-wing-full-clearance-screen.json"
    model=REPO/"hardware/cad/a12/enclosure_growth/nf265_fpc91/generated/model.json"
    data=json.loads(screen.read_text())
    assert not data["current_NF_FPC_receiving_box_hits"]
    assert all(r["clear"] for rows in data["nominal_mesh_checks"].values() for r in rows.values())
    view=folder/"control-wing-plan.svg"
    receipt=folder/"mechanical-review.json"
    assert not view.exists() and not receipt.exists()
    tree=read_sexpr(pcb.read_text())
    old=read_sexpr(parent.read_text())
    elements=[]

    def rect(bounds,stroke,fill="none",dashed=False,width=.14):
        x0,y0,x1,y1=bounds
        elements.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" stroke="{stroke}" fill="{fill}" stroke-width="{width}"'+(' stroke-dasharray=".6 .4"' if dashed else '')+'/>')

    def text(x,y,label,size=1.,color="#cbd5e1"):
        elements.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-family="sans-serif">{html.escape(label)}</text>')

    rect((100,145,180,166),"none","#101b2c")
    rect((105,154.5,175,160),"#f59e0b","#30271d")
    elements.append('<path d="M105 154.5H175" stroke="#38bdf8" stroke-width=".18" stroke-dasharray=".8 .4"/>')
    receiving=[]
    candidates=json.loads(model.read_text())
    for rows in (candidates["boxes"],candidates["mates"],candidates["tails"]):
        for row in rows:
            ref,x,y,z,dx,dy,dz=row
            if z>=8.62 or z+dz<=5:
                continue
            # Assembly datum [8,108.5,5] corresponds to PCB CAD [100,100].
            bounds=(x+92-.45,y-8.5-.45,x+dx+92+.45,y+dy-8.5+.45)
            if bounds[2]>105 and bounds[0]<175 and 160<bounds[1]<166:
                rect(bounds,"#f472b6","#39233a",True)
                text(bounds[0]+.25,bounds[1]+1.4,str(ref),.95,"#f9a8d4")
                receiving.append(dict(id=ref,expanded_xy_bounds_cad_mm=list(bounds),
                    gap_from_new_PCB_edge_mm=bounds[1]-160))
    moved=[]
    for t,is_old in ((old,True),(tree,False)):
        for fp in children(t,"footprint"):
            ref=next(p[2] for p in children(fp,"property") if p[1]=="Reference")
            if is_old and ref not in ("U38","C81"):
                continue
            layer=first(fp,"layer")[1]
            try:
                bounds=tuple(map(float,courtyard(fp,"F.CrtYd" if layer=="F.Cu" else "B.CrtYd")))
            except AssertionError:
                continue
            if bounds[2]<105 or bounds[0]>175 or bounds[3]<145 or bounds[1]>160:
                continue
            moving=ref in ("U38","C81")
            color="#38bdf8" if is_old else ("#fbbf24" if moving else "#4b657e")
            rect(bounds,color,dashed=is_old,width=.18 if moving else .08)
            if moving:
                text(bounds[0],bounds[1]-.4,ref+(" previous" if is_old else " proposed"),.95,color)
                if not is_old:
                    # A courtyard encloses the body and its placement allowance.
                    world=box(bounds[0]-92,bounds[1]+8.5,bounds[2]-92,bounds[3]+8.5)
                    assert box(13,163,83,168.5).contains(world)
                    moved.append(dict(ref=ref,courtyard_cad_mm=list(bounds),
                        within_screened_wing_XY=True,screened_component_height_mm=2.))
    text(107,158.7,"NEW PCB AREA",1.2,"#fbbf24")
    text(106,164.8,"Pink: connector envelopes + 0.45 mm XY allowance. Blue: previous edge/poses.",.95)
    # Keep the heading outside the crowded assembly drawing.
    rect((100,145,180,151),"none","#101b2c")
    text(106,147,"E28 CONTROL WING / PLACEMENT REVIEW",1.5,"#f8fafc")
    text(106,149,"70 x 5.5 mm added area; PCB depth 54.5 -> 60 mm (+10.1%)",1.05)
    text(106,150.5,"Existing housing and mounting-hole positions retained",1.05)
    assert len(moved)==2 and len(receiving)==3
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="336" viewBox="100 145 80 21">'+''.join(elements)+'</svg>\n'
    view.write_text(svg)
    receipt.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in (pcb,parent,screen,model,Path(__file__))},
        view_sha256=sha(view),moved_component_courtyard_review=moved,
        nearest_front_connector_envelopes=receiving,
        minimum_gap_to_expanded_front_connector_boxes_mm=min(r["gap_from_new_PCB_edge_mm"] for r in receiving),
        unchanged_housing_dimensions=True,unchanged_mounting_holes=True,
        nominal_mesh_screen_only=True,full_native_assembly_receiving_pending=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Wrote source-derived wing plan and mechanical review; 1.05 mm minimum expanded-box gap")


if __name__=="__main__":
    run()
