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
    assert len(defs)==len(r['components'])==30
    all_src='\n'.join((ROOT/p).read_text() for p in r['source_sha256'] if p.endswith('.scad'))
    modules=set(re.findall(r'module\s+(\w+)\s*\(',all_src))
    for c in r['components']:
        assert tokens(defs[c['module']])==tokens(c['delegate_body']),c['id']
        assert c['role'] in ['installed','motion','receiving']
        for call in re.findall(r'\b((?:tbh\w*|controls_\w+))\s*\(',c['delegate_body']):assert call in modules,call
        if c['role']=='installed':assert not re.search(r'(?:_wires|_wiring|_reserve|_motion|_max|_receiving)\s*\(',c['delegate_body']),c['id']
    by_id={c['id']:c for c in r['components']}
    assert by_id['controls_button_mechanisms']['scene'] is True
    for name in ['controls_switches','controls_retaining_clips']:assert by_id[name]['scene'] is False
    touch=by_id['controls_touch_module_receiving'];binding=touch['capture_binding']
    assert touch['role']=='receiving' and touch['scene'] is False
    cap=json.loads((ROOT/binding['source']).read_text())
    row=next(x for x in cap['context'] if x['id']==binding['context_id'])
    assert row['xy']==binding['xy']==[82,158,135.848,179.844]
    assert row['z']==binding['z']==[17,28]
    x0,y0,x1,y1=row['xy'];z0,z1=row['z']
    expected='module controls_touch_reserve_delegate(){translate('+json.dumps([x0,y0,z0])+')cube('+json.dumps([x1-x0,y1-y0,z1-z0])+');}'
    assert tokens((HERE/'touch_reserve.scad').read_text())==tokens(expected)
    assert len(cap['buttons'])==29
    scope=(HERE/'key_scope.scad').read_text()
    assert 'for(b=buttons)button_pose(b)mechanism(b,0);' in scope
    assert 'translate([74.8,125.8,35.2+panel_z-34])touch_lens();' in scope
    housing=(ROOT/'hardware/cad/two_board_print_01/housing.scad').read_text()
    assert 'H=43.6;' in housing and 'panel_z=H;' in housing
    assert not re.search(r'panel_z\s*=',(ROOT/'hardware/cad/two_board_print_01/captured.scad').read_text())
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
    for mutation in ['missing_instance','installed_wire','changed_delegate','stale_source','duplicate_switch','touch_as_installed','touch_bounds']:
        bad=copy.deepcopy(r)
        if mutation=='missing_instance':bad['pcb_inventory']['instances'].pop()
        elif mutation=='installed_wire':bad['components'][1]['role']='installed'
        elif mutation=='changed_delegate':bad['components'][0]['delegate_body']='tbh04_fasteners();'
        elif mutation=='duplicate_switch':next(c for c in bad['components'] if c['id']=='controls_switches')['scene']=True
        elif mutation=='touch_as_installed':next(c for c in bad['components'] if c['id']=='controls_touch_module_receiving')['role']='installed'
        elif mutation=='touch_bounds':next(c for c in bad['components'] if c['id']=='controls_touch_module_receiving')['capture_binding']['z'][0]=18
        else:bad['source_sha256'][next(iter(bad['source_sha256']))]='0'*64
        try:check(bad)
        except AssertionError:pass
        else:raise AssertionError('Accepted '+mutation)
    result['rejected_mutations']=7
    print(json.dumps(result,indent=2))
