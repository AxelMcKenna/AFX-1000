"""Finish vacated-leaf pruning, including short end-cap overlaps."""
from hardware.fabrication.nf_logic_swap_prepare import *

def prune_leaves(capture,nets):
    assert not any(z['net'] in nets and not z['keepout'] for z in capture['zones'])
    active={o['uuid']:o for o in capture['objects'] if o['net'] in nets}
    geometries={(u,l):shape(polys) for u,o in active.items() for l,polys in o['layers'].items()}
    adj={u:set() for u in active};touch=defaultdict(set)
    buckets=defaultdict(list)
    for u,o in active.items():
        for layer in o['layers']:buckets[o['net'],layer].append(u)
    for (net,layer),ids in buckets.items():
        geoms=[geometries[u,layer] for u in ids];tree=STRtree(geoms)
        for i,u in enumerate(ids):
            for j in tree.query(geoms[i].buffer(.00001)):
                j=int(j);v=ids[j]
                if j<=i or geoms[i].distance(geoms[j])>.00001:continue
                adj[u].add(v);adj[v].add(u);touch[u,v].add(layer);touch[v,u].add(layer)
    protected_before=pad_partitions(active,adj);removed=[]
    def neighbors_connected_without(uid,neighbors):
        if len(neighbors)<2:return True
        seed=next(iter(neighbors));seen={seed};stack=[seed]
        while stack:
            key=stack.pop()
            for nxt in adj[key]:
                if nxt!=uid and nxt in active and nxt not in seen:seen.add(nxt);stack.append(nxt)
            if neighbors<=seen:return True
        return False
    while True:
        choice=None
        for uid,obj in active.items():
            if obj['kind']=='PAD':continue
            neighbors=adj[uid]&active.keys();reason=None
            if obj['kind']=='PCB_TRACK':
                layer=next(iter(obj['layers']))
                dead=[pt for pt in [obj['position_mm'],obj['end_mm']] if not any((v,layer) in geometries and geometries[v,layer].distance(Point(pt))<=obj['width_mm']/2+.00001 for v in neighbors)]
                if dead or len(neighbors)<=1:reason='unattached end or sole graph neighbor; every remaining contact is joined without this track'
            elif obj['kind']=='PCB_VIA':
                layers={l for v in neighbors for l in touch[uid,v]}
                if len(layers)<2:reason='no interlayer function, with every remaining contact joined without this via'
            if reason and neighbors_connected_without(uid,neighbors):choice=(uid,reason,sorted(neighbors));break
        if choice is None:break
        uid,reason,neighbors=choice;removed.append(dict(object=active.pop(uid),reason=reason,neighbors=neighbors))
        assert len(removed)<600,'Unexpectedly broad vacated-branch pruning'
    protected_after=pad_partitions(active,adj);assert protected_before==protected_after
    removed_ids={r['object']['uuid'] for r in removed}
    return [o for o in capture['objects'] if o['uuid'] not in removed_ids],removed,protected_before


def run():
    cp=ROOT/'staging/nf-logic-swap-rework-inputs-165/capture.json';c=json.loads(cp.read_text());assert all(sha(Path(p))==h for p,h in c['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text())
    initial=ROOT/'staging/nf-logic-swap-prepared-01/construction.json';plan=json.loads(initial.read_text());nets=set(plan['affected_nets'])
    c['objects'],removed,partitions=prune_leaves(c,nets);ids={r['object']['uuid'] for r in removed};nodes=[]
    for n in list(children(board,'segment')+children(board,'via')):
        if first(n,'uuid')[1] in ids:nodes.append(n);board.remove(n)
    assert len(nodes)==len(ids) and ids
    out=ROOT/'staging/nf-logic-swap-leaves-01';out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,initial,Path(__file__),ROOT/'nf_logic_swap_prepare.py',ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),pruned_leaves=removed,removed_objects=nodes,protected_pad_partitions=partitions,all_post_cut_pad_connections_preserved=True,native_checks_pending=True,fabrication_released=False),indent=2)+'\n')
    print('Pruned further vacated leaves:',len(nodes),flush=True)

if __name__=='__main__':run()
