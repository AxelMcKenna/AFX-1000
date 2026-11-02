"""Swap preparation that reserves proven escapes at all unmoved SMD pads."""
import heapq,math
from hardware.fabrication.nf_logic_swap_prepare import *

def prune_leaves(capture,nets,protected=()):
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
            if obj['kind']=='PAD' or uid in protected:continue
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


def terminal_escapes(capture,nets,cut):
    objects={o['uuid']:o for o in capture['objects'] if o['net'] in nets and o['uuid'] not in cut and 'F.Cu' in o['layers']}
    geometry={u:shape(o['layers']['F.Cu']) for u,o in objects.items()};by_net=defaultdict(list)
    for u,o in objects.items():by_net[o['net']].append(u)
    adj={u:set() for u in objects}
    for ids in by_net.values():
        gs=[geometry[u] for u in ids];tree=STRtree(gs)
        for i,u in enumerate(ids):
            for j in tree.query(gs[i].buffer(.00001)):
                j=int(j);v=ids[j]
                if i!=j and gs[i].distance(gs[j])<=.00001:adj[u].add(v)
    paths=[];protected=set()
    for uid,pad in objects.items():
        if pad['kind']!='PAD' or pad['ref'] in PAIR or len(pad['layers'])!=1:continue
        queue=[(0.,uid,[])];best={uid:0};found=None
        while queue:
            cost,key,route=heapq.heappop(queue)
            if cost>best[key]+1e-9:continue
            if objects[key]['kind']=='PCB_VIA':found=(cost,route);break
            for nxt in adj[key]:
                o=objects[nxt]
                if o['kind']=='PAD':continue
                total=cost+(math.dist(o['position_mm'],o['end_mm']) if o['kind']=='PCB_TRACK' else 0)
                if total>6 or total>=best.get(nxt,float('inf')):continue
                best[nxt]=total;heapq.heappush(queue,(total,nxt,route+[nxt]))
        if found:
            cost,route=found;protected.update(route);paths.append(dict(ref=pad['ref'],pin=pad['pin'],net=pad['net'],objects=route,length_mm=cost,via=route[-1]))
        else:
            leaves=[v for v in adj[uid] if objects[v]['kind']=='PCB_TRACK' and math.dist(objects[v]['position_mm'],objects[v]['end_mm'])<=3]
            if leaves:protected.update(leaves);paths.append(dict(ref=pad['ref'],pin=pad['pin'],net=pad['net'],objects=leaves,via=None))
    return protected,paths


def run():
    cp=ROOT/'staging/nf-u37-multilayer-inputs-149/capture.json';inventory=ROOT/'staging/nf-logic-swap-study-01/swap-rework-inventory.json';c=json.loads(cp.read_text());plan=json.loads(inventory.read_text())
    assert all(sha(Path(p))==h for d in [c,plan] for p,h in d['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text());fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(board,'footprint')}
    poses={r:copy.deepcopy(first(fps[r],'at')[1:]) for r in PAIR}
    for here,other in [PAIR,PAIR[::-1]]:first(fps[here],'at')[1:]=copy.deepcopy(poses[other])
    oldpads={(o['ref'],o['pin']):copy.deepcopy(o) for o in c['objects'] if o['kind']=='PAD'}
    for o in c['objects']:
        if o.get('ref') in PAIR:
            other=PAIR[1] if o['ref']==PAIR[0] else PAIR[0]
            for k in ['position_mm','layers','orientation_degrees']:o[k]=copy.deepcopy(oldpads[other,o['pin']][k])
    cut={o['uuid'] for o in plan['initial_copper_cut_candidates']};nets={r['old_net'] for r in plan['changed_physical_site_pin_nets']};protected,paths=terminal_escapes(c,nets,cut)
    assert not protected&cut;c['objects']=[o for o in c['objects'] if o['uuid'] not in cut]
    c['objects'],pruned,partitions=prune_leaves(c,nets,protected);removed_ids=cut|{r['object']['uuid'] for r in pruned};assert not protected&removed_ids
    removed=[]
    for n in list(children(board,'segment')+children(board,'via')):
        if first(n,'uuid')[1] in removed_ids:removed.append(n);board.remove(n)
    assert len(removed)==len(removed_ids)
    out=ROOT/'staging/nf-logic-swap-reserved-01';out.mkdir(exist_ok=False);pcb=out/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,inventory,Path(__file__),ROOT/'nf_logic_swap_prepare.py',ROOT/'route_nf_surface.py']
    (out/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),pose_swap_before=poses,initial_cut_uuids=sorted(cut),protected_terminal_escapes=paths,protected_objects=sorted(protected),pruned_leaves=pruned,removed_objects=removed,affected_nets=sorted(nets),protected_pad_partitions_after_initial_cuts=partitions,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Reserved',len(paths),'terminal escapes with',len(protected),'objects; removed',len(removed),'vacated objects',flush=True)

if __name__=='__main__':run()
