"""Shorten a routed polyline only along independently screened shortcuts."""
import math


def simplify(screen, net, result):
    runs = []
    for face, path in result['runs']:
        costs, parents = [0.] + [math.inf]*(len(path)-1), {}
        for j in range(1,len(path)):
            for i in range(j-1,-1,-1):
                cost = costs[i]+math.dist(path[i],path[j])
                if cost >= costs[j]-1e-10:
                    continue
                if screen.legal(net,face,[path[i],path[j]]):
                    costs[j],parents[j] = cost,i
            assert j in parents, 'Original route contains an illegal segment'
        index = len(path)-1
        short = [path[index]]
        while index:
            index = parents[index]
            short.append(path[index])
        short.reverse()
        assert screen.legal(net,face,short)
        runs.append((face,short))
    return dict(runs=runs,vias=result['vias'])
