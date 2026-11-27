"""A closed boundary after facet exclusion must still fail the clean-positive gate."""
import copy,hashlib,json
from pathlib import Path
from hardware.cad.two_board_installation_06.r41_left_inputs.positive_gate import require_clean_positive
H=Path(__file__).resolve().parent;R=H.parents[3]
p=H/'native/positive_clearance-r10/result.json';baseline=json.loads(p.read_text());require_clean_positive(baseline)
rejected=[]
for name,key,value in [('one_degenerate','degenerate_triangles_excluded',1),('fourteen_degenerate','degenerate_triangles_excluded',14),('bad_directed_edge','bad_directed_edges',1),('open_boundary','closed_oriented_boundary',False),('zero_volume','volume_mm3',0)]:
 changed=copy.deepcopy(baseline);changed['mesh'][key]=value
 try:require_clean_positive(changed)
 except AssertionError:rejected.append(name)
 else:raise AssertionError('Invalid positive accepted: '+name)
sources=[Path(__file__),H/'positive_gate.py',p]
out={'clean_r10_positive_accepted':True,'rejected':rejected,'source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
(H/'positive-gate-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(rejected))
