"""Remove warned copper only when its contacts remain joined locally.

Native polygons are outside approximations. Supporting copper is eroded by
2 um and remaining physical drills are subtracted conservatively. Contacts
must remain connected inside a 2 mm neighborhood, with actual plated objects
providing cross-layer connections. This is topology evidence, not a PDN rating.
"""
import argparse,json
from collections import defaultdict
from pathlib import Path
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha

ROOT=Path(__file__).resolve().parent

def pieces(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for part in getattr(g,'geoms',[]) for p in pieces(part)]

def contact_components(nodes,contacts):
    """Nodes contain (id, layer, plated, inner geometry). Reject lost contacts."""
    parent=list(range(len(nodes)))
    def root(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    for i,(uid,layer,plated,g) in enumerate(nodes):
        for j in range(i):
            vid,other,other_plated,h=nodes[j]
            if (uid==vid and plated and other_plated) or (layer==other and g.intersection(h).area>1e-10):
                parent[root(i)]=root(j)
    groups={root(k) for k in contacts}
    return len(groups),[sorted(k for k in contacts if root(k)==g) for g in groups]

class LocalCopper:
    def __init__(self,capture,board,nets):
        self.rows=[];self.objects={o['uuid']:o for o in capture['objects']}
        vias={first(v,'uuid')[1]:float(first(v,'drill')[1]) for v in children(board,'via')}
        self.holes=[]
        for o in capture['objects']:
            drill=vias.get(o['uuid'])
            if drill is not None:
                self.holes.append((o['uuid'],Point(o['position_mm']).buffer(drill/2+.002,quad_segs=64)))
            elif o['kind']=='PAD' and any(o['drill_mm']):
                # A bounding disk encloses round and slotted holes independently
                # of footprint rotation. It can reject safe removals, never grant one.
                radius=max(o['drill_mm'])/2+.002
                self.holes.append((o['uuid'],Point(o['position_mm']).buffer(radius,quad_segs=64)))
            if o['net'] not in nets:continue
            plated=o['kind']=='PCB_VIA' or (o['kind']=='PAD' and any(o['drill_mm']) and not o.get('npth'))
            for layer,polys in o['layers'].items():
                for p in polys:self.rows.append((o['uuid'],o['net'],layer,plated,Polygon(p['outer'],p['holes'])))
        for z in capture['zones']:
            if z['keepout'] or z['net'] not in nets:continue
            for i,p in enumerate(z['polygons']):
                self.rows.append((z['uuid']+':'+str(i),z['net'],z['layer'],False,Polygon(p['outer'],p['holes'])))
        self.tree=STRtree([r[-1] for r in self.rows]);self.hole_tree=STRtree([g for uid,g in self.holes])

    def review(self,uid,removed):
        obj=self.objects[uid]
        target={l:unary_union([Polygon(p['outer'],p['holes']) for p in ps]) for l,ps in obj['layers'].items()}
        region=box(*unary_union(list(target.values())).bounds).buffer(2,join_style=2)
        holes=unary_union([self.holes[int(i)][1] for i in self.hole_tree.query(region)
                           if self.holes[int(i)][0] not in removed|{uid}])
        nodes=[];contacts=set();missing=[]
        for index in self.tree.query(region):
            other,net,layer,plated,outer=self.rows[int(index)]
            if other in removed|{uid} or net!=obj['net']:continue
            outer=outer.intersection(region).difference(holes)
            inner=outer.buffer(-.002)
            touch=layer in target and outer.distance(target[layer])<=.002
            parts=pieces(inner)
            if touch and not parts:missing.append(other)
            found_contact=False
            for geom in parts:
                k=len(nodes);nodes.append((other,layer,plated,geom))
                if touch and geom.distance(target[layer])<=.004:
                    contacts.add(k);found_contact=True
            if touch and not found_contact:missing.append(other)
        count,groups=contact_components(nodes,contacts)
        return dict(uuid=uid,net=obj['net'],kind=obj['kind'],position_mm=obj['position_mm'],
            safe=not missing and count<=1,local_contact_components=count,
            conservative_contact_not_represented=sorted(set(missing)),
            contact_groups=[[dict(uuid=nodes[k][0],layer=nodes[k][1]) for k in group] for group in groups],
            copper_current_capacity_qualified=False)

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',required=True);ap.add_argument('--label',required=True);args=ap.parse_args()
    assert all(v and all(ch.isalnum() or ch in '-_' for ch in v) for v in [args.capture,args.label])
    cp=ROOT/'staging'/args.capture/'capture.json';c=json.loads(cp.read_text())
    assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));drc=source.with_name('drc.json');report=json.loads(drc.read_text())
    assert not report['unconnected_items'] and not report['schematic_parity']
    assert all(v['type'] in ['track_dangling','via_dangling'] and v['severity']=='warning' for v in report['violations'])
    targets=[v['items'][0]['uuid'] for v in report['violations']]
    board=read_sexpr(source.read_text());objects={o['uuid']:o for o in c['objects']};nets={objects[u]['net'] for u in targets}
    screen=LocalCopper(c,board,nets);removed=set();reviews=[]
    for uid in targets:
        row=screen.review(uid,removed);reviews.append(row)
        if row['safe']:removed.add(uid)
        print(row['kind'],row['net'],row['position_mm'],'remove' if row['safe'] else 'retain','contact groups',row['local_contact_components'],flush=True)
    nodes=[n for tag in ['segment','via'] for n in children(board,tag) if first(n,'uuid')[1] in removed]
    assert len(nodes)==len(removed) and nodes
    for n in nodes:board.remove(n)
    out=ROOT/'staging'/args.label;out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,drc,Path(__file__)]
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),removed_objects=nodes,checks=reviews,local_neighborhood_mm=2,support_erosion_mm=.002,physical_drills_subtracted=True,source_and_load_PDN_qualified=False,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Removed',len(nodes),'of',len(targets),'warned objects')

if __name__=='__main__':run()
