"""Complete component3MF review; preserve all source triangles without repair."""

import hashlib
import json
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .stage import OUT, ROOT, sha, write
from .verify import mesh

CASEMAP = json.loads((OUT / "cases.json").read_text())
ALL = list(CASEMAP)
REVIEW = {n for n, v in CASEMAP.items() if v["role"] == "review"}

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", NS)

GROUPS = {
    "eb_interface_geometry": [
        "Four original TGP6000ULM TIM shapes atZ5.28..6.5 and ten OD6/ID2.3 matched nominal.2mm support shims; measured matching/compression/isolation unqualified"
    ],
    "eb_metal_geometry": [
        "Actual enlarged plate,1037pins,four retained lands,ten supports,all physical bores/countersinks"
    ],
    "eb_feet_assembly_geometry": [
        "Four machined foot assemblies and fourSJ5312 bumpers in global poses; actual5.8mm M3screw overlap plus20nmend guards; manufacturing footpilot unchanged"
    ],
    "eb_carrier_geometry": [
        "Enlarged retained plastic chassis,nine lower nut pockets/slots and bores,low-board posts,H9post,TC02two posts"
    ],
    "eb_attachment_geometry": [
        "Nine lower M3x16 screws+nine03223nuts andfourM3x12footretainers; actual supplier envelopes,threads unresolved"
    ],
    "eb_retained_controls_review": [
        "ui_controls():all PM01-shifted mechanics/optics,lever+7.6,allA11B3Fbodies/leads/holders/keymotions/revisedPS01knobs(base49.2,grubaxis3)/selectorcaps,guide,backer,lenses"
    ],
    "eb_retained_electronics_review": [
        "ui_electronics():P03db83/E28fed native actual-bore PCBs and both-face component boxes/cylinders; E19central3b2a; eight other boards; all inherited headers/inlet reserves plus ten exact PS01potbody envelopes; rearbody arraysZ14; actualTC02C3board/components"
    ],
    "eb_retained_wire_review": [
        "pf_wires()+ui_all_joints():complete accepted source-to-J13 curves,bare/insulation/strip/joints andallJ13/J14/J15joint/tails; no addedJ14/J15outgoingharness"
    ],
    "eb_retained_power_review": [
        "return_assembly(),exactpositive-links.stl,H9head,TC02heads; no surfaces removed to repair inherited mesh caveats"
    ],
    "eb_lid_rear_review": [
        "Enlarged UIlid/frontpanel and rear_panel() with all8audioaxesZ14; ten PS01panelpotbores9.5; FA01notadopted"
    ],
    "cp_pot_hardware_review": [
        "Ten PS01maximum hardware/shaft receiving unions, not simultaneous manufactured nut/washer/bushing stacks; all axial/radial/interface requirements remain unaccepted"
    ],
}


def triangles(path):
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * n
    for i in range(n):
        r = struct.unpack_from("<12fH", data, 84 + 50 * i)
        yield tuple(tuple(r[j : j + 3]) for j in (3, 6, 9))


def digest(rows):
    h = hashlib.sha256()
    for t in rows:
        h.update(struct.pack("<9d", *(v for p in t for v in p)))
    return h.hexdigest()


def build():
    if (ROOT / "handoff.json").exists():
        raise RuntimeError("Sealed component assembly cannot be overwritten")
    r = json.loads((OUT / "verification.json").read_text())
    assert (
        r["required_cases"] == ALL
        and r["all_native_checks_clear"]
        and r["complete_required_set"]
        and not r["changed_inputs"]
    )
    assert all(sha(Path(n)) == h for n, h in r["input_sha256"].items())
    assert all(sha(Path(n)) == h for n, h in r["artifact_sha256"].items())
    model = ET.Element(
        f"{{{NS}}}model", attrib={"unit": "millimeter", "{http://www.w3.org/XML/1998/namespace}lang": "en-US"}
    )
    ET.SubElement(
        model, f"{{{NS}}}metadata", name="Title"
    ).text = "CP01 EB01+PS01 whole-unit separate-component review; not one fabricated part"
    resources = ET.SubElement(model, f"{{{NS}}}resources")
    build = ET.SubElement(model, f"{{{NS}}}build")
    manifest = {}
    for ident, (name, families) in enumerate(GROUPS.items(), 1):
        source = OUT / (name + ".stl")
        assert r["cases"][name]["clear"]
        obj = ET.SubElement(resources, f"{{{NS}}}object", id=str(ident), type="model", name=name)
        ms = ET.SubElement(obj, f"{{{NS}}}mesh")
        verts = ET.SubElement(ms, f"{{{NS}}}vertices")
        faces = ET.SubElement(ms, f"{{{NS}}}triangles")
        # Deduplicate identical coordinate triples only in vertex indexing.
        # All source faces, including any inherited zero-area faces, survive.
        index = {}
        count = 0
        for tri in triangles(source):
            ids = []
            for p in tri:
                if p not in index:
                    index[p] = len(index)
                    ET.SubElement(
                        verts, f"{{{NS}}}vertex", **dict(zip(("x", "y", "z"), (format(v, ".17g") for v in p)))
                    )
                ids.append(index[p])
            ET.SubElement(faces, f"{{{NS}}}triangle", **dict(zip(("v1", "v2", "v3"), map(str, ids))))
            count += 1
        ET.SubElement(build, f"{{{NS}}}item", objectid=str(ident))
        manifest[name] = dict(
            object_id=ident,
            source_path=str(source.relative_to(ROOT)),
            source_sha256=sha(source),
            families=families,
            pose="Global source coordinates;3MFidentity transform",
            triangles=count,
            unique_coordinate_vertices=len(index),
            triangle_coordinate_digest=digest(triangles(source)),
            source_mesh=mesh(source),
            new_manufacturing_part=name not in REVIEW,
            retained_review_group_caveats=(
                "Retained group is a review assembly of source envelopes and/or meshes, not a single manufacturable watertight part. Every source face retained."
                if name in REVIEW
                else None
            ),
        )
    target = OUT / "CP01-whole-unit-component-review.3mf"
    contents = b"""<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>"""
    rels = b"""<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>"""
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", contents)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
    with zipfile.ZipFile(target) as z:
        reread = ET.fromstring(z.read("3D/3dmodel.model"))
    objects = reread.findall(f"{{{NS}}}resources/{{{NS}}}object")
    assert len(objects) == len(GROUPS) == 11
    for o in objects:
        name = o.attrib["name"]
        m = o.find(f"{{{NS}}}mesh")
        vs = [tuple(float(v.attrib[k]) for k in ("x", "y", "z")) for v in m.find(f"{{{NS}}}vertices")]
        ts = [tuple(vs[int(t.attrib[k])] for k in ("v1", "v2", "v3")) for t in m.find(f"{{{NS}}}triangles")]
        assert len(ts) == manifest[name]["triangles"]
        assert digest(ts) == manifest[name]["triangle_coordinate_digest"]
    report = dict(
        scope=__doc__,
        objects=manifest,
        all_eleven_source_scene_families_present=True,
        all_source_triangle_coordinates_and_order_roundtrip_exact=True,
        deleted_or_decimated_or_repaired_faces=0,
        all_new_production_meshes_closed_oriented_nonzero=True,
        complete_component_review_present=True,
        whole_fused_binary_STL_OFF_3MF_valid=False,
        whole_unit_is_one_fabricable_part=False,
        source_sha256={
            "assembly.py": sha(ROOT / "assembly.py"),
            "generated/verification.json": sha(OUT / "verification.json"),
            "geometry.scad": sha(ROOT / "geometry.scad"),
        },
        artifact_sha256={target.name: sha(target)},
        physical_qualified=False,
        thermal_qualified=False,
        fabrication_released=False,
    )
    write(OUT / "assembly-manifest.json", report)
    print(
        json.dumps(
            dict(
                objects=len(manifest),
                triangles=sum(m["triangles"] for m in manifest.values()),
                all_coordinates_exact=True,
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    build()
