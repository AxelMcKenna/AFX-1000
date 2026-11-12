"""Verify frozen source closure, exact delegation and inventory without CAD launch."""
import collections,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def tokens(s):return re.findall(r'\w+|[^\s]',re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S))
def check(r):
    for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    for p in r['source_sha256']:
        path=ROOT/p
        if path.suffix=='.scad':
            for dep in re.findall(r'\b(?:use|include)\s*<([^>]+)>',path.read_text()):
                assert str((path.parent/dep).resolve().relative_to(ROOT)) in r['source_sha256'],dep
        elif path.suffix=='.kicad_sch':
            for dep in re.findall(r'\(property \"Sheetfile\" \"([^\"]+)\"',path.read_text()):
                assert str((path.parent/dep).resolve().relative_to(ROOT)) in r['source_sha256'],dep
    text=(HERE/'controls.scad').read_text(); defs={}
    for m in re.finditer(r'module\s+(\w+)\s*\(\)\s*\{',text):
        start=m.end(); n=1; end=start
        while n:
            n+=(text[end]=='{')-(text[end]=='}');end+=1
        defs[m[1]]=text[start:end-1]
    assert len(defs)==len(r['components'])==26
    all_src='\n'.join((ROOT/p).read_text() for p in r['source_sha256'] if p.endswith('.scad'))
    modules=set(re.findall(r'module\s+(\w+)\s*\(',all_src))
    for c in r['components']:
        assert tokens(defs[c['module']])==tokens(c['delegate_body']),c['id']
        assert c['role'] in ['installed','motion','receiving']
        for call in re.findall(r'\b((?:tbh\w*|controls_\w+))\s*\(',c['delegate_body']):assert call in modules,call
        if c['role']=='installed':assert not re.search(r'(?:_wires|_wiring|_reserve|_motion|_max|_receiving)\s*\(',c['delegate_body']),c['id']
    inv=r['pcb_inventory']; designs=inv['designs']; instances=inv['instances']
    assert len(instances)==34 and len(designs)==12
    assert len({x['instance'] for x in instances})==34
    assert collections.Counter(x['pcb'] for x in instances)=={x['path']:x['quantity'] for x in designs}
    for x in designs:assert hashlib.sha256((HERE.parent/x['path']).read_bytes()).hexdigest()==x['sha256']
    for key in ['project','schematic']:assert r['panel_electrical'][key] in r['source_sha256']
    return {'components':len(defs),'source_files':len(r['source_sha256']),'physical_control_pcbs':34,'designs':12,'delegation':'exact token equality','geometry_qualification':False}
if __name__=='__main__':
    r=json.loads((HERE/'registry.json').read_text());result=check(r)
    import copy
    for mutation in ['missing_instance','installed_wire','changed_delegate','stale_source']:
        bad=copy.deepcopy(r)
        if mutation=='missing_instance':bad['pcb_inventory']['instances'].pop()
        elif mutation=='installed_wire':bad['components'][1]['role']='installed'
        elif mutation=='changed_delegate':bad['components'][0]['delegate_body']='tbh04_fasteners();'
        else:bad['source_sha256'][next(iter(bad['source_sha256']))]='0'*64
        try:check(bad)
        except AssertionError:pass
        else:raise AssertionError('Accepted '+mutation)
    result['rejected_mutations']=4
    print(json.dumps(result,indent=2))
