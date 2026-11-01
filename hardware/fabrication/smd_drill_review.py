"""Conservative native-polygon screen for through-drills near SMD copper.

This establishes copper separation only. Stencil, mask-web and assembly process
acceptance are separate requirements and are never inferred from this screen.
"""

import argparse
import json
from pathlib import Path

from shapely.geometry import Point
from shapely.strtree import STRtree

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT = Path(__file__).resolve().parent


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture",required=True)
    parser.add_argument("--source",required=True)
    args = parser.parse_args()
    for label in (args.capture,args.source):
        assert label and all(c.isalnum() or c in "-_" for c in label)
    capture_path = ROOT/"staging"/args.capture/"capture.json"
    folder = ROOT/"staging"/args.source
    output = folder/"smd-drill-review.json"
    assert not output.exists()
    capture = json.loads(capture_path.read_text())
    assert all(sha(Path(p)) == digest for p,digest in capture["source_sha256"].items())
    source = next(Path(p) for p in capture["source_sha256"] if p.endswith(".kicad_pcb"))
    assert source.parent == folder
    drills = {str(first(v,"uuid")[1]):float(first(v,"drill")[1]) for v in children(read_sexpr(source.read_text()),"via")}
    pads = [p for p in capture["objects"] if p["kind"] == "PAD" and not any(p["drill_mm"]) and p["layers"]]
    geometries = [shape([p for polygons in obj["layers"].values() for p in polygons]) for obj in pads]
    tree = STRtree(geometries)
    rows = []
    for via in (v for v in capture["objects"] if v["kind"] == "PCB_VIA"):
        point = Point(via["position_mm"])
        nearest = int(tree.nearest(point))
        radius = drills[via["uuid"]]/2
        gap = point.distance(geometries[nearest])-radius
        rows.append(dict(via_uuid=via["uuid"],via_net=via["net"],via_position_mm=via["position_mm"],
            nearest_SMD_ref=pads[nearest]["ref"],nearest_SMD_pin=pads[nearest]["pin"],
            conservative_drill_edge_to_SMD_copper_mm=gap))
    assert rows and min(r["conservative_drill_edge_to_SMD_copper_mm"] for r in rows) >= .1
    inputs = (source,capture_path,Path(__file__))
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        screened_through_vias=len(rows),screened_SMD_lands=len(pads),native_outside_polygon_error_mm=.001,
        minimum_drill_edge_to_SMD_copper_mm=min(r["conservative_drill_edge_to_SMD_copper_mm"] for r in rows),
        no_drilled_hole_overlap_with_SMD_copper=True,minimum_required_screen_gap_mm=.1,
        nearest_SMD_for_each_via=rows,stencil_mask_web_and_assembly_process_accepted=False,
        fabrication_released=False),indent=2)+"\n")
    print("Screened",len(rows),"through-vias; minimum SMD drill gap",round(min(r["conservative_drill_edge_to_SMD_copper_mm"] for r in rows),4),"mm")


if __name__ == "__main__":
    run()
