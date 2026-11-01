"""Read-only clearance precheck for a small control-layout PCB extension.

Uses captured native meshes and current NF265/FPC91 receiving boxes. This is a
nominal placement screen, not a new native Boolean or physical qualification.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box

from hardware.electronics.rail_disconnect.revision28.u28_band_mesh_screen import contains, triangles

from .route_e28 import WORK, sha

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]


def clip_z(points,height,above):
    result=[]
    for p,q in zip(points,points[1:]+points[:1]):
        pin=p[2]>=height if above else p[2]<=height
        qin=q[2]>=height if above else q[2]<=height
        if pin:
            result.append(p)
        if pin!=qin:
            t=(height-p[2])/(q[2]-p[2])
            result.append([p[i]+t*(q[i]-p[i]) for i in range(3)])
    return result


def mesh_intersections(ts,region,zlow,zhigh):
    x0,y0,x1,y1=region.bounds
    mask=((ts[:,:,0].max(axis=1)>=x0)&(ts[:,:,0].min(axis=1)<=x1)
          &(ts[:,:,1].max(axis=1)>=y0)&(ts[:,:,1].min(axis=1)<=y1)
          &(ts[:,:,2].max(axis=1)>zlow)&(ts[:,:,2].min(axis=1)<zhigh))
    count=0
    for triangle in ts[mask]:
        points=clip_z(triangle.tolist(),zlow,True)
        if not points:
            continue
        points=clip_z(points,zhigh,False)
        xy=list(dict.fromkeys((p[0],p[1]) for p in points))
        if not xy:
            continue
        if len(xy)==1:
            projected=Point(xy[0])
        elif len(xy)==2:
            projected=LineString(xy)
        else:
            projected=Polygon(xy)
            if projected.area<1e-12:
                projected=LineString(xy)
            elif not projected.is_valid:
                projected=projected.buffer(0)
        if region.intersects(projected):
            count+=1
    point=region.representative_point()
    inside=contains(ts,[point.x,point.y,(zlow+zhigh)/2]) if not count else False
    return dict(surface_intersections=count,representative_point_inside=bool(inside),clear=not count and not inside)


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--end-y",type=float,default=171.)
    parser.add_argument("--label",default="control-wing-screen")
    parser.add_argument("--component-inset",type=float,default=1.)
    parser.add_argument("--underside-height",type=float,default=0.)
    args=parser.parse_args()
    assert 165.<args.end_y<=171.
    assert 0<=args.component_inset<=1
    assert 0<=args.underside_height<=1.2
    assert args.label and all(c.isalnum() or c in "-_" for c in args.label)
    out=WORK/"generated"/(args.label+".json")
    assert not out.exists()
    source=WORK/"generated/eight-layer-followup/rail_disconnect.kicad_pcb"
    context=REPO/"hardware/cad/a12/interface.json"
    datum=json.loads(context.read_text())["disconnect_terminals"]["board_datum"]
    assert datum==[8,108.5,5.0]
    cp=REPO/"hardware/cad/a12/thermal/enlarged_base_pot/generated"
    paths=[cp/(name+".stl") for name in ("eb_carrier_geometry","eb_attachment_geometry","eb_metal_geometry",
        "eb_interface_geometry","eb_retained_power_review","ei_controls_geometry","ei_all_ports_geometry",
        "ei_trill_frontbay_geometry","ps_body_geometry","ps_stack","cp_pot_hardware_review")]
    model_path=REPO/"hardware/cad/a12/enclosure_growth/nf265_fpc91/generated/model.json"
    receiving=json.loads(model_path.read_text())
    region=box(13,163,83,args.end_y).buffer(-1e-5)
    # Avoid counting the deliberate join at the old PCB edge as a collision.
    inset=args.component_inset
    targets={"PCB":(region,5.00001,6.61999),"component_space":(box(13+inset,163+inset,83-inset,args.end_y-inset).buffer(-1e-5),6.62001,8.62)}
    if args.underside_height:
        targets["underside_component_space"]=(region,5.-args.underside_height,4.99999)
    result={name:{} for name in targets}
    sources={str(p):sha(p) for p in [source,context,model_path,Path(__file__),*paths]}
    for path in paths:
        ts=triangles(path)
        for name,(area,lo,hi) in targets.items():
            result[name][path.name]=mesh_intersections(ts,area,lo,hi)
    boxes=[]
    for rows in (receiving["boxes"],receiving["mates"],receiving["tails"]):
        for row in rows:
            name,x,y,z,dx,dy,dz=row
            for target,(area,lo,hi) in targets.items():
                if z+dz>lo and z<hi and area.intersects(box(x,y,x+dx,y+dy).buffer(.45)):
                    boxes.append(dict(target=target,id=name,receiving_box=row))
    synthetic=np.array([[[20.,165.,4.],[20.,166.,8.],[21.,165.,8.]]])
    control=mesh_intersections(synthetic,region,5.,6.62)
    assert control["surface_intersections"]>0
    assert contains(triangles(paths[0]),[133,156,1])
    assert all(sha(Path(p))==value for p,value in sources.items())
    out.write_text(json.dumps(dict(source_sha256=sources,board_frame_mm=datum,
        proposed_extension_local_xy_mm=[5,54.5,75,args.end_y-108.5],
        height_growth_ratio=(args.end_y-108.5)/54.5,
        target_bounds_world_mm={n:dict(xy_bounds=list(p.bounds),z_bounds=[lo,hi]) for n,(p,lo,hi) in targets.items()},
        original_housing_dimensions_unchanged=True,nominal_mesh_checks=result,
        current_NF_FPC_receiving_box_hits=boxes,synthetic_crossing_control=control,
        source_geometry_unchanged=True,full_native_receiving_and_airflow_checks_pending=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print({k:[p for p,r in rows.items() if not r["clear"]] for k,rows in result.items()},"receiving-box hits",boxes,flush=True)


if __name__=="__main__":
    run()
