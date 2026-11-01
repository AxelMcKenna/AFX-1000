"""Exact separate-object review; receiving groups are never fabrication solids."""

import json
import shutil
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from hardware.cad.a12.thermal.interior_airpath.assembly import NS, digest, triangles
from hardware.cad.a12.thermal.interior_airpath_meter318.assembly import roundtrip_errors

from .capture import ROOT, UA, sha


def box_triangles(row):
    _, x, y, z, sx, sy, sz = row
    v = [
        (x + i * sx, y + j * sy, z + k * sz)
        for i, j, k in [
            (0, 0, 0),
            (1, 0, 0),
            (1, 1, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 1),
            (1, 1, 1),
            (0, 1, 1),
        ]
    ]
    faces = [
        (0, 2, 1),
        (0, 3, 2),
        (4, 5, 6),
        (4, 6, 7),
        (0, 1, 5),
        (0, 5, 4),
        (1, 2, 6),
        (1, 6, 5),
        (2, 3, 7),
        (2, 7, 6),
        (3, 0, 4),
        (3, 4, 7),
    ]
    return [tuple(v[i] for i in f) for f in faces]


def write_stl(path, tris):
    data = bytearray(b"Receiving boxes; not selected physical connector CAD".ljust(80, b" "))
    data += struct.pack("<I", len(tris))
    for t in tris:
        data += struct.pack("<12fH", 0, 0, 0, *(x for p in t for x in p), 0)
    path.write_bytes(data)


def build():
    out = ROOT / "generated"
    copies = out / "review-final-meshes"
    target = out / "FR01-component-review-final.3mf"
    if copies.exists() or target.exists() or (ROOT / "handoff.json").exists():
        raise RuntimeError("New output required; replay never recaptures sealed parents")
    parent = json.loads((UA / "generated/assembly-manifest-corrected.json").read_text())
    seal = json.loads((UA / "handoff.json").read_text())
    assert all(sha(UA / p) == h for p, h in seal["files_sha256"].items())
    selection = {
        n: (UA / v["source_path"], "Retained UA01: " + v["description"]) for n, v in parent["objects"].items()
    }
    selection["assembly_lid"] = (
        out / "native-mount5/new_lid_geometry.stl",
        "Actual new four Ø2.4 keeper clearance holes; retained HT01 panel",
    )
    selection["carrier_geometry"] = (
        out / "native-mount5/new_carrier_geometry.stl",
        "Actual integral front columns/toes/pilots/keeper pockets; polymer/strength unqualified",
    )
    for board in ["NF233", "FPC84"]:
        for family in ["PCB", "components"]:
            selection[board + "_" + family] = (
                out / "native-robust-rear" / (board + "_" + family + "_geometry.stl"),
                "Actual captured native geometry with conditional both-face/tail receiving dimensions; FPC C7 conservative parent superset",
            )
    for i in range(4):
        selection["keeper_" + str(i)] = (
            out / "native-mount5" / ("keeper_" + str(i) + ".stl"),
            "Individual removable keeper; editable analytic STEP supplied separately",
        )
    selection["keeper_screw_receivers"] = (
        out / "native-mount5/screw_receiving_geometry.stl",
        "Four M2×10-class screw/head/washer receiving requirements, not certified hardware CAD",
    )
    selection["FPC_local_reference_exits"] = (
        out / "native-wire-escape/wire_escape_geometry.stl",
        "Fourteen local R10 reference exits only; no selected wire or complete harness",
    )
    assert len(selection) == 80
    copies.mkdir()
    for n, (p, desc) in list(selection.items()):
        q = copies / (n + ".stl")
        shutil.copyfile(p, q)
        selection[n] = (q, desc, p)
    coherent = json.loads((out / "coherent-receiving-model.json").read_text())
    for board in ["NF233", "FPC84"]:
        rows = [r for r in coherent["mates"] if r[0].startswith(board + "_")]
        p = copies / (board + "_connector_receivers.stl")
        write_stl(p, [tri for row in rows for tri in box_triangles(row)])
        selection[board + "_connector_receivers"] = (
            p,
            "Source-derived receiving boxes only; NF generic connector neighbor failure remains open",
            out / "coherent-receiving-model.json",
        )
    model = ET.Element("model", dict(xmlns=NS, unit="millimeter"))
    resources = ET.SubElement(model, "resources")
    items = ET.SubElement(model, "build")
    objects = {}
    for i, (name, (p, desc, origin)) in enumerate(selection.items(), 1):
        tris = triangles(p)
        vertices = []
        lookup = {}
        faces = []
        for t in tris:
            ids = []
            for v in t:
                if v not in lookup:
                    lookup[v] = len(vertices)
                    vertices.append(v)
                ids.append(lookup[v])
            faces.append(ids)
        obj = ET.SubElement(resources, "object", dict(id=str(i), type="model", name=name))
        m = ET.SubElement(obj, "mesh")
        vs = ET.SubElement(m, "vertices")
        ts = ET.SubElement(m, "triangles")
        for v in vertices:
            ET.SubElement(vs, "vertex", {k: repr(x) for k, x in zip(["x", "y", "z"], v)})
        for face in faces:
            ET.SubElement(ts, "triangle", {k: str(x) for k, x in zip(["v1", "v2", "v3"], face)})
        ET.SubElement(items, "item", dict(objectid=str(i)))
        objects[name] = dict(
            source_path=str(p.relative_to(ROOT)),
            source_sha256=sha(p),
            origin_path=str(origin),
            origin_sha256=sha(origin),
            description=desc,
            triangles=len(tris),
            triangle_coordinate_digest=digest(tris),
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
    assert not roundtrip_errors(target, objects)
    d = dict(
        objects=objects,
        object_count=82,
        retained_UA01_families=68,
        changed_UA01_families=2,
        new_families=12,
        integral_columns_not_duplicated_in_assembly=True,
        exact_triangle_coordinate_roundtrip_verified=True,
        deleted_repaired_reoriented_decimated_faces=0,
        whole_as_one_manufacturable_part=False,
        opaque_harness_sensitivity_boxes_not_physical_material=True,
        complete_wiring=False,
        NF_generic_mate_neighbor_failure_retained=True,
        physical_qualified=False,
        thermal_qualified=False,
        source_sha256={
            str(Path(__file__)): sha(Path(__file__)),
            str(UA / "handoff.json"): sha(UA / "handoff.json"),
            str(out / "coherent-receiving-model.json"): sha(out / "coherent-receiving-model.json"),
        },
        artifact_sha256={str(target): sha(target)},
    )
    (out / "assembly-manifest-final.json").write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                objects=len(objects),
                triangles=sum(v["triangles"] for v in objects.values()),
                sha256=sha(target),
            )
        )
    )


if __name__ == "__main__":
    build()
