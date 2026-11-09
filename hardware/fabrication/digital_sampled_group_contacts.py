"""Add attachment points along native-connected target tracks, not just endpoints."""
import math
from hardware.fabrication.digital_native_route_cleanup import other_group_contacts

def contacts(capture,source,faces,step_mm=.2):
    assert 0 < step_mm <= .2
    result=other_group_contacts(capture,source,faces)
    for obj in capture['objects']:
        if obj['net']!=source['net'] or obj['group']==source['group'] or obj['kind']!='PCB_TRACK':continue
        assert obj['group'] is not None
        a,b=obj['position_mm'],obj['end_mm'];count=max(1,math.ceil(math.dist(a,b)/step_mm))
        for i in range(1,count):
            point=tuple(round(x+(y-x)*i/count,6) for x,y in zip(a,b))
            result.update((f,point) for f in faces if obj['layers'].get(f))
    return result
