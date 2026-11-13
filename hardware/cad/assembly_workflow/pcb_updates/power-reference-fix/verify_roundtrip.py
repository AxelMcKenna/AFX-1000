"""Compare retained native roundtrip evidence without weakening the shared bridge."""
import collections,copy,gzip,hashlib,json,tempfile
from pathlib import Path
from hardware.cad.two_board_installation_06.workflow_adapter import pcb_freshness as bridge
ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
NATIVE=HERE/'native-roundtrip'
sha=lambda data:hashlib.sha256(data).hexdigest()
def main():
    audit=json.loads((HERE/'audit.json').read_text());capture=json.loads((NATIVE/'capture.json').read_text());manifest=json.loads((NATIVE/'input-manifest.json').read_text());process=json.loads((NATIVE/'process.json').read_text())
    assert process['exit_code']==0 and not process['timeout']
    assert capture['script_sha256']==manifest['capture.py']==sha((NATIVE/'capture.py').read_bytes())
    snapshots={}
    with tempfile.TemporaryDirectory() as tmp:
        for label,key in [('before','baseline'),('after','candidate')]:
            r=capture['boards'][label];assert r['input_sha256']==manifest[label+'.kicad_pcb']==sha((ROOT/audit[key]).read_bytes())
            compressed=(NATIVE/(label+'.kicad_pcb.gz')).read_bytes();assert sha(compressed)==r['gzip_sha256'];data=gzip.decompress(compressed);assert sha(data)==r['saved_sha256']
            p=Path(tmp)/(label+'.kicad_pcb');p.write_bytes(data);snapshots[label]=bridge.snapshot(p)
    differences=bridge.compare(snapshots['before'],snapshots['after'])
    physical=[d for d in differences if d['field']=='physical']
    key=lambda rows:collections.Counter(json.dumps(x,sort_keys=True) for x in rows)
    order=[d['ref'] for d in physical if key(d['before'])==key(d['after'])]
    residual=[d for d in physical if d['ref'] not in order]
    assert [d['ref'] for d in residual]==['E_C13']
    moved=residual[0];expected=copy.deepcopy(moved['before']);changed=0
    for child in expected:
        if isinstance(child,list) and child[0] in ('pad','fp_text'):
            at=next(x for x in child if isinstance(x,list) and x[0]=='at')
            assert len(at)==4 and at[3]=='180'
            at[3]='90';changed+=1
    assert changed==3 and key(expected)==key(moved['after']), 'Unexpected physical difference beyond exact E_C13 rotation'
    assert snapshots['before']['footprints']['E_C13']['pose']==[97.0,127.5,180.0,'F.Cu']
    assert snapshots['after']['footprints']['E_C13']['pose']==[108.275,129.095,90.0,'F.Cu']
    report={'native_E_C13_physical_change_exactly_three_absolute_angles':True,'native_version':capture['native_version'],'source_sha256':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [Path(__file__),HERE/'audit.json',NATIVE/'capture.json',NATIVE/'input-manifest.json',NATIVE/'process.json',Path(bridge.__file__)]},'counts_by_field':dict(collections.Counter(d['field'] for d in differences)),'native_order_only':order,'residual_physical_changes':residual,'all_differences':differences,'selected':False,'geometry_equivalence_qualified':False}
    (HERE/'roundtrip-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native differences:',report['counts_by_field'],'order-only:',len(order),'residual:',[d['ref'] for d in residual])
if __name__=='__main__':main()
