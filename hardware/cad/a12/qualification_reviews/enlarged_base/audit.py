"""Independent read-only EB01 evidence audit. Does not import EB01 code."""
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET
import zipfile

REPO = Path('/Users/axelmckrnna/dev/rmx-publish')
ROOT = REPO / 'hardware/cad/a12/thermal/enlarged_base'
OUT = Path(__file__).parent
EXPECTED = 'daeb19a1f8eb5ae0f07b3f467a0cfcd35384e3e570007d8397b4182cdc8352cf'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mesh(p):
    data = p.read_bytes()
    n = struct.unpack_from('<I', data, 80)[0]
    assert n > 0 and len(data) == 84 + n*50
    edges = collections.Counter()
    zero = 0
    terms = []
    low, high = [math.inf]*3, [-math.inf]*3
    for i in range(n):
        row = struct.unpack_from('<12fH', data, 84 + 50*i)
        a,b,c = (tuple(row[k:k+3]) for k in (3,6,9))
        assert all(math.isfinite(v) for q in (a,b,c) for v in q)
        u = [b[k]-a[k] for k in range(3)]
        v = [c[k]-a[k] for k in range(3)]
        cross = [u[(k+1)%3]*v[(k+2)%3]-u[(k+2)%3]*v[(k+1)%3] for k in range(3)]
        if math.fsum(z*z for z in cross) < 1e-24:
            zero += 1
            continue
        for x,y in ((a,b),(b,c),(c,a)):
            edges[x,y] += 1
        for q in (a,b,c):
            for k in range(3):
                low[k],high[k] = min(low[k],q[k]),max(high[k],q[k])
        terms.append(a[0]*(b[1]*c[2]-b[2]*c[1]) + a[1]*(b[2]*c[0]-b[0]*c[2]) + a[2]*(b[0]*c[1]-b[1]*c[0]))
    bad = sum(count != 1 or edges[y,x] != 1 for (x,y),count in edges.items())
    return dict(triangles=n, zero_area_triangles=zero, bad_directed_edges=bad,
                closed_without_discarding_faces=(zero==0 and bad==0),
                signed_volume_mm3=math.fsum(terms)/6, abs_volume_mm3=abs(math.fsum(terms))/6,
                min_mm=low,max_mm=high)


def j(name):
    return json.loads((ROOT/name).read_text())


def main():
    assert sha(ROOT/'handoff.json') == EXPECTED
    h = j('handoff.json')
    mismatches = [p for p,v in h['files_sha256'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=v]
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()
              and p.name!='handoff.json' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    missing_inventory = sorted(actual-set(h['files_sha256']))
    assert len(h['files_sha256']) == 440 and not mismatches and not missing_inventory
    c = j('capture.json')
    assert len(c['original_sha256']) == len(c['derived_context_sha256']) == 137
    assert all(sha(ROOT/'sources'/n)==v for n,v in c['original_sha256'].items())
    assert all(sha(ROOT/n)==v for n,v in c['derived_context_sha256'].items())
    live_changed = [n for n,v in c['original_sha256'].items() if not (REPO/n).exists() or sha(REPO/n)!=v]
    d,a = j('design.json'),j('generated/analysis.json')
    pins = []
    for x in range(12,323,7):
        for y in range(12,177,7):
            if any(math.dist((x,y),q)<12 for q in d['feet']['centres']): continue
            if any(math.dist((x,y),q)<6 for q in d['shell_fasteners']): continue
            if any(math.dist((x,y),q)<4+math.sqrt(2)*1.5 for q in d['return_support_attachments']['centres']): continue
            pins.append([x,y])
    assert len(pins)==1037 and sorted(pins)==sorted(a['pins']['centres'])
    context_errors=[]
    for n in c['original_sha256']:
        source,derived=ROOT/'sources'/n,ROOT/'context'/n
        if source.suffix!='.scad':
            if source.read_bytes()!=derived.read_bytes():context_errors.append(n)
            continue
        expected=source.read_text().replace(str(REPO),str(ROOT/'context'))
        if source.name=='thermal-base.scad':
            for key,value in [('thermal_pins',a['pins']['centres']),('thermal_feet_xy',d['feet']['centres']),('thermal_shell_bolts',d['shell_fasteners'])]:
                expected,count=re.subn('^'+key+r'=.*?;',key+'='+json.dumps(value)+';',expected,flags=re.M)
                assert count==1
            expected=expected.replace('thermal_round_rect(334,157,7)','thermal_round_rect(334,188.4,7)')
            expected=expected.replace('translate([p[0],p[1],-25.2])cylinder(d=18,h=19,$fn=64);','translate([p[0],p[1],-25.2])difference(){cylinder(d=18,h=19,$fn=64);translate([0,0,6])cylinder(d=2.5,h=13.01,$fn=64);}')
        if expected!=derived.read_text():context_errors.append(n)
    assert not context_errors
    r=j('generated/verification.json')
    groups=collections.Counter(row['role'] for row in r['cases'].values())
    assert len(r['cases'])==42 and set(r['requested_cases'])==set(r['cases'])
    assert groups=={'production-part':7,'empty-collision':23,'positive-control':7,'retained-review-only-group':5}
    assert h['native_receipt_sha256']==sha(ROOT/'generated/verification.json')
    for field in ('input_sha256','artifact_sha256'):
        assert all(sha(ROOT/n)==v for n,v in r[field].items())
    stats={}
    for name,row in r['cases'].items():
        log=(ROOT/'generated'/(name+'.log')).read_text()
        assert not re.search(r'\b(WARNING|ERROR)\b',log,re.I),(name,log)
        assert '--hardwarnings' in row['command'] and 'Manifold' in row['command'] and 'binstl' in row['command']
        assert 'eb_case='+json.dumps(name) in row['command']
        target=ROOT/'generated'/(name+'.stl')
        if row['role']=='empty-collision':
            assert row['returncode']==1 and 'Current top level object is empty.' in log and not target.exists() and row['statistics'] is None
            continue
        assert row['returncode']==0 and 'NoError' in log and target.exists()
        m=mesh(target)
        stats[name]=m
        declared=row['statistics']
        assert m['triangles']==declared['triangles'] and m['zero_area_triangles']==declared['degenerate_triangles_excluded'] and m['bad_directed_edges']==declared['bad_directed_edges']
        assert math.isclose(m['abs_volume_mm3'],declared['volume_mm3'],rel_tol=1e-12,abs_tol=1e-8)
        if row['role']!='retained-review-only-group':
            assert m['closed_without_discarding_faces'] and m['signed_volume_mm3']>0.001,name
        if name in ('front_material_positive_control','new_bolt_material_positive_control','foot_screw_positive_control','interface_positive_control'):
            assert math.isclose(m['abs_volume_mm3'],.008,abs_tol=2e-6)
        elif row['role']=='positive-control': assert m['abs_volume_mm3']>.1
        assert row['errors']==[] and row['clear'] is True
        print('mesh',name,m['triangles'],m['zero_area_triangles'],m['bad_directed_edges'],flush=True)
    assert stats['metal_geometry']==stats['standalone_metal_geometry']
    fused=mesh(ROOT/'generated/assembly_geometry.stl')
    assert not fused['closed_without_discarding_faces']
    asm=j('generated/assembly-manifest.json')
    archive=ROOT/'generated/EB01-whole-unit-component-review.3mf'
    ns='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
    verified_objects={}
    build=[]
    with zipfile.ZipFile(archive) as z:
        with z.open('3D/3dmodel.model') as stream:
            for event,element in ET.iterparse(stream,events=('start','end')):
                if event=='start' and element.tag==ns+'model': assert element.attrib['unit']=='millimeter'
                if event=='end' and element.tag==ns+'item':build.append(dict(element.attrib))
                if event!='end' or element.tag!=ns+'object':continue
                name=element.attrib['name'];record=asm['objects'][name]
                assert name not in verified_objects and int(element.attrib['id'])==record['object_id']
                verts=element.find(ns+'mesh/'+ns+'vertices')
                vertices=[tuple(float(v.attrib[k]) for k in ('x','y','z')) for v in verts]
                ts=element.find(ns+'mesh/'+ns+'triangles')
                data=(ROOT/record['source_path']).read_bytes()
                count=struct.unpack_from('<I',data,80)[0]
                assert count==len(ts)==record['triangles']
                for i,t in enumerate(ts):
                    ix=[int(t.attrib[k]) for k in ('v1','v2','v3')]
                    assert all(0<=v<len(vertices) for v in ix)
                    actual_t=tuple(vertices[v] for v in ix)
                    raw=struct.unpack_from('<12fH',data,84+50*i)
                    expected_t=tuple(tuple(raw[k:k+3]) for k in (3,6,9))
                    assert actual_t==expected_t,(name,i)
                assert sha(ROOT/record['source_path'])==record['source_sha256']
                verified_objects[name]=dict(id=record['object_id'],triangles=count,all_coordinates_and_order_exact=True,new_manufacturing_part_flag=record['new_manufacturing_part'])
                element.clear()
    assert len(verified_objects)==len(build)==10
    assert {int(q['objectid']) for q in build}=={q['id'] for q in verified_objects.values()}
    assert all('transform' not in q for q in build)
    stack=j('interface-stack-review.json')
    g=stack['actual_source_geometry']
    assert math.isclose(g['metal_support_top']+g['nominal_shim'],g['P03_bottom'])
    assert math.isclose(g['thermal_land_top']+g['compressed_TIM_height'],g['P03_bottom'])
    assert math.isclose(stack['nominal_compression_fraction'],1-1.22/1.524)
    calculations=[]
    for z in (6.3,6.5,6.7):
        calculations.append(dict(board_z=z,shim=z-6.3,TIM_compressed=z-5.28,compression_nominal_sheet=1-(z-5.28)/1.524))
    flag_errors=[]
    for name in ('handoff.json','design.json','generated/verification.json','generated/cad-verification.json','generated/assembly-manifest.json','generated/analysis.json','interface-stack-review.json'):
        obj=j(name)
        for key,val in obj.items():
            if key.endswith(('_qualified','_released')) or key in ('build_ready','material_certified','physical_fit_verified'):
                if val is not False:flag_errors.append([name,key,val])
    assert not flag_errors
    findings=[
        dict(id='EB-I01',severity='description/abstraction mismatch',
             observed='Feet assembly removes diameter3.02 for10mm (Z-16.2..-6.19998), versus actual5.8mm screw engagement (tipZ-12).',
             consequence='README/intended-contact wording only engaged interval is inaccurate; manufacturing STEP remains2.5mm pilot. No concealed external collision established.',
             extra_removed_volume_below_actual_tip_per_foot_mm3=math.pi/4*(3.02**2-2.5**2)*4.2),
        dict(id='EB-I02',severity='replay usage/reproducibility defect',
             observed='Documented first replay command stage.py reads LIVE EI/thermal sources and overwrites sealed capture/context/design. It does not replay EB01 sources.',
             consequence='Captured verify/artifact checks can be used without stage. Portable relocation also requires explicit absolute-path rebinding. Current sealed native results are not disproved.'),
        dict(id='EB-I03',severity='assembly-role advisory',
             observed='3MF feet_assembly_geometry is labelled new_manufacturing_part=true although it contains the3.02mm thread fit abstraction; interface object also combines pads/shims.',
             consequence='Use exact independent FOOT STEP for fabrication; review groups are not a fabrication bill of separate parts. Overall fabrication release remains false.'),
    ]
    assert sha(ROOT/'handoff.json')==EXPECTED
    assert all(sha(ROOT/p)==v for p,v in h['files_sha256'].items())
    result=dict(
        audited_handoff_sha256=EXPECTED,source_packet_unchanged=True,
        source_file_sha256={str(ROOT/'handoff.json'):EXPECTED,**{str(ROOT/p):v for p,v in h['files_sha256'].items()}},
        script_sha256=sha(Path(__file__)),file_count=440,all_file_hashes_match=True,unlisted_files=missing_inventory,
        captured_originals=137,derived_contexts=137,derived_changes_exactly_match_declared_rebinding_and_thermal_variant=True,
        live_original_changes_now=live_changed,native_roles=dict(groups),native_case_count=42,native_rows_logs_and_actual_STL_statistics_agree=True,
        independent_mesh_statistics=stats,fused_STL_statistics=fused,fused_mesh_not_valid_as_manufacturing_part=True,
        ten_object_3MF=verified_objects,all_source_triangles_and_global_poses_preserved_exactly=True,
        nominal_TIM_shim_datums_coherent=True,TIM_height_corner_calculations=calculations,
        uniform_fixed_stack_and_pressure_isolation_not_qualified=True,unsupported_release_flags=flag_errors,
        source_E28_scope='fed472/R58ground126.5,45electricalopens; notU14/P9/J8',
        findings=findings,native_reruns_performed=0,new_qualification_granted=False,
    )
    (OUT/'audit-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('file_count','all_file_hashes_match','native_roles','all_source_triangles_and_global_poses_preserved_exactly','findings')},indent=2))


if __name__=='__main__':main()
