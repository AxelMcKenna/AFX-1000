"""Separate-object exact-triangle UA01 review; never a fused fabrication mesh."""
import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from hardware.cad.a12.thermal.interior_airpath.assembly import NS, digest, triangles
from hardware.cad.a12.thermal.interior_airpath_meter318.assembly import roundtrip_errors
from .ground_route import ROOT, sha, write

PARENT=ROOT.parents[1]/'thermal/interior_airpath_meter318'
CHANGED={'base_geometry','carrier_geometry','assembly_electronics','assembly_power','assembly_wires'}

def build():
    out=ROOT/'generated'; target=out/'UA01-complete-modeled-component-review.3mf'; copies=out/'review-meshes'
    if target.exists() or copies.exists() or (ROOT/'handoff.json').exists():raise RuntimeError('New review output required')
    parent=json.loads((PARENT/'generated/assembly-manifest.json').read_text())
    parentseal=json.loads((PARENT/'handoff.json').read_text())
    for n,h in parentseal['files_sha256'].items():
        assert sha(PARENT/n)==h,n
    main=json.loads((out/'current-native/verification.json').read_text())
    review=json.loads((out/'review-native/verification.json').read_text())
    for proof in [main,review]:
        assert not proof['changed_inputs']
        for group in ['input_sha256','artifact_sha256']:
            for n,h in proof[group].items():assert sha(Path(n))==h,n
    assert review['all_requested_clear']
    assert [n for n,r in main['cases'].items() if not r['clear']]==['H9_openlid_controls_collision']
    selections={}
    for n,v in parent['objects'].items():
        if n not in CHANGED:selections[n]=(PARENT/v['source_path'],'Unchanged AP03 family: '+v['description'],'AP03 sealed exact mesh reuse')
    for n,case in [('base_geometry','new_base_geometry'),('carrier_geometry','new_carrier_geometry'),('assembly_wires','new_wire_pair_geometry')]:
        selections[n]=(out/'current-native'/(case+'.stl'),'Fresh UA01 '+n,'UA01 current-native')
    selections['assembly_electronics']=(out/'review-native/review_electronics.stl','Fresh P03db83/E28sealed32/R1dc559 both-face PCB/body/port requirements; lowstack','UA01 review-native')
    selections['remaining_power']=(out/'review-native/review_remaining_power.stl','Actual retained H9 head and TC02 fastener receiving requirements','UA01 review-native')
    audit=json.loads((out/'production-mesh-audit.json').read_text())
    for n,v in audit['parts'].items():
        # Three covered/receiving envelopes are NOT additional physical material.
        if n.split('/')[-1].replace('.stl','').endswith(('COVERED-ENVELOPE','SUPPORT-ENVELOPE')):continue
        selections['power_'+n.replace('/','_').replace('.stl','')]=(Path(v['source_path']),'Individual actual CAD part shape; material/process/assembly unqualified','UA01 strict part audit')
    assert len(selections)==70,len(selections) #16 unchanged +5 fresh +49 actual powerparts
    copies.mkdir(); model=ET.Element('model',dict(xmlns=NS,unit='millimeter'));resources=ET.SubElement(model,'resources');build_items=ET.SubElement(model,'build');objects={}
    for i,(n,(origin,desc,evidence)) in enumerate(selections.items(),1):
        path=copies/(n+'.stl');shutil.copyfile(origin,path);tris=triangles(path);verts=[];lookup={};indices=[]
        for tri in tris:
            ids=[]
            for v in tri:
                if v not in lookup:lookup[v]=len(verts);verts.append(v)
                ids.append(lookup[v])
            indices.append(ids)
        o=ET.SubElement(resources,'object',dict(id=str(i),type='model',name=n));m=ET.SubElement(o,'mesh');vs=ET.SubElement(m,'vertices');ts=ET.SubElement(m,'triangles')
        for v in verts:ET.SubElement(vs,'vertex',{k:repr(x) for k,x in zip(['x','y','z'],v)})
        for ids in indices:ET.SubElement(ts,'triangle',{k:str(x) for k,x in zip(['v1','v2','v3'],ids)})
        ET.SubElement(build_items,'item',dict(objectid=str(i)))
        objects[n]=dict(source_path=str(path.relative_to(ROOT)),source_sha256=sha(path),origin_path=str(origin),origin_sha256=sha(origin),description=desc,evidence=evidence,triangles=len(tris),triangle_coordinate_digest=digest(tris),group_or_receiving_mesh_promoted_as_manufacturable=False)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats-package.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
    assert not roundtrip_errors(target,objects)
    write(out/'assembly-manifest.json',dict(objects=objects,unchanged_AP03_families=16,fresh_changed_families=5,individual_power_part_shapes=49,exact_triangle_coordinate_roundtrip_verified=True,deleted_repaired_reoriented_or_decimated_faces=0,complete_currently_modeled_scene_families=True,whole_as_one_manufacturable_part=False,physical_qualified=False,thermal_qualified=False,full_wiring_qualified=False,source_sha256={str(Path(__file__)):sha(Path(__file__)),str(PARENT/'handoff.json'):sha(PARENT/'handoff.json'),str(PARENT/'generated/assembly-manifest.json'):sha(PARENT/'generated/assembly-manifest.json')},artifact_sha256={str(target):sha(target)}))
    print(json.dumps(dict(objects=len(objects),triangles=sum(v['triangles'] for v in objects.values()),sha256=sha(target))))
if __name__=='__main__':build()
