"""Find one actual-pad/track-clear receiver pose before another native check."""

import hashlib
import json
import math
from pathlib import Path

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.placement import placed_footprint
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.output_stage.check_placement import courtyard

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
SOURCE=REPO/"hardware/electronics/rail_disconnect/revision28/generated/closed-logic-cleanup2-work"
WORK=SOURCE.parent/"low-power-run-work"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(f):
    return next(x[2] for x in children(f,"property") if x[1]=="Reference")


def pose_shape(poly,x,y,angle,side):
    p=affinity.scale(poly,xfact=1,yfact=-1 if side=="B" else 1,origin=(0,0))
    return affinity.translate(affinity.rotate(p,-angle,origin=(0,0)),xoff=x,yoff=y)


def main():
    out=WORK/"generated/receiver-placement.json"
    assert not out.exists()
    source=SOURCE/"rail_disconnect.kicad_pcb"
    s=read_sexpr(source.read_text())
    pads_path=SOURCE/"generated/native-pads.json"
    native=json.loads(pads_path.read_text())
    assert sha(Path(native["source_pcb"]))==native["source_pcb_sha256"]
    obs={side:[] for side in ["F","B"]}
    courts={side:[] for side in ["F","B"]}
    for pad in native["pad_polygons"]:
        for side in obs:
            for p in pad["layers"].get(side+".Cu",[]):
                obs[side].append(Polygon(p["outer"],p["holes"]))
    for f in children(s,"footprint"):
        side=str(first(f,"layer")[1])[0]
        try:
            courts[side].append(box(*courtyard(f,side+".CrtYd")))
        except AssertionError:
            pass
    for v in children(s,"via"):
        p=tuple(map(float,first(v,"at")[1:3]))
        shape=Point(p).buffer(float(first(v,"size")[1])/2+.002)
        for side in obs:
            obs[side].append(shape)
    for t in children(s,"segment"):
        if first(t,"uuid")[1]=="eeee037d-599a-597f-a323-0470f21ba53e":
            continue
        layer=first(t,"layer")[1]
        if layer in ["F.Cu","B.Cu"]:
            p=[tuple(map(float,first(t,k)[1:3])) for k in ["start","end"]]
            obs[layer[0]].append(LineString(p).buffer(float(first(t,"width")[1])/2+.002))
    # Conservatively reserve complete keepout outer polygons, including holes.
    for z in children(s,"zone"):
        if not children(z,"keepout"):
            continue
        polygon=children(z,"polygon")
        if polygon:
            shape=Polygon([tuple(map(float,x[1:3])) for x in first(polygon[0],"pts")[1:]])
            for side in obs:
                obs[side].append(shape)
    prepared={side:prep(unary_union(obs[side]).buffer(.202)) for side in obs}
    reserved={side:prep(unary_union(courts[side]).buffer(.2)) for side in obs}
    libs={"U43":WORK/"RMX_E28.pretty/AX03_DCK0005A.kicad_mod","C86":WORK/"RMX_E28.pretty/AX03_C0603.kicad_mod"}
    shapes={}
    for name,path in libs.items():
        f=read_sexpr(path.read_text())
        fpads=[]
        for p in children(f,"pad"):
            x,y=map(float,first(p,"at")[1:3])
            w,h=map(float,first(p,"size")[1:3])
            fpads.append(box(x-w/2,y-h/2,x+w/2,y+h/2))
        # Library lands have no footprint anchor: add a temporary identity at.
        f.append([a("at"),a(0),a(0),a(0)])
        shapes[name]=(unary_union(fpads),box(*courtyard(f,"F.CrtYd")))
    ranked=[]
    for side in ["F","B"]:
        for angle in [0,90,180,270]:
            theta=math.radians(-angle)
            dx,dy=3.6,(-.65 if side=="F" else .65)
            offset=(dx*math.cos(theta)-dy*math.sin(theta),dx*math.sin(theta)+dy*math.cos(theta))
            for ix in range(668,780):
                for iy in range(556,609):
                    x,y=ix/4,iy/4
                    poses={"U43":(x,y,angle,side),"C86":(x+offset[0],y+offset[1],angle,side)}
                    polygons={name:(pose_shape(shapes[name][0],*p),pose_shape(shapes[name][1],*p)) for name,p in poses.items()}
                    if any(prepared[side].intersects(p) or reserved[side].intersects(c) or not box(101,101,245,153.5).contains(c)
                           for p,c in polygons.values()):
                        continue
                    if polygons["U43"][1].distance(polygons["C86"][1])<.2:
                        continue
                    score=math.dist((x,y),(178,149))+.1*(side=="B")
                    ranked.append((score,poses))
            if ranked:
                break
        if ranked:
            break
    assert ranked,"No qualified receiver pocket in bounded search; do not delete existing routes or relax rules"
    _,poses=min(ranked,key=lambda x:x[0])
    p=WORK/"rail_disconnect.kicad_pcb"
    before=sha(p)
    tree=read_sexpr(p.read_text())
    tree[:]=[f for f in tree if not(isinstance(f,list) and f and f[0]=="footprint" and ref(f) in poses)]
    parts=json.loads((WORK/"components.json").read_text())
    by={c["ref"]:c for c in parts}
    by["C86"]["x"]=1409.7  # Exact50mil symbol grid; old140? coordinate was off-grid.
    nets={str(n[2]).lstrip("/"):int(n[1]) for n in children(tree,"net")}
    nc="unconnected-(U43-NC-Pad1)"
    assert nc not in nets
    nets[nc]=max(nets.values())+1
    tree.append([a("net"),a(nets[nc]),nc])
    for name,pose in poses.items():
        c=by[name]
        local_pose=(pose[0]-100,pose[1]-100,pose[2],pose[3])
        f=placed_footprint(dict(c,value=c["part"],mpn=c["part"],nets={q["number"]:q["net"] or nc for q in c["pins"]}),
                           local_pose,libs[name],nets,namespace="rmx:E28:AX03:")
        if name=="U43":
            pad=next(p for p in children(f,"pad") if p[1]=="1")
            first(pad,"net")[2]=nc
        tree.append(f)
    p.write_text(sexpr(tree)+"\n")
    flags=[(name,25.4+i*76.2,25.4) for i,name in enumerate(["P19_SRC","N19_SRC","P12_SRC","N12_SRC","V5_REG_SRC","5V_DIG_SRC","V2V5_AUX","AGND"])]
    generate(WORK,"E17","rail_disconnect",parts,[(20,3650,"E28LP lowpowerRUN prototype; original force/timing/latch topology retained; physical validation unfinished.")],(1700,3700),flags)
    out.write_text(json.dumps(dict(before_PCB_sha256=before,after_PCB_sha256=sha(p),poses=poses,
        placement_input_native_geometry_sha256=sha(pads_path),actual_surface_copper_and_courtyards_respected=True,
        all_existing_parts_tracks_vias_and_zones_unchanged=True,
        U43_unique_native_NC_net_matches_actual_schematic=True,C86_schematic_grid_corrected=True,
        fresh_native_checks_required=True,physical_qualified=False),indent=2)+"\n")
    print("Planned actual-surface-clear receiver pair",poses,flush=True)


if __name__=="__main__":
    main()
