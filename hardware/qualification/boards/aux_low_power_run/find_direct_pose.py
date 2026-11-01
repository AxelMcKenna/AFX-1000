"""Read-only search for a receiver pocket with actual direct terminal access."""

import json
import math

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

from hardware.electronics.common.sexpr import a, children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

from .place_receiver import SOURCE, WORK, pose_shape, sha


def run():
    out = WORK / "generated/direct-placement-search.json"
    assert not out.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(source.read_text())
    pads_path = SOURCE / "generated/native-pads.json"
    native = json.loads(pads_path.read_text())
    netnames = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree,"net")}
    copper = {side: [] for side in ("F","B")}
    courts = {side: [] for side in copper}
    terminals = {side: {} for side in copper}
    for pad in native["pad_polygons"]:
        for side in copper:
            for p in pad["layers"].get(side+".Cu",[]):
                copper[side].append((pad["net"], Polygon(p["outer"],p["holes"])))
                terminals[side].setdefault(pad["net"],[]).append(pad["position_mm"])
    for fp in children(tree,"footprint"):
        side = str(first(fp,"layer")[1])[0]
        try:
            courts[side].append(box(*courtyard(fp,side+".CrtYd")))
        except AssertionError:
            pass
    for via in children(tree,"via"):
        xy = tuple(map(float,first(via,"at")[1:3]))
        net = netnames[str(first(via,"net")[1])]
        shape = Point(xy).buffer(float(first(via,"size")[1])/2+.002)
        for side in copper:
            copper[side].append((net,shape))
            terminals[side].setdefault(net,[]).append(xy)
    for track in children(tree,"segment"):
        if first(track,"uuid")[1] == "eeee037d-599a-597f-a323-0470f21ba53e":
            continue
        layer = str(first(track,"layer")[1])
        if layer not in ("F.Cu","B.Cu"):
            continue
        xy = [tuple(map(float,first(track,k)[1:3])) for k in ("start","end")]
        copper[layer[0]].append((netnames[str(first(track,"net")[1])],
                                  LineString(xy).buffer(float(first(track,"width")[1])/2+.002)))
    for zone in children(tree,"zone"):
        if children(zone,"keepout") and children(zone,"polygon"):
            shape = Polygon([tuple(map(float,p[1:3])) for p in first(first(zone,"polygon"),"pts")[1:]])
            for side in copper:
                copper[side].append(("KEEPOUT",shape))
    all_copper = {side: prep(unary_union([s for _,s in rows]).buffer(.202)) for side,rows in copper.items()}
    all_courts = {side: prep(unary_union(rows).buffer(.2)) for side,rows in courts.items()}
    nets = {"2":"POWER_RUN","3":"AGND","4":"RUN_BUFFERED","5":"V2V5_AUX"}
    foreign = {(side,net):prep(unary_union([s for n,s in copper[side] if n != net]).buffer(.322))
               for side in copper for net in nets.values()}
    # The old board still names the U28 input POWER_RUN; its final branch is
    # excluded above and U28.1 itself is excluded for the new buffered output.
    u28 = next(p for p in native["pad_polygons"] if p["ref"]=="U28" and p["pin"]=="1")
    foreign["B","RUN_BUFFERED"] = prep(unary_union([
        shape for net,shape in copper["B"]
        if not (net=="POWER_RUN" and shape.intersects(Point(u28["position_mm"])))
    ]).buffer(.322))
    libs = {"U43":WORK/"RMX_E28.pretty/AX03_DCK0005A.kicad_mod",
            "C86":WORK/"RMX_E28.pretty/AX03_C0603.kicad_mod"}
    shapes, lands = {}, {}
    for name,path in libs.items():
        fp = read_sexpr(path.read_text())
        lands[name] = {}
        for p in children(fp,"pad"):
            x,y = map(float,first(p,"at")[1:3])
            w,h = map(float,first(p,"size")[1:3])
            lands[name][str(p[1])] = (Point(x,y),box(x-w/2,y-h/2,x+w/2,y+h/2))
        fp.append([a("at"),a(0),a(0),a(0)])
        shapes[name] = (unary_union([s for _,s in lands[name].values()]),box(*courtyard(fp,"F.CrtYd")))
    ranked, valid = [], 0
    for side in ("B",):
        for angle in (0,90,180,270):
            theta = math.radians(-angle)
            dx,dy = 3.6,.65
            offset = (dx*math.cos(theta)-dy*math.sin(theta),dx*math.sin(theta)+dy*math.cos(theta))
            for ix in range(228,402):
                for iy in range(274,307):
                    x,y = ix/2,iy/2
                    poses = {"U43":(x,y,angle,side),"C86":(x+offset[0],y+offset[1],angle,side)}
                    polys = {n:(pose_shape(shapes[n][0],*p),pose_shape(shapes[n][1],*p)) for n,p in poses.items()}
                    if any(all_copper[side].intersects(p) or all_courts[side].intersects(c)
                           or not box(101,101,245,153.5).contains(c) for p,c in polys.values()):
                        continue
                    if polys["U43"][1].distance(polys["C86"][1]) < .2:
                        continue
                    valid += 1
                    paths = {}
                    for pin,net in nets.items():
                        start = tuple(pose_shape(lands["U43"][pin][0],*poses["U43"]).coords[0])
                        choices = [u28["position_mm"]] if net=="RUN_BUFFERED" else terminals[side].get(net,[])
                        for end in sorted(choices,key=lambda p:math.dist(start,p))[:24]:
                            line = LineString([start,end])
                            if foreign[side,net].intersects(line):
                                continue
                            other_new = []
                            for name,rows in lands.items():
                                for p,(_,shape) in rows.items():
                                    pn = nets.get(p) if name=="U43" else ("V2V5_AUX" if p=="1" else "AGND")
                                    if pn != net:
                                        other_new.append(pose_shape(shape,*poses[name]))
                            if unary_union(other_new).buffer(.322).intersects(line):
                                continue
                            paths[net] = dict(start=start,end=end,length_mm=line.length)
                            break
                    ranked.append(dict(direct_connections=len(paths),poses=poses,paths=paths))
        print(side,"clear pockets",valid,flush=True)
    ranked.sort(key=lambda r:(-r["direct_connections"],sum(p["length_mm"] for p in r["paths"].values())))
    out.write_text(json.dumps(dict(source_sha256=sha(source),recipe_sha256=sha(__import__("pathlib").Path(__file__)),
                                  clear_pockets=valid, best=ranked[:20], source_unchanged=True),indent=2)+"\n")
    print([(r["direct_connections"],r["poses"]) for r in ranked[:3]],flush=True)


if __name__=="__main__":
    run()
