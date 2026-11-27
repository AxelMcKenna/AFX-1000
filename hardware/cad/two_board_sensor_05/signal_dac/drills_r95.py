"""Screen only new/replaced via drills; do not qualify legacy solder processes."""
import argparse
import json
from pathlib import Path
from shapely.geometry import Point
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape

ROOT=Path(__file__).resolve().parents[3]/'fabrication'


def run():
    folder=Path(__file__).resolve().parent/'native-r95'
    before=folder.parent.parent/'signal_input/native-r7/signal_main.kicad_pcb'
    after=folder/'signal_main.kicad_pcb'
    capture_path=folder.parent/'capture-r95/capture.json'
    capture=json.loads(capture_path.read_text())
    assert all(sha(Path(p))==h for p,h in capture['source_sha256'].items())
    assert str(after) in capture['source_sha256']
    old={str(first(v,'uuid')[1]) for v in children(read_sexpr(before.read_text()),'via')}
    new={str(first(v,'uuid')[1]):float(first(v,'drill')[1]) for v in children(read_sexpr(after.read_text()),'via')}
    pads=[o for o in capture['objects'] if o['kind']=='PAD' and not any(o['drill_mm']) and o['layers']]
    polygons=[shape([p for layer in o['layers'].values() for p in layer]) for o in pads]
    tree=STRtree(polygons)
    rows=[]
    for obj in capture['objects']:
        if obj['kind']!='PCB_VIA' or obj['uuid'] in old:
            continue
        point=Point(obj['position_mm'])
        index=int(tree.nearest(point))
        gap=point.distance(polygons[index])-new[obj['uuid']]/2
        rows.append(dict(uuid=obj['uuid'],net=obj['net'],position_mm=obj['position_mm'],
                         drill_mm=new[obj['uuid']],nearest_SMD_ref=pads[index]['ref'],
                         nearest_SMD_pin=pads[index]['pin'],hole_edge_to_SMD_copper_mm=gap))
    assert rows and min(r['hole_edge_to_SMD_copper_mm'] for r in rows)>=.1
    output=folder/'added-via-drill-review.json'
    # Deterministic source-bound review may be regenerated after an audit-code change.
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in (before,after,capture_path,Path(__file__),ROOT/'smd_drill_review.py')},
        new_or_replaced_vias=rows,minimum_gap_mm=min(r['hole_edge_to_SMD_copper_mm'] for r in rows),
        new_drills_do_not_overlap_SMD_copper=True,all_legacy_vias_qualified=False,
        mask_stencil_registration_and_process_accepted=False,fabrication_released=False),indent=2)+'\n')
    print('Screened',len(rows),'new/replaced via drills; minimum gap',min(r['hole_edge_to_SMD_copper_mm'] for r in rows))


if __name__=='__main__':
    run()
