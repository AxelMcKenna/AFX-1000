"""Find mutually compatible local escapes using full pair graphs and propagation."""
import itertools
from hardware.fabrication.digital_serial1_joint_escape_survey import compatible


def pack(domains, limit=64, predicate=compatible):
    assert limit>0
    names=list(domains)
    assert len({domains[n]['net'] for n in names})==len(names)
    options=[domains[n]['options'] for n in names]
    edges={};counts={}
    for i,j in itertools.combinations(range(len(names)),2):
        forward={a:set() for a in range(len(options[i]))}
        reverse={b:set() for b in range(len(options[j]))}
        for a,left in enumerate(options[i]):
            for b,right in enumerate(options[j]):
                if predicate(left,right):forward[a].add(b);reverse[b].add(a)
        edges[i,j]=forward;edges[j,i]=reverse
        counts[names[i]+' / '+names[j]]=sum(map(len,forward.values()))
    selected=[];seen=set();visited=0;stopped=False
    def search(chosen,allowed):
        nonlocal visited,stopped
        visited+=1
        if len(chosen)==len(names):
            indices=[chosen[i] for i in range(len(names))]
            key=tuple(tuple(round(v,1) for v in options[i][a]['point']) for i,a in enumerate(indices))
            if key not in seen:
                seen.add(key);selected.append(dict(indices=indices,cost=sum(options[i][a]['cost'] for i,a in enumerate(indices))))
            if len(selected)>=limit:stopped=True
            return
        remaining=[i for i in range(len(names)) if i not in chosen]
        i=min(remaining,key=lambda k:len(allowed[k]))
        for a in sorted(allowed[i],key=lambda k:(options[i][k]['cost'],k)):
            next_allowed={j:allowed[j]&edges[i,j][a] for j in remaining if j!=i}
            if any(not v for v in next_allowed.values()):continue
            search({**chosen,i:a},next_allowed)
            if stopped:return
    if all(options):search({}, {i:set(range(len(rows))) for i,rows in enumerate(options)})
    selected.sort(key=lambda r:r['cost'])
    return dict(names=names,pair_compatible_counts=counts,choices=selected,
                visited_search_nodes=visited,complete_enumeration=not stopped,
                spatial_bin_mm=.1,maximum_distinct_packs=limit)
