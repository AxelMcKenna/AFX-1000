"""Verify aliases cannot add geometry or relax contacts, and source closure is fresh."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]

def verify(registry):
    assert registry['schema_version']==1
    assert not registry['fabrication_released']
    ids=[c['id']for c in registry['components']];assert len(ids)==len(set(ids))==8
    text=(HERE/'parts.scad').read_text();clean=re.sub(r'//[^\n]*','',text)
    aliases=dict(re.findall(r'module\s+(\w+)\s*\(\s*\)\s*\{\s*(\w+)\s*\(\s*\)\s*;\s*\}',clean))
    remainder=re.sub(r'module\s+\w+\s*\(\s*\)\s*\{\s*\w+\s*\(\s*\)\s*;\s*\}','',clean)
    remainder=re.sub(r'use\s*<[^>]+>','',remainder)
    assert not remainder.strip(),'Adapter contains top-level geometry, overrides, transforms or side effects'
    assert set(aliases)==set(ids)
    actual={}
    def bind(p):
        p=p.resolve();k=str(p.relative_to(REPO))
        if k in actual:return
        actual[k]=hashlib.sha256(p.read_bytes()).hexdigest()
        if p.suffix=='.scad':
            for d in re.findall(r'(?:use|include)\s*<([^>]+)>',p.read_text()):bind(p.parent/d)
    bind(HERE/'parts.scad')
    for key,digest in registry['source_sha256'].items():
        assert hashlib.sha256((REPO/key).read_bytes()).hexdigest()==digest,key
    for key,digest in actual.items():assert registry['source_sha256'][key]==digest,key
    for c in registry['components']:
        assert c['source']==str((HERE/'parts.scad').relative_to(REPO))
        assert c['module']==c['id'] and c['role'] in ['installed','motion','receiving']
        assert c['parameters']=={} and aliases[c['module']]==c['source_module']
        assert re.search(r'\bmodule\s+'+c['source_module']+r'\s*\(\s*\)',(REPO/c['source_definition']).read_text())
    assert registry['runtime_contract']['separate_harness_parts_required']
    assert not registry['runtime_contract']['native_macos_allowed']
    for contact in registry['intentional_contacts']+registry['external_contacts']:
        assert contact['blanket_pair_exclusion'] is False,'Broad contact waiver not allowed'
    topology=registry['electrical_topology'];assert topology['cad_roles']==[] and not topology['physically_routed']
    a=json.loads((REPO/topology['anode']).read_text());g=json.loads((REPO/topology['ground']).read_text())
    assert len(a['nodes'])==topology['anode_splices']==34
    assert len(g['nodes'])==topology['ground_splices']==26
    assert len(a['edges'])+len(g['edges'])==topology['wires']==129
    return dict(roles=len(ids),recursive_scad_sources=len(actual),bound_sources=len(registry['source_sha256']),aliases_are_direct_zero_argument_calls=True,top_level_geometry=False,broad_contact_exclusions=False,unrouted_topology_not_rendered=True)

if __name__=='__main__':
    result=verify(json.loads((HERE/'registry.json').read_text()))
    print(json.dumps(result,indent=2))
