"""Use native pad groups as routing targets and omit unused signal vias."""
import copy,math
from shapely.geometry import Point,LineString
from hardware.fabrication.route_nf_surface import shape

def other_group_contacts(capture, source, faces):
    assert source['group'] is not None
    objects=[o for o in capture['objects'] if o['net']==source['net'] and o['group']!=source['group']]
    assert objects and all(o['group'] is not None for o in objects)
    return {(f,tuple(p)) for o in objects for f in faces if o['layers'].get(f)
            for p in [o['position_mm']]+([o['end_mm']] if o['kind']=='PCB_TRACK' else [])}

def prune_single_face_vias(capture, routes):
    result=copy.deepcopy(routes);removed=[]
    for route in result:
        keep=[];net=route['net']
        assert net not in {'AGND','5V_DIG','V3V3_IO'}
        for p in route['new_vias_mm']:
            point=Point(p)
            # Overlapping same-net barrels may have indirect multilayer use;
            # retain those rather than inferring their connectivity here.
            neighbours=[q for r in routes if r['net']==net for q in r['new_vias_mm'] if 1e-7<math.dist(p,q)<.601]
            neighbours += [o['position_mm'] for o in capture['objects'] if o['net']==net and o['kind']=='PCB_VIA' and math.dist(p,o['position_mm'])<.601]
            faces={f for r in routes if r['net']==net for f,path in r['runs'] if LineString(path).distance(point)<=.400001}
            faces |= {f for o in capture['objects'] if o['net']==net and o['kind']!='PCB_VIA' for f,ps in o['layers'].items() if ps and shape(ps).distance(point)<=.300001}
            if len(faces)>1 or neighbours:
                keep.append(p)
            else:
                assert len(faces)==1
                removed.append(dict(net=net,point_mm=p,only_connected_layer=next(iter(faces))))
        route['new_vias_mm']=keep
    return result,removed
