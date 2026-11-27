"""Audit selected group coverage and screen remaining main-population interactions."""
import itertools,json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent

def run():
    prev=HERE/'previous-manifest.json'
    if not prev.exists():prev.write_bytes((w.HERE/'current.json').read_bytes())
    m,c,k,_=w.load_manifest(prev);bounds={};sources=dict(m['_loaded_sources']);sources[w.relative(Path(__file__))]=w.sha(Path(__file__))
    covered={tuple(sorted((a,b))) for q in k.values() for a in q['left'] for b in q['right']}
    for n,x in c.items():
        identity,folder=w.job('component',x,c);r=w.cached(identity,folder);assert r and r['passed'],n
        w.assert_current(identity);bounds[n]=r['mesh'];sources[w.relative(folder/'result.json')]=w.sha(folder/'result.json')
    rows=[]
    for a,b in itertools.combinations(sorted(bounds),2):
        if any(c[x]['role']=='installed' and not c[x].get('scene',True) for x in [a,b]):continue
        if (a,b) in covered or a.split('_')[0]==b.split('_')[0]:continue
        A,B=bounds[a],bounds[b];span=[min(A['max_mm'][i],B['max_mm'][i])-max(A['min_mm'][i],B['min_mm'][i]) for i in range(3)]
        if min(span)>0:rows.append({'a':a,'b':b,'bbox_overlap_mm':span})
    (HERE/'audit.json').write_text(json.dumps({'source_sha256':sources,'cross_family_bbox_overlap_pairs_not_in_current_checks':rows,'not_a_collision_finding':True,'local_frozen_evidence_not_yet_mapped':True,'fabrication_released':False},indent=2)+'\n')
    candidate=json.loads(prev.read_text());candidate['checks']=[]
    for prefix in ['controls_','sensor_','cooling_']:
        right=sorted({r['b'] for r in rows if r['a']=='base_component_allocations' and r['b'].startswith(prefix)})
        assert right
        candidate['checks'].append({'id':'coverage_main_population_'+prefix[:-1],'left':['base_component_allocations'],'right':right,'expect':'empty'})
    (HERE/'candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    w.load_manifest(HERE/'candidate.json');print(len(rows),'pairs need mapping to local proof or new checks; three main-population groups prepared')
if __name__=='__main__':run()
