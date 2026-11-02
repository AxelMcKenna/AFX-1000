"""Follow proven dead branch tips without one native run per tiny segment.

Only neighbors of an already removed warned branch are considered. Each new
track must have a centerline endpoint without a continuation, or a single
remaining copper contact;
every removal repeats the conservative
local contact proof. Authored zones, component geometry and other copper stay fixed.
"""
import argparse,json
from collections import deque
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from hardware.fabrication.e28_warning_cleanup import LocalCopper,Polygon
from hardware.fabrication.audit_candidate import sha
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr

ROOT=Path(__file__).resolve().parent

def exposed(screen,uid,removed):
    o=screen.objects[uid]
    if o['kind']!='PCB_TRACK':return False
    layer=next(iter(o['layers']))
    for xy in [o['position_mm'],o['end_mm']]:
        p=Point(xy);joined=False
        for index in screen.tree.query(p.buffer(.002)):
            other,net,l,plated,g=screen.rows[int(index)]
            if other not in removed|{uid} and net==o['net'] and l==layer and g.distance(p)<=.002:
                neighbor=screen.objects.get(other)
                if neighbor and neighbor['kind']=='PCB_TRACK' and neighbor['width_mm']<=o['width_mm']:
                    # An equal-width end cap may overlap the next short zigzag.
                    # Use centerline continuity only to propose a leaf; the
                    # independent full-copper contact proof still decides removal.
                    if LineString([neighbor['position_mm'],neighbor['end_mm']]).distance(p)>.002:continue
                joined=True;break
        if not joined:return True
    return False

def prune(screen,seeds,limit=2000):
    queue=deque(sorted(seeds));removed=set();checks=[];attempts=0
    while queue:
        uid=queue.popleft()
        if uid in removed:continue
        if screen.objects[uid]['kind'] not in ['PCB_TRACK','PCB_VIA']:continue
        free=exposed(screen,uid,removed)
        row=screen.review(uid,removed);attempts+=1
        neighbor_ids={c['uuid'] for g in row['contact_groups'] for c in g}
        sole_contact=len(neighbor_ids)<=1
        if uid not in seeds and not free and not sole_contact:continue
        row['native_warned_seed']=uid in seeds;row['derived_centerline_endpoint']=uid not in seeds and free
        row['derived_single_contact_leaf']=uid not in seeds and sole_contact
        if not row['safe']:continue
        removed.add(uid);checks.append(row);assert len(removed)<=limit
        o=screen.objects[uid];region=unary_union([Polygon(p['outer'],p['holes']) for ps in o['layers'].values() for p in ps])
        for index in screen.tree.query(region.buffer(.002)):
            other,net,l,plated,g=screen.rows[int(index)]
            if other in screen.objects and other not in removed and net==o['net'] and l in o['layers'] and g.distance(region)<=.002:
                queue.append(other)
    return removed,checks,attempts

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--label',required=True);args=ap.parse_args()
    assert all(v and all(ch.isalnum() or ch in '-_' for ch in v) for v in [args.capture,args.label])
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));drc=source.with_name('drc.json');report=json.loads(drc.read_text())
    assert not report['unconnected_items'] and not report['schematic_parity']
    assert all(v['type'] in ['track_dangling','via_dangling'] and v['severity']=='warning' for v in report['violations'])
    seeds={v['items'][0]['uuid'] for v in report['violations']};board=read_sexpr(source.read_text());objects={o['uuid']:o for o in c['objects']}
    screen=LocalCopper(c,board,{objects[u]['net'] for u in seeds});removed,checks,attempts=prune(screen,seeds)
    nodes=[n for tag in ['segment','via'] for n in children(board,tag) if first(n,'uuid')[1] in removed];assert len(nodes)==len(removed) and nodes
    for n in nodes:board.remove(n)
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,drc,Path(__file__),ROOT/'e28_warning_cleanup.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),removed_objects=nodes,checks=checks,native_seed_count=len(seeds),local_contact_reviews=attempts,source_and_load_PDN_qualified=False,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Removed',len(nodes),'objects from',len(seeds),'native warned branch tips; exact local reviews',attempts)

if __name__=='__main__':run()
