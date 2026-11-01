"""Complete AP03 component review, explicitly reusing16 unchanged AP02 meshes."""

import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from hardware.cad.a12.thermal.interior_airpath.assembly import GROUPS, NS, digest, triangles

from .stage import OUT, PARENT, ROOT, require_parent, sha, write

ET.register_namespace("",NS)
CHANGED={"base_geometry","tray_geometry","assembly_all_gaskets","assembly_meter_hardware","feedthrough_receiving_geometry"}


def roundtrip_errors(path,objects):
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read("3D/3dmodel.model"))
    actual=root.findall(f"{{{NS}}}resources/{{{NS}}}object")
    if {o.attrib["name"] for o in actual}!=set(objects):
        return ["missing-or-duplicated-review-family"]
    items=root.findall(f"{{{NS}}}build/{{{NS}}}item")
    if len(items)!=len(objects) or any("transform" in item.attrib for item in items):
        return ["review-object-transform-or-coverage"]
    bad=[]
    for obj in actual:
        name=obj.attrib["name"]
        m=obj.find(f"{{{NS}}}mesh")
        vs=[tuple(float(v.attrib[k]) for k in ["x","y","z"]) for v in m.find(f"{{{NS}}}vertices")]
        tris=[tuple(vs[int(t.attrib[k])] for k in ["v1","v2","v3"]) for t in m.find(f"{{{NS}}}triangles")]
        if len(tris)!=objects[name]["triangles"] or digest(tris)!=objects[name]["triangle_coordinate_digest"]:
            bad.append("changed-source-triangles:"+name)
    return bad


def build():
    target=OUT/"AP03-complete-modeled-component-review.3mf"
    copies=OUT/"review-meshes"
    if target.exists() or copies.exists() or (ROOT/"handoff.json").exists():
        raise RuntimeError("New complete-review destination required")
    require_parent()
    parent_proof=PARENT/"generated/current-native/verification.json"
    main_proof=OUT/"current-native/verification.json"
    extra_proof=OUT/"review-exports/verification.json"
    proofs={str(p):json.loads(p.read_text()) for p in [parent_proof,main_proof,extra_proof]}
    for p,d in proofs.items():
        if not d["all_requested_clear"] or d["changed_inputs"]:
            raise RuntimeError("Failed native proof: "+p)
        for k in ["input_sha256","artifact_sha256"]:
            if any(sha(Path(n))!=v for n,v in d[k].items()):
                raise RuntimeError("Stale native proof")
    copies.mkdir()
    model=ET.Element("model",dict(xmlns=NS,unit="millimeter"))
    resources=ET.SubElement(model,"resources")
    build_items=ET.SubElement(model,"build")
    objects={}
    for i,(name,old_description) in enumerate(GROUPS.items(),1):
        if name in ["base_geometry","tray_geometry"]:
            proof_path=main_proof
        elif name in CHANGED:
            proof_path=extra_proof
        else:
            proof_path=parent_proof
        proof=proofs[str(proof_path)]
        origin=proof_path.parent/(name+".stl")
        path=copies/(name+".stl")
        shutil.copyfile(origin,path)
        tris=triangles(path)
        seen={}
        verts=[]
        indices=[]
        for tri in tris:
            ids=[]
            for v in tri:
                if v not in seen:
                    seen[v]=len(verts)
                    verts.append(v)
                ids.append(seen[v])
            indices.append(ids)
        obj=ET.SubElement(resources,"object",dict(id=str(i),type="model",name=name))
        m=ET.SubElement(obj,"mesh")
        vs=ET.SubElement(m,"vertices")
        for v in verts:
            ET.SubElement(vs,"vertex",{k:repr(x) for k,x in zip(["x","y","z"],v)})
        ts=ET.SubElement(m,"triangles")
        for ids in indices:
            ET.SubElement(ts,"triangle",{k:str(x) for k,x in zip(["v1","v2","v3"],ids)})
        ET.SubElement(build_items,"item",dict(objectid=str(i)))
        description={"base_geometry":"AP03actualbase899pins;19wholepinremovalonlyvsAP02",
            "tray_geometry":"AP03rearwalltranslated5mm;integralbaytray",
            "assembly_all_gaskets":"AP03translated/enlargedrearwallgaskets;nominalcompressionrequirements",
            "assembly_meter_hardware":"AP03two16x10R1meters+translatedM2hardware;flowunverified",
            "feedthrough_receiving_geometry":"AP03translatedFULLYFILLEDlead/resinreceivers;actualprocessunselected"}.get(name,old_description)
        objects[name]=dict(description=description,source_path=str(path.relative_to(ROOT)),source_sha256=sha(path),
            origin_path=str(origin),origin_sha256=sha(origin),native_proof=str(proof_path),
            native_proof_sha256=sha(proof_path),native_statistics=proof["cases"][name]["statistics"],
            source_role=proof["cases"][name]["role"],
            unchanged_parent_mesh_reused=name not in CHANGED,triangles=len(tris),
            triangle_coordinate_digest=digest(tris),group_or_receiving_mesh_promoted_as_manufacturable=False)
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels",'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model",ET.tostring(model,encoding="utf-8",xml_declaration=True))
    bad=roundtrip_errors(target,objects)
    if bad:
        raise RuntimeError(bad)
    write(OUT/"assembly-manifest.json",dict(objects=objects,unchanged_parent_families=16,fresh_changed_families=5,
          source_sha256={"assembly.py":sha(ROOT/"assembly.py")},artifact_sha256={target.name:sha(target)},
          exact_triangle_coordinate_roundtrip_verified=True,deleted_repaired_or_decimated_faces=0,
          complete_currently_modeled_scene_families=True,whole_as_one_manufacturable_part=False,
          physical_qualified=False,thermal_qualified=False,full_wiring_qualified=False))
    print(json.dumps(dict(objects=len(objects),triangles=sum(o["triangles"] for o in objects.values()),sha256=sha(target))))


if __name__=="__main__":
    build()
