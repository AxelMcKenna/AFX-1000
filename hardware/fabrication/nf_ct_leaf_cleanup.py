"""Prune vacated reference leaves using track centre-lines, not end-cap overlap."""
from shapely.geometry import Point,LineString
from hardware.fabrication.route_nf_surface import shape
REFERENCES={'/N12_P03_SRC','/N19_P03_SRC'}

def prune_leaf_returns(capture):
    active={o['uuid']:o for o in capture['objects']}
    geometry={(o['uuid'],layer):(LineString([o['position_mm'],o['end_mm']]) if o['kind']=='PCB_TRACK' else Point(o['position_mm']) if o['kind']=='PCB_VIA' else shape(polys)) for o in capture['objects'] if o['net'] in REFERENCES for layer,polys in o['layers'].items()}
    removed=[]
    while True:
        selected=None
        for uid,o in active.items():
            if o['net'] not in REFERENCES or o['kind'] not in ('PCB_TRACK','PCB_VIA'):continue
            neighbours=[(k,v) for k,v in active.items() if k!=uid and v['net']==o['net']]
            if o['kind']=='PCB_TRACK':
                layer=next(iter(o['layers']))
                if any(not any(layer in v['layers'] and geometry[k,layer].distance(Point(pt))<.00001 for k,v in neighbours) for pt in [o['position_mm'],o['end_mm']]):
                    selected=uid;break
            else:
                # A via with contacts on fewer than two layers has no remaining
                # interlayer function. Reference nets have no filled zones.
                assert not any(z['net']==o['net'] and not z['keepout'] for z in capture['zones'])
                contact_layers={layer for k,v in neighbours for layer in v['layers'] if geometry[k,layer].distance(Point(o['position_mm']))<.00001}
                if len(contact_layers)<2:
                    selected=uid;break
        if selected is None:break
        removed.append(active.pop(selected))
        assert len(removed)<100,'Unexpectedly broad pruning'
    return list(active.values()),removed

