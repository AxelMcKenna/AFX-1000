"""Bridge three enclosed same-net copper pinholes after clearance screening."""

import json
import uuid
from collections import defaultdict
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import a, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_layers import LayerScreen
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent


def run():
    capture_path = ROOT/"staging/rail-monitor-routing-inputs-16-clean/capture.json"
    output = ROOT/"staging/rail-monitor-sliver-repair-01"
    assert not output.exists()
    capture = json.loads(capture_path.read_text())
    assert all(sha(Path(p)) == digest for p,digest in capture["source_sha256"].items())
    source = next(Path(p) for p in capture["source_sha256"] if p.endswith(".kicad_pcb"))
    tree = read_sexpr(source.read_text())
    screen = LayerScreen(capture,signal_layers=("F.Cu","B.Cu"))
    nets = defaultdict(list)
    for obj in capture["objects"]:
        if "F.Cu" in obj["layers"]:
            nets[obj["net"]].append(shape(obj["layers"]["F.Cu"]))
    bridges = []
    for net,polygons in nets.items():
        copper = unary_union(polygons)
        for poly in ([copper] if copper.geom_type == "Polygon" else copper.geoms):
            if poly.geom_type != "Polygon":
                continue
            for ring in poly.interiors:
                hole = Polygon(ring)
                if hole.area >= .01:
                    continue
                x,y,u,v = hole.bounds
                choices = [[(x,(y+v)/2),(u,(y+v)/2)],
                    [((x+u)/2,y),((x+u)/2,v)],[(x,y),(u,v)],[(x,v),(u,y)]]
                accepted = next((points for points in choices if
                    LineString(points).buffer(.099,quad_segs=32).covers(hole) and screen.legal(net,"F.Cu",points)),None)
                assert accepted,(net,hole.bounds)
                ident = str(uuid.uuid5(uuid.NAMESPACE_URL,f"AFX:E13:pinhole:{sha(capture_path)}:{net}:{accepted}"))
                tree.append([a("segment"),[a("start"),*accepted[0]],[a("end"),*accepted[1]],[a("width"),.2],
                    [a("layer"),"F.Cu"],[a("net"),net],[a("uuid"),ident]])
                screen.added.append((net,"F.Cu",LineString(accepted)))
                bridges.append(dict(net=net,hole_area_mm2=hole.area,bounds_mm=hole.bounds,points_mm=accepted,
                    entire_hole_covered_with_1um_radius_reserve=True,other_net_clearance_screen_passed=True))
    assert len(bridges) == 3
    output.mkdir()
    pcb = output/source.name
    pcb.write_text(sexpr(tree)+"\n")
    inputs = (source,capture_path,Path(__file__),ROOT/"route_nf_layers.py",ROOT/"route_nf_surface.py")
    (output/"construction.json").write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        candidate_PCB_sha256=sha(pcb),bridges=bridges,all_original_authored_objects_exact=True,
        native_checks_pending=True,manufacturing_process_accepted=False,fabrication_released=False),indent=2)+"\n")
    print("Bridged3 enclosed pinholes with0.2mm same-net tracks; native checks pending")


if __name__ == "__main__":
    run()
