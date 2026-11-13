"""Bind native withdrawal witnesses; failures are expected, never promoted."""
import hashlib
import json
from pathlib import Path
H=Path(__file__).resolve().parent
R=H.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
for revision in ('r1','r2'):
    for case in ('positive','population','controls','sensor','ground_supports'):
        folder=H/'native'/f'{case}-{revision}'
        p=folder/'result.json'
        r=json.loads(p.read_text())
        assert not r['runtime_failure']
        for name,digest in r['source_sha256'].items():
            source=R/name
            if revision=='r1' and source.name in ('service.scad','probe.scad') and source.parent==H:
                source=H/'rejected-r1'/source.name
            assert sha(source)==digest, (revision,case,name)
        expected_collision=(revision,case) in [('r1','population'),('r2','controls')]
        if case=='positive' or expected_collision:
            assert not r['empty'] and r['mesh']['closed_oriented_boundary']
            assert r['mesh']['volume_mm3']>0
        else:
            assert r['empty'] and r['mesh'] is None
        artifacts={str(q.relative_to(R)):sha(q) for q in sorted(folder.iterdir()) if q.is_file()}
        records.append({'revision':revision,'case':case,'empty':r['empty'],'mesh':r['mesh'],'artifact_sha256':artifacts})
a=json.loads((H/'slack-audit.json').read_text())
for name,digest in a['source_sha256'].items(): assert sha(R/name)==digest
assert not a['constant_length_bend_deformation_verified'] and a['completed_touch_wires']==0
out={'status':'DIAGNOSTIC_WITNESSES_VERIFIED_NO_SERVICE_PASS','cases':records,'source_sha256':{str(p.relative_to(R)):sha(p) for p in [Path(__file__),H/'slack-audit.json']}}
(H/'verification.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])
