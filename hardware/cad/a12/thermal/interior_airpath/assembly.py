"""AP02 complete currently modeled scene families as separate3MF objects.

No triangle is deleted, decimated, moved, repaired or reoriented. Receiving
envelopes/composites and joined review meshes are not manufacturable parts.
"""

import hashlib
import json
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .stage import OUT, ROOT, sha, write

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", NS)
GROUPS = {
    "base_geometry": "Actual334x188.4plate,918wholepins,4retainedthermal lands,10supports,actualholesandnewairinlets",
    "carrier_geometry": "Actualventedplasticcarrier+H9+bothTC02posts,oldmount/seatinterfacesretained",
    "assembly_lid": "HT01round9.5bores+namedblindlugpockets;panelstrength/printunapproved",
    "assembly_rear": "Capturedrearinterfacewithall8audioZ14;actualconnectormatesunqualified",
    "assembly_feet": "Fouractualfootreceivingassemblies/SJ5312andM3x20retainers;nominal104overall",
    "assembly_lower_hardware": "Nineexistinglowercasebolts/nuts;sourcehardwareenvelopesandseats",
    "assembly_electronics": "CapturedbothfacePCB/component/portrequirements;P03db83/E28fed45/E19oldR1central3b2;notlatestunit",
    "assembly_controls": "Actualcurrentlymodeledlever/buttons/switches/optics/HTknobs;loosewiringnotcomplete",
    "assembly_pots": "16sqreceivingbody/substrate/tailreserves+HTbushing/shaft/hardwareandALL10lugs;notvendorCAD",
    "assembly_power": "Capturedreturn/positivebars/insulation/retention,H9andTCheads;noPB02adoption",
    "assembly_wires": "Acceptedcapturedsource-to-J13routeandjointrequirements;nooperatingfanlead/fullunitwiringclaim",
    "assembly_TIM_shims": "Actual4originalTIMand10matchednominal.2supports;compression/isolationunqualified",
    "assembly_foot_spacers": "Fourunchanged8mmloweredfootstackspacers;structuralapprovalfalse",
    "tray_geometry": "Actualtray+twointegralpressurebays+recessedseal/hardstopgeometry;rejected16zerofacettrialpreserved",
    "guard_geometry": "Twoactual7slotguards,868.200mm2neteach;nofinger/strength/protectionapproval",
    "fan_receiving_geometry": "FILLED40.5maxSunonframeenvelopes,10.4nomCADclampheight;notvendorrotorCADorCFD",
    "shim_geometry": "Twoexactcommonendlandderived2.1nomshimswith4.4custombores;matched2..2.5requirements",
    "assembly_all_gaskets": "ActualnominalcompressedBISCOsealrequirements;customconversion/contact/creep/leaknotapproved",
    "assembly_fan_fasteners": "M3x20panheadreceivinggauges+washers/nuts;directheadseal;nomunderheadZ-28.2",
    "assembly_meter_hardware": "Tworeplaceable6.25x10meterplates+M2hardware;125mm2totalisnotacalibratedflowratio",
    "feedthrough_receiving_geometry": "OPAQUEfullyfilledlead/resinreceivingcomposites;actualwireOD/resin/retention/leakprocessunselected",
}


def triangles(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count
    result = []
    for i in range(count):
        row = struct.unpack_from("<12fH", data, 84 + i * 50)
        result.append((row[3:6], row[6:9], row[9:12]))
    return result


def digest(tris):
    result = hashlib.sha256()
    for tri in tris:
        result.update(struct.pack("<9d", *(value for p in tri for value in p)))
    return result.hexdigest()


def build():
    target = OUT / "AP02-complete-modeled-component-review.3mf"
    if (ROOT / "handoff.json").exists() or target.exists():
        raise RuntimeError("Component review output is immutable")
    proof = json.loads((OUT / "current-native/verification.json").read_text())
    if not proof["complete_set"] or not proof["all_requested_clear"] or proof["changed_inputs"]:
        raise RuntimeError("Complete current native screening is required")
    for key in ["input_sha256", "artifact_sha256"]:
        for n, expected in proof[key].items():
            assert sha(Path(n)) == expected, n
    model = ET.Element("model", dict(xmlns=NS, unit="millimeter"))
    resources = ET.SubElement(model, "resources")
    build_items = ET.SubElement(model, "build")
    objects = {}
    for i, (name, description) in enumerate(GROUPS.items(), 1):
        path = OUT / "current-native" / (name + ".stl")
        tris = triangles(path)
        verts = []
        seen = {}
        indices = []
        for tri in tris:
            ids = []
            for v in tri:
                if v not in seen:
                    seen[v] = len(verts)
                    verts.append(v)
                ids.append(seen[v])
            indices.append(ids)
        obj = ET.SubElement(resources, "object", dict(id=str(i), type="model", name=name))
        mesh = ET.SubElement(obj, "mesh")
        vs = ET.SubElement(mesh, "vertices")
        for v in verts:
            ET.SubElement(vs, "vertex", {k: repr(x) for k, x in zip(["x", "y", "z"], v)})
        ts = ET.SubElement(mesh, "triangles")
        for ids in indices:
            ET.SubElement(ts, "triangle", {k: str(x) for k, x in zip(["v1", "v2", "v3"], ids)})
        ET.SubElement(build_items, "item", dict(objectid=str(i)))
        objects[name] = dict(
            description=description,
            source_path=str(path.relative_to(ROOT)),
            source_sha256=sha(path),
            triangles=len(tris),
            triangle_coordinate_digest=digest(tris),
            native_statistics=proof["cases"][name]["statistics"],
            source_role=proof["cases"][name]["role"],
            group_or_receiving_mesh_promoted_as_manufacturable=False,
        )
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
        )
        z.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
    with zipfile.ZipFile(target) as z:
        parsed = ET.fromstring(z.read("3D/3dmodel.model"))
    actual = parsed.findall(f"{{{NS}}}resources/{{{NS}}}object")
    assert len(actual) == len(GROUPS)
    for obj in actual:
        name = obj.attrib["name"]
        m = obj.find(f"{{{NS}}}mesh")
        vs = [tuple(float(v.attrib[k]) for k in ["x", "y", "z"]) for v in m.find(f"{{{NS}}}vertices")]
        tris = [tuple(vs[int(t.attrib[k])] for k in ["v1", "v2", "v3"]) for t in m.find(f"{{{NS}}}triangles")]
        assert (
            len(tris) == objects[name]["triangles"]
            and digest(tris) == objects[name]["triangle_coordinate_digest"]
        )
    write(
        OUT / "assembly-manifest.json",
        dict(
            objects=objects,
            current_native_proof_sha256=sha(OUT / "current-native/verification.json"),
            source_sha256={"assembly.py": sha(ROOT / "assembly.py")},
            artifact_sha256={target.name: sha(target)},
            exact_triangle_coordinate_roundtrip_verified=True,
            deleted_repaired_reoriented_or_decimated_faces=0,
            complete_currently_modeled_scene_families=True,
            full_operating_wiring_or_physical_unit_complete=False,
            whole_as_one_manufacturable_part=False,
            physical_qualified=False,
            thermal_qualified=False,
            fabrication_released=False,
        ),
    )
    print(
        json.dumps(
            dict(
                objects=len(objects),
                triangles=sum(o["triangles"] for o in objects.values()),
                artifact_sha256=sha(target),
            )
        )
    )


if __name__ == "__main__":
    build()
