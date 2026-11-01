"""Local surface escapes into actual same-net inner-plane copper."""

import json
import math
import uuid
from pathlib import Path

from shapely.geometry import LineString, Point

from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_layers import LayerScreen
from hardware.fabrication.route_nf_surface import candidate_paths, shape

ROOT = Path(__file__).resolve().parent
CAPTURE = ROOT/"staging/bypass-routing-inputs-37/capture.json"
OUTPUT = ROOT/"staging/bypass-plane-stitches-01"


def run():
    assert not OUTPUT.exists()
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(Path(p)) == digest for p,digest in capture["source_sha256"].items())
    source = next(Path(p) for p in capture["source_sha256"] if p.endswith(".kicad_pcb"))
    board = read_sexpr(source.read_text())
    original, original_count = sexpr(board),len(board)
    objects = {p["uuid"]:p for p in capture["objects"]}
    planes = {z["net"]:(z["layer"],shape(z["polygons"])) for z in capture["zones"] if not z["keepout"]}
    screen = LayerScreen(capture)
    offsets = sorted((math.hypot(x,y),x,y) for x in range(-30,31) for y in range(-30,31) if .5 <= math.hypot(x,y)*.1 <= 3)
    results = []
    for key,identifiers in capture["groups"].items():
        net = objects[identifiers[0]]["net"]
        if net not in planes:
            continue
        layer,plane = planes[net]
        connected = any(layer in objects[i]["layers"] and
            shape(objects[i]["layers"][layer]).intersection(plane).area > 1e-8 for i in identifiers)
        if connected:
            continue
        contacts = set()
        for uid in identifiers:
            item = objects[uid]
            for face in ("F.Cu","B.Cu"):
                if face not in item["layers"]:
                    continue
                for xy in [item["position_mm"]]+([item["end_mm"]] if "end_mm" in item else []):
                    if plane.distance(Point(xy)) <= 3:
                        contacts.add((face,tuple(xy)))
        accepted = None
        checks = 0
        for face,start in sorted(contacts,key=lambda c: (c[0] != "F.Cu",objects[identifiers[0]]["kind"] != "PAD")):
            origin = tuple(round(v/.1) for v in start)
            for _,dx,dy in offsets:
                target = (round((origin[0]+dx)*.1,6),round((origin[1]+dy)*.1,6))
                if not plane.covers(Point(target)):
                    continue
                checks += 1
                if checks > 2000:
                    break
                if not screen.via_legal(net,target):
                    continue
                for path in candidate_paths(start,target):
                    path = [p for i,p in enumerate(path) if i == 0 or p != path[i-1]]
                    if screen.legal(net,face,path):
                        accepted = face,path,target
                        break
                if accepted:
                    break
            if accepted or checks > 2000:
                break
        if not accepted:
            results.append(dict(net=net,group=key,connected=False,reason="no bounded local plane escape"))
            continue
        face,path,target = accepted
        new_via = not any(n == net and math.dist(xy,target) < 1e-7 for n,xy in screen.vias+screen.new_vias)
        for start,end in zip(path,path[1:]):
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E11:stitch:{sha(CAPTURE)}:{net}:{face}:{start}:{end}"))
            board.append([a("segment"),[a("start"),*start],[a("end"),*end],[a("width"),.2],
                          [a("layer"),face],[a("net"),net],[a("uuid"),ident]])
        if new_via:
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E11:via:{sha(CAPTURE)}:{net}:{target}"))
            board.append([a("via"),[a("at"),*target],[a("size"),.65],[a("drill"),.3],
                [a("layers"),"F.Cu","B.Cu"],[a("tenting"),[a("front"),a("yes")],[a("back"),a("yes")]],
                [a("net"),net],[a("uuid"),ident]])
            screen.new_vias.append((net,target))
        screen.added.append((net,face,LineString(path)))
        results.append(dict(net=net,group=key,connected=True,face=face,points_mm=path,plane_layer=layer,new_via=new_via))
        print(net,"local plane stitch",target,flush=True)
    assert sexpr(board[:original_count]) == original
    OUTPUT.mkdir()
    pcb = OUTPUT/source.name
    pcb.write_text(sexpr(board)+"\n")
    inputs = (source,CAPTURE,Path(__file__),ROOT/"route_nf_layers.py",ROOT/"route_nf_surface.py")
    (OUTPUT/"construction.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        candidate_PCB_sha256=sha(pcb),results=results,added_segments=len(children(board,"segment"))-len(children(read_sexpr(original),"segment")),
        added_vias=len(screen.new_vias),original_authored_geometry_exact=True,
        targets_actual_same_net_filled_planes=True,native_checks_pending=True,
        power_noise_and_stencil_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Local plane routes",sum(r["connected"] for r in results),"of",len(results),flush=True)


if __name__ == "__main__":
    run()
