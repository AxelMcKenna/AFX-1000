"""Predict all same-net contacts, including pads crossed between route endpoints."""
import json
from pathlib import Path
from shapely.geometry import LineString
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape

PLAN=STAGING/'two-board-aux-local-distribution-plan-01/plan.json'
CAP=STAGING/'two-board-power-routing-inputs-control-corridors-04/capture.json'
OUT=STAGING/'two-board-aux-local-distribution-plan-02'

def run():
    assert not OUT.exists()
    p,c=[json.loads(f.read_text()) for f in [PLAN,CAP]]
    for data in [p,c]:
        for n,h in data['source_sha256'].items():
            f=Path(n);assert sha(f if f.is_absolute() else REPO/f)==h,n
    parent={g:g for g in c['all_groups']}
    def root(g):
        while parent[g]!=g:g=parent[g]
        return g
    joins=[];contacts=[]
    def merge(a,b,net):
        x,y=root(a),root(b)
        if x==y:return False
        parent[y]=x;joins.append(dict(net=net,source_groups=[a,b]));return True
    for r in p['routes']:merge(*r['source_groups'],r['net'])
    endpoint_only=len(joins)
    bands=[LineString(r['path_mm']).buffer(r['width_mm']/2) for r in p['routes']]
    for i,(r,band) in enumerate(zip(p['routes'],bands)):
        source=r['source_groups'][0]
        for o in c['objects']:
            if o['net']!=r['net'] or r['layer'] not in o['layers']:continue
            area=band.intersection(shape(o['layers'][r['layer']])).area
            if area>1e-9 and merge(source,o['group'],r['net']):
                contacts.append(dict(route_index=i,contact_uuid=o['uuid'],ref=o.get('ref'),pin=o.get('pin'),intersection_mm2=area,source_group=o['group']))
        for j,other in enumerate(p['routes'][:i]):
            if other['net']==r['net'] and other['layer']==r['layer'] and band.intersection(bands[j]).area>1e-9 and merge(source,other['source_groups'][0],r['net']):
                contacts.append(dict(route_index=i,other_route_index=j))
    # Regression: endpoint-only bookkeeping missed the tied MR input beneath route4.
    assert endpoint_only==p['expected_closed_connections']==33
    assert len(joins)==34 and len(contacts)==1
    assert (contacts[0]['route_index'],contacts[0]['ref'],contacts[0]['pin'])==(4,'P_U201','3')
    p.update(joins=joins,expected_closed_connections=len(joins),endpoint_only_connections=endpoint_only,additional_same_net_contacts=contacts,source_sha256={str(f.relative_to(REPO)):sha(f) for f in [Path(__file__),PLAN,CAP,REPO/'hardware/fabrication/route_nf_surface.py']})
    OUT.mkdir();(OUT/'plan.json').write_text(json.dumps(p,indent=2)+'\n')
    print('33 endpoint joins plus explicit P_U201.3 contact;34 predicted merges')

if __name__=='__main__':run()
