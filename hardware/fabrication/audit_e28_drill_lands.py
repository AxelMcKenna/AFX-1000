"""Map retained via drills against actual front/back SMD copper and paste lands."""
import argparse,csv,json
from pathlib import Path
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent

def classify_gap(gap,error=.001):
    return 'intersects_beyond_capture_error' if gap < -error else 'possible_intersection' if gap<0 else 'under_0.1mm_screen' if gap<.1 else 'outside_screen'

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--after',required=True);args=ap.parse_args()
    assert all(v and all(ch.isalnum() or ch in '-_' for ch in v) for v in [args.capture,args.after])
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    folder=ROOT/'staging'/args.after;pcb=folder/'rail_disconnect.kicad_pcb';assert str(pcb) in c['source_sha256']
    board=read_sexpr(pcb.read_text());vias={first(v,'uuid')[1]:v for v in children(board,'via')}
    authored_pads={first(p,'uuid')[1]:p for f in children(board,'footprint') for p in children(f,'pad')}
    pads=[];polys=[]
    for o in c['objects']:
        if o['kind']!='PAD' or any(o['drill_mm']):continue
        layers=first(authored_pads[o['uuid']],'layers')[1:]
        for layer,ps in o['layers'].items():
            if layer not in ['F.Cu','B.Cu']:continue
            pads.append(dict(ref=o['ref'],pin=o['pin'],layer=layer,has_paste_layer=layer.replace('.Cu','.Paste') in layers))
            polys.append(unary_union([Polygon(p['outer'],p['holes']) for p in ps]))
    tree=STRtree(polys);rows=[]
    for o in c['objects']:
        if o['kind']!='PCB_VIA':continue
        v=vias[o['uuid']];drill=float(first(v,'drill')[1]);point=Point(o['position_mm']);contacts=[]
        for index in tree.query(point.buffer(drill/2+.101)):
            i=int(index);gap=point.distance(polys[i])-drill/2
            if gap<.1:contacts.append(dict(**pads[i],screened_hole_edge_gap_mm=gap,classification=classify_gap(gap)))
        if contacts:
            rows.append(dict(uuid=o['uuid'],net=o['net'],position_mm=o['position_mm'],drill_mm=drill,
                capping=first(v,'capping')[1] if first(v,'capping') else 'unspecified',
                filling=first(v,'filling')[1] if first(v,'filling') else 'unspecified',contacts=contacts))
    overlaps=[r for r in rows if any(x['screened_hole_edge_gap_mm']<0 for x in r['contacts'])]
    definite=[r for r in rows if any(x['classification']=='intersects_beyond_capture_error' for x in r['contacts'])]
    inputs=[pcb,cp,Path(__file__)]
    result=dict(source_sha256={str(p):sha(p) for p in inputs},total_vias=len(vias),vias_under_0p1mm_screen=len(rows),
        vias_intersecting_SMD_copper_screen=len(overlaps),vias_intersecting_beyond_capture_error=len(definite),
        vias_intersecting_paste_target_lands=sum(any(x['has_paste_layer'] and x['screened_hole_edge_gap_mm']<0 for x in r['contacts']) for r in rows),
        overlap_vias_explicitly_unfilled_uncapped=sum(r['capping']=='no' and r['filling']=='no' for r in overlaps),
        contacts=rows,minimum_gap_is_conservative_outside_polygon_screen=True,
        acceptance_note='These are geometry/process review locations. A 0.1 mm screen is not a manufacturer acceptance criterion; thermal/connector lands and ordinary SMD lands need their appropriate reviewed solder/stencil/process treatment.',
        supplier_process_accepted=False,physical_qualified=False,fabrication_released=False)
    path=folder/'drill-land-review.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n')
    with (folder/'drill-land-locations.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['via_uuid','net','x_mm','y_mm','drill_mm','pad_ref','pad_pin','pad_layer','has_paste_layer','screened_gap_mm','classification','capping','filling'])
        for r in rows:
            for contact in r['contacts']:writer.writerow([r['uuid'],r['net'],*r['position_mm'],r['drill_mm'],contact['ref'],contact['pin'],contact['layer'],contact['has_paste_layer'],contact['screened_hole_edge_gap_mm'],contact['classification'],r['capping'],r['filling']])
    print('Retained vias',len(vias),'SMD overlap screen',len(overlaps),'beyond approximation error',len(definite),'under 0.1mm screen',len(rows))

if __name__=='__main__':run()
