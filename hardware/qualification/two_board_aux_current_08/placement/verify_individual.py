"""Independently check native pose conversion, pin sets and placed courtyards."""
import json,math,hashlib
from pathlib import Path
from shapely.geometry import box
from shapely.affinity import rotate,translate
from .individual import HERE,geometry

def verify(here=HERE,root=None):
    p=json.loads((here/'individual-placement.json').read_text());n=json.loads((here/'native/native-poses.json').read_text())
    assert n['input_proposal_sha256']==hashlib.sha256((here/'individual-placement.json').read_bytes()).hexdigest(),'Stale native proposal'
    poses={q['ref']:q for g in p['groups'].values() for q in g['chosen']['parts']}
    assert len(poses)==18 and set(poses)=={q['ref'] for q in n['poses']},'Wrong native pose set'
    geoms={};maxerr=0
    for q in n['poses']:
        r=q['ref'];pose=poses[r];fp=p['footprints'][r];angle=math.radians(pose['rotation_deg'])
        assert q['footprint_sha256']==fp['source_sha256'],'Native footprint source drift'
        assert q['layer']==pose['layer'] and q['orientation_degrees']%360==pose['kicad_orientation_degrees_after_left_right_flip']
        assert set(q['pads'])==set(fp['pads']),'Wrong native pin set'
        for pin,(x,y) in fp['pads'].items():
            x*=(-1 if pose['layer']=='B.Cu' else 1)
            expected=[pose['at_mm'][0]+x*math.cos(angle)+y*math.sin(angle),pose['at_mm'][1]-x*math.sin(angle)+y*math.cos(angle)]
            err=math.dist(q['pads'][pin],expected);assert err<1e-6,'Native pad coordinate mismatch';maxerr=max(maxerr,err)
        geoms[r]=translate(rotate(box(*fp['bounds_mm']),-pose['rotation_deg'],origin=(0,0)),*pose['at_mm'])
    separation=min(a.distance(b) for i,(ar,a) in enumerate(geoms.items()) for br,b in list(geoms.items())[i+1:] if poses[ar]['layer']==poses[br]['layer'])
    assert separation>=.2-1e-8,'Proposed courtyard overlap'
    if root:
        cap,board,area,obs,target=geometry(root)
        assert p['source_sha256']=={k:v for k,v in cap['source_sha256'].items() if k.endswith('power_protection.kicad_pcb')}
        for r,g in geoms.items():assert area.contains(g) and not obs[poses[r]['layer']].intersects(g),'Proposal hits frozen geometry'
    return {'native_pose_count':len(poses),'maximum_native_pad_error_mm':maxerr,'minimum_proposed_courtyard_separation_mm':separation,'frozen_geometry_checked':bool(root),'qualified_routing':False,'qualified_housing_fit':False}
if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('root',type=Path);r=verify(root=a.parse_args().root);(HERE/'individual-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
