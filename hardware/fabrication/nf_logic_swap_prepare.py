"""Separate U38/U41 pose swap with explicit cuts and conservative leaf pruning.

Only vacated signal copper is pruned. Protected pad connectivity after the
initial documented cuts must be identical before and after pruning.
"""
import copy,json
from pathlib import Path
from collections import defaultdict
from shapely.geometry import Point
from shapely.strtree import STRtree
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.route_nf_surface import shape
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr

ROOT=Path(__file__).resolve().parent
PAIR=('U38','U41')

def pad_partitions(active,adj):
    seen=set();groups=[]
    for uid in active:
        if uid in seen:continue
        stack=[uid];seen.add(uid);pads=[]
        while stack:
            key=stack.pop();obj=active[key]
            if obj['kind']=='PAD':pads.append((obj['ref'],obj['pin'],obj['net']))
            for nxt in adj[key]:
                if nxt in active and nxt not in seen:seen.add(nxt);stack.append(nxt)
        if pads:groups.append(sorted(pads))
    return sorted(groups)


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
                if dead:reason='unattached track end, with every remaining contact joined without this track'
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
    cp=ROOT/'staging/nf-u37-multilayer-inputs-149/capture.json';inventory=ROOT/'staging/nf-logic-swap-study-01/swap-rework-inventory.json'
    c=json.loads(cp.read_text());plan=json.loads(inventory.read_text())
    assert all(sha(Path(p))==h for d in [c,plan] for p,h in d['source_sha256'].items())
    source=next(Path(p) for p in c['source_sha256'] if p.endswith('.kicad_pcb'));board=read_sexpr(source.read_text())
    fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(board,'footprint')}
    poses={r:copy.deepcopy(first(fps[r],'at')[1:]) for r in PAIR}
    assert all(len(poses[r])==2 for r in PAIR)
    for here,other in [PAIR,PAIR[::-1]]:first(fps[here],'at')[1:]=copy.deepcopy(poses[other])
    oldpads={(o['ref'],o['pin']):copy.deepcopy(o) for o in c['objects'] if o['kind']=='PAD'}
    for obj in c['objects']:
        if obj.get('ref') in PAIR:
            other=PAIR[1] if obj['ref']==PAIR[0] else PAIR[0];replacement=oldpads[other,obj['pin']]
            for key in ['position_mm','layers','orientation_degrees']:obj[key]=copy.deepcopy(replacement[key])
    cut={o['uuid'] for o in plan['initial_copper_cut_candidates']};assert len(cut)==25
    c['objects']=[o for o in c['objects'] if o['uuid'] not in cut]
    nets={r['old_net'] for r in plan['changed_physical_site_pin_nets']}
    assert not nets&{'/AGND','/AUX2V6'}
    c['objects'],pruned,partitions=prune_leaves(c,nets);removed_ids=cut|{r['object']['uuid'] for r in pruned}
    removed=[]
    for node in list(children(board,'segment')+children(board,'via')):
        if first(node,'uuid')[1] in removed_ids:
            assert first(node,'net')[-1] in nets;removed.append(node);board.remove(node)
    assert len(removed)==len(removed_ids)
    output=ROOT/'staging/nf-logic-swap-prepared-01';output.mkdir(exist_ok=False);pcb=output/source.name;pcb.write_text(sexpr(board)+'\n')
    inputs=[source,cp,inventory,Path(__file__),ROOT/'route_nf_surface.py']
    (output/'construction.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},candidate_PCB_sha256=sha(pcb),pose_swap_before=poses,pose_swap_after={r:poses[PAIR[1] if r==PAIR[0] else PAIR[0]] for r in PAIR},initial_cut_uuids=sorted(cut),pruned_leaves=pruned,removed_objects=removed,affected_nets=sorted(nets),protected_pad_partitions_after_initial_cuts=partitions,pruning_preserves_all_post_cut_pad_partitions=True,only_two_component_poses_changed=True,original_pad_net_assignments_unchanged=True,native_checks_pending=True,physical_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Prepared swap; initial cuts',len(cut),'pruned leaves',len(pruned),'removed copper objects',len(removed),flush=True)

if __name__=='__main__':run()
