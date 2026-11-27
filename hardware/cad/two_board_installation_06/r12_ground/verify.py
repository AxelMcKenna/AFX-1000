"""Independent connectivity and swept-polyline separation checks."""
from pathlib import Path
import json, math, hashlib, copy
from collections import Counter, defaultdict
import numpy as np
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def distance(a,b,c,d):
    a,b,c,d=map(np.array,(a,b,c,d));u=b-a;v=d-c;w=a-c
    A=float(u@u);B=float(u@v);C=float(v@v);D=float(u@w);E=float(v@w)
    clamp=lambda n:max(0,min(1,n))
    candidates=[(0,clamp(E/C)),(1,clamp((B+E)/C)),(clamp(-D/A),0),(clamp((B-D)/A),1)]
    den=A*C-B*B
    if den>1e-12:
        t,s=(B*E-C*D)/den,(A*E-B*D)/den
        if 0<=t<=1 and 0<=s<=1:candidates.append((t,s))
    return min(float(np.linalg.norm(w+t*u-s*v)) for t,s in candidates)

def audit(g,contract):
    expected={'button_'+r['id']+':3':r['signal']['reference'] for r in contract['front_inputs'] if r['receiver_kind']=='B3F-1000 momentary'}
    expected.update({'settings:W2.1':'D_J2003','release:W3.1':'D_J2003'})
    assert len(expected)==31 and len(g['edges'])==32 and len(g['splices'])==1
    count=Counter(p for e in g['edges'] for p in (e['from'],e['to']))
    assert set(count.values())=={1},'multiple wires on a contact'
    graph=defaultdict(set)
    def link(a,b):graph[a].add(b);graph[b].add(a)
    for e in g['edges']:link(e['from'],e['to'])
    expected_links={('button_'+r['id']+':3','button_'+r['id']+':4') for r in contract['front_inputs'] if r['receiver_kind']=='B3F-1000 momentary'}
    assert set(map(tuple,g['internal_links']))==expected_links
    for a,b in g['internal_links']:link(a,b)
    for p in ('OUT_A','OUT_B'):link('GROUND_SCENE:IN','GROUND_SCENE:'+p)
    actual={}
    for root in ('D_J2001:15','D_J2001:16','D_J2002:15','D_J2002:16','D_J2003:1'):
        visited=set();todo=[root]
        while todo:
            n=todo.pop()
            if n in visited:continue
            visited.add(n);todo.extend(graph[n]-visited)
        assert {n for n in visited if n.startswith('D_J')}=={root},'ground roots joined in harness'
        for n in visited & set(expected):
            assert n not in actual;actual[n]=root
    assert {k:v.split(':')[0] for k,v in actual.items()}==expected
    for e in g['edges']:
        assert e['points_mm'][0]==g['endpoints_mm'][e['from']]
        assert e['points_mm'][-1]==g['endpoints_mm'][e['to']]
    return actual

def main():
    g=json.loads((HERE/'ground-routes.json').read_text());c=json.loads((HERE.parent/'r11_distribution/reference/panel-contract.json').read_text())
    assert all(sha(REPO/p)==h for p,h in g['source_sha256'].items())
    actual=audit(g,c);bad=copy.deepcopy(g);bad['internal_links'][0][1]=bad['internal_links'][0][1].replace(':4',':1')
    try:audit(bad,c)
    except AssertionError:mutation='rejected'
    else:raise AssertionError('Wrong contact pair accepted')
    bad=copy.deepcopy(g);bad['edges'][1]['from']=bad['edges'][0]['from']
    try:audit(bad,c)
    except AssertionError:contact_mutation='rejected'
    else:raise AssertionError('Double wire contact accepted')
    minimum=999;clashes=[]
    for i,a in enumerate(g['edges']):
        for b in g['edges'][i+1:]:
            gap=min(distance(aa,ab,ba,bb) for aa,ab in zip(a['points_mm'],a['points_mm'][1:]) for ba,bb in zip(b['points_mm'],b['points_mm'][1:]))
            minimum=min(minimum,gap)
            if gap<1.2-1e-8:clashes.append({'wires':[a['id'],b['id']],'centerline_distance_mm':gap})
    out={'source_sha256':{str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),HERE/'ground-routes.json',HERE/'routes.scad']},'electrical_graph_pass':True,'receiver_roots':actual,'wire_count':32,'splice_count':1,'wrong_pair_mutation':mutation,'double_contact_mutation':contact_mutation,'minimum_centerline_distance_mm':minimum,'required_centerline_distance_mm':1.2,'wire_collisions':clashes,'polyline_separation_pass':not clashes,'bend_formation_qualified':False,'support_retention_qualified':False,'fabrication_released':False}
    (HERE/'verification.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('source_sha256','receiver_roots')}))
    return 0 if not clashes else 1
if __name__=='__main__':raise SystemExit(main())
