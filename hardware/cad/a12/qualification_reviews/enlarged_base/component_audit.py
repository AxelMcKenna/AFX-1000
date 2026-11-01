"""Check orientation per connected boundary of each strict existing STL."""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT=Path('/Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/enlarged_base')
OUT=Path(__file__).parent
report=json.loads((ROOT/'generated/verification.json').read_text())
results={}
for name,row in report['cases'].items():
    if row['role']!='production-part':continue
    path=ROOT/'generated'/(name+'.stl')
    data=path.read_bytes(); n=struct.unpack_from('<I',data,80)[0]
    parent=list(range(n)); seen={}; terms=[]
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i in range(n):
        raw=struct.unpack_from('<12fH',data,84+50*i)
        a,b,c=(tuple(raw[k:k+3]) for k in (3,6,9))
        terms.append((a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6)
        for x,y in ((a,b),(b,c),(c,a)):
            key=tuple(sorted((x,y)))
            if key in seen:parent[find(i)]=find(seen[key])
            else:seen[key]=i
    components={}
    for i,t in enumerate(terms):components.setdefault(find(i),[]).append(t)
    volumes=sorted(math.fsum(values) for values in components.values())
    assert all(v>1e-6 for v in volumes),(name,volumes)
    results[name]=dict(sha256=hashlib.sha256(data).hexdigest(),connected_boundary_count=len(volumes),
                       signed_component_volumes_mm3=volumes,all_connected_boundaries_positive=True)
payload=dict(existing_STL_artifacts_only=True,strict_mesh_connected_boundaries=results,
             disconnected_output_groups_are_not_single_fabrication_parts=True,
             no_native_rerun=True,new_qualification_granted=False,
             script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'component-audit-result.json').write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps({k:v['connected_boundary_count'] for k,v in results.items()},indent=2))
