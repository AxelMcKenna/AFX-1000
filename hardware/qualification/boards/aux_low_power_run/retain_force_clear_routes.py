"""Retain complete logic joins only when foreign filled power is untouched."""

import json
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision26.layout import POWER_NETS

from .route_e28 import WORK, sha


def run():
    base = WORK / "generated/receiver-direct-routes/rail_disconnect.kicad_pcb"
    trial = WORK / "generated/logic-pour-trial/rail_disconnect.kicad_pcb"
    filled = WORK / "generated/native-direct-pose-checked/rail_disconnect.kicad_pcb"
    out = WORK / "generated/force-clear-logic"
    out.mkdir(exist_ok=False)
    tree = read_sexpr(base.read_text())
    original_count, frozen = len(tree), sexpr(tree)
    proposed = read_sexpr(trial.read_text())
    ids = {str(first(n,"uuid")[1]) for kind in ("segment","via") for n in children(tree,kind)}
    names = {str(n[1]):str(n[2]).lstrip("/") for n in children(tree,"net")}
    pours = {}
    for zone in children(read_sexpr(filled.read_text()),"zone"):
        if not children(zone,"net"):
            continue
        net = str(first(zone,"net")[-1]).lstrip("/")
        if net not in POWER_NETS:
            continue
        for poly in children(zone,"filled_polygon"):
            layer = str(first(poly,"layer")[1])
            points = [(float(p[1]),float(p[2])) for p in first(poly,"pts")[1:]]
            pours.setdefault((net,layer),[]).append(Polygon(points).buffer(0))
    pours = {key:unary_union(rows) for key,rows in pours.items()}
    additions = {}
    for kind in ("segment","via"):
        for node in children(proposed,kind):
            if str(first(node,"uuid")[1]) not in ids:
                additions.setdefault(names[str(first(node,"net")[1])],[]).append(node)
    results=[]
    for net,nodes in additions.items():
        hits=[]
        for node in nodes:
            if node[0]=="segment":
                points=[tuple(map(float,first(node,k)[1:3])) for k in ("start","end")]
                shape=LineString(points).buffer(float(first(node,"width")[1])/2+.222)
                layers={str(first(node,"layer")[1])}
            else:
                shape=Point(tuple(map(float,first(node,"at")[1:3]))).buffer(float(first(node,"size")[1])/2+.222)
                layers={"F.Cu","In1.Cu","In2.Cu","In3.Cu","In4.Cu","B.Cu"}
            for (force,layer),pour in pours.items():
                if layer in layers and force!=net and shape.intersects(pour):
                    hits.append(dict(uuid=str(first(node,"uuid")[1]),force_net=force,layer=layer))
        if not hits:
            tree.extend(nodes)
        results.append(dict(net=net,objects=len(nodes),retained=not hits,foreign_power_intersections=hits))
    assert sexpr(tree[:original_count])==frozen
    pcb=out/base.name
    pcb.write_text(sexpr(tree)+"\n")
    (out/"selection.json").write_text(json.dumps(dict(source_sha256=sha(base),trial_sha256=sha(trial),
        filled_input_sha256=sha(filled),candidate_sha256=sha(pcb),recipe_sha256=sha(Path(__file__)),
        selections=results,all_source_objects_unchanged=True,native_checks_pending=True,
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print([(r["net"],r["retained"],len(r["foreign_power_intersections"])) for r in results])


if __name__=="__main__":
    run()
