"""Map existing supply conductors; trace-squares proxy is not a resistance bound."""
import hashlib, heapq, json, math
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def analyze():
    cap=json.loads((HERE/'TBP72-AUX-copper.json').read_text())
    dist=json.loads((HERE/'TBP72-distribution.json').read_text())
    provenance=json.loads((HERE/'capture-provenance.json').read_text())
    for n,h in provenance['snapshots_sha256'].items():assert sha(HERE/n)==h
    assert cap['native_uncapped_opens']==dist['native_board_opens']==1937
    assert dist['source_sha256'][cap['source_path']]==cap['source_sha256']
    assert provenance['source_sha256'][cap['source_path']]==cap['source_sha256']
    objs={o['uuid']:o for o in cap['objects']}
    src=next(o for o in objs.values() if o.get('ref')=='P_U102' and o.get('pin')=='1')
    source_group=src['group']
    objs={k:o for k,o in objs.items() if o['group']==source_group}
    shapes={k:{l:unary_union([Polygon(p['outer'],p['holes']) for p in ps]) for l,ps in o['layers'].items() if ps} for k,o in objs.items()}
    adj={k:[] for k in objs};contacts={}
    for n,(a,oa) in enumerate(objs.items()):
        for b,ob in list(objs.items())[n+1:]:
            layers=[l for l in sorted(shapes[a].keys()&shapes[b].keys()) if shapes[a][l].intersection(shapes[b][l]).area>1e-12]
            if layers:
                adj[a].append(b);adj[b].append(a);contacts[tuple(sorted([a,b]))]=layers
    costs={k:math.dist(o['position_mm'],o['end_mm'])/o['width_mm'] if o['kind']=='PCB_TRACK' else 0 for k,o in objs.items()}
    best={src['uuid']:0};paths={src['uuid']:[src['uuid']]};queue=[(0,src['uuid'])]
    while queue:
        cost,a=heapq.heappop(queue)
        if cost!=best[a]:continue
        for b in adj[a]:
            new=cost+costs[b]
            if new<best.get(b,float('inf')):
                best[b]=new;paths[b]=paths[a]+[b];heapq.heappush(queue,(new,b))
    # Reproduce all35 native source-connected pad identities by geometric contact.
    assert len(best)==len(objs),(len(best),len(objs))
    rows=[]
    for r in dist['terminals']:
        if r['category']!='IC_supply':continue
        uid=next((k for k,o in objs.items() if o.get('ref')==r['ref'] and o.get('pin')==r['pin']),None)
        assert bool(uid)==r['source_connected']
        if uid:
            route=paths[uid];tracks=[objs[k] for k in route if objs[k]['kind']=='PCB_TRACK']
            rows.append(dict(ref=r['ref'],pin=r['pin'],track_squares_proxy=best[uid],full_track_length_sum_mm=math.fsum(math.dist(o['position_mm'],o['end_mm']) for o in tracks),minimum_track_width_mm=min((o['width_mm'] for o in tracks),default=None),via_objects_on_path=sum(objs[k]['kind']=='PCB_VIA' for k in route),objects=route,contacts=[dict(objects=[a,b],layers=contacts[tuple(sorted([a,b]))]) for a,b in zip(route,route[1:])]))
    rows.sort(key=lambda r:r['track_squares_proxy'],reverse=True)
    return dict(source_connected_ICs=len(rows),unconnected_ICs=81-len(rows),source_group_object_count=len(objs),geometric_contact_graph_matches_native=True,
        paths=rows,nominal_source_and_main_ground_connected_capacitance_F=math.fsum(c['nominal_F'] for c in dist['capacitors'] if c['source_connected'] and c['ground_to_main']),
        whole_board_distribution_drop_bound_V=None,
        method='Dijkstra sum of full track length/width for each touched trace. Whole track charged even for midpoint contacts. Zero-cost pads/vias; not a resistor network or resistance upper bound. Useful route geometry only.',
        missing=['72 IC supply paths are not connected','Actual board copper thickness/resistivity/temperature and manufacturing width bounds','Pad spreading/via/return-path resistance','Perbranch actual current and simultaneous-state bounds'],
        source_sha256={p.name:sha(p) for p in [HERE/'TBP72-AUX-copper.json',HERE/'TBP72-distribution.json',HERE/'capture-provenance.json',Path(__file__)]})
if __name__=='__main__':
    r=analyze();(HERE/'routes.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ['paths','source_sha256']},indent=2))
    print([(p['ref'],round(p['track_squares_proxy'],3),p['via_objects_on_path']) for p in r['paths']])
