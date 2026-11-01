"""Portable independent artifact/capture review; no native solver required."""

import argparse
import json
import math
import xml.etree.ElementTree as ET
import zipfile

from .assembly import GROUPS, NS, digest, triangles
from .stage import OUT, ROOT, sha
from .verify import ALL, SOLIDS, row_errors


def contract_errors(d, a):
    errors = []
    if d["housing"] != [334, 188.4, 45.6]:
        errors.append("wrong enlarged extent")
    if sorted(d["shell_fasteners"]) != sorted([[x, y] for x in [8, 167, 326] for y in [8, 149, 180.4]]):
        errors.append("missing or misplaced nine lower axes")
    expected_feet = sorted([[x, y] for x in [20, 314] for y in [20, 168.4]])
    if sorted(d["feet"]["centres"]) != expected_feet:
        errors.append("feet do not preserve20mm new-edge offset")
    pins = a["pins"]["centres"]
    if len(pins) != 1037 or len(set(map(tuple, pins))) != 1037:
        errors.append("wrong actual pin count")
    for p in pins:
        if p[0] < 12 or p[0] > 322 or p[1] < 12 or p[1] > 176.4 or any((v - 12) % 7 for v in p):
            errors.append("pin outside declared border/lattice")
            break
        if (
            any(math.dist(p, q) < 12 for q in d["feet"]["centres"])
            or any(math.dist(p, q) < 6 for q in d["shell_fasteners"])
            or any(
                math.dist(p, q) < 4 + math.sqrt(2) * 1.5 for q in d["return_support_attachments"]["centres"]
            )
        ):
            errors.append("pin invades actual attachment exclusion")
            break
    if len(a["retained_supports"]) != 10 or len(a["retained_thermal_lands"]) != 4:
        errors.append("lost original supports/thermal interfaces")
    for name in [
        "physical_qualified",
        "thermal_qualified",
        "fabrication_released",
        "structural_qualified",
        "whole_wiring_qualified",
    ]:
        if a.get(name) is not False:
            errors.append("unsupported qualification flag:" + name)
    return errors


def assembly_errors(manifest, target):
    errors = []
    with zipfile.ZipFile(target) as z:
        model = ET.fromstring(z.read("3D/3dmodel.model"))
    objs = model.findall(f"{{{NS}}}resources/{{{NS}}}object")
    if {o.attrib.get("name") for o in objs} != set(GROUPS) or len(objs) != 10:
        return ["component assembly missing/duplicated scene family"]
    items = model.findall(f"{{{NS}}}build/{{{NS}}}item")
    if (
        len(items) != 10
        or {i.attrib["objectid"] for i in items} != {o.attrib["id"] for o in objs}
        or any("transform" in i.attrib for i in items)
    ):
        errors.append("component assembly missing/repositioned build item")
    for o in objs:
        n = o.attrib["name"]
        expected = manifest["objects"][n]
        m = o.find(f"{{{NS}}}mesh")
        v = [tuple(float(p.attrib[k]) for k in ("x", "y", "z")) for p in m.find(f"{{{NS}}}vertices")]
        ts = [tuple(v[int(t.attrib[k])] for k in ("v1", "v2", "v3")) for t in m.find(f"{{{NS}}}triangles")]
        if len(ts) != expected["triangles"] or digest(ts) != expected["triangle_coordinate_digest"]:
            errors.append("component assembly changed/deleted triangles:" + n)
        source = ROOT / expected["source_path"]
        if (
            sha(source) != expected["source_sha256"]
            or digest(triangles(source)) != expected["triangle_coordinate_digest"]
        ):
            errors.append("component assembly source mismatch:" + n)
    return errors


def errors(check_assembly=True):
    bad = []
    a = json.loads((OUT / "analysis.json").read_text())
    d = json.loads((ROOT / "design.json").read_text())
    bad += contract_errors(d, a)
    capture = json.loads((ROOT / "capture.json").read_text())
    for n, h in capture["original_sha256"].items():
        if sha(ROOT / "sources" / n) != h:
            bad.append("captured original mismatch:" + n)
    for n, h in capture["derived_context_sha256"].items():
        if sha(ROOT / n) != h:
            bad.append("derived context mismatch:" + n)
    r = json.loads((OUT / "verification.json").read_text())
    if (
        r["requested_cases"] != ALL
        or set(r["cases"]) != set(ALL)
        or not r["all_requested_native_checks_clear"]
        or r["changed_inputs"]
    ):
        bad.append("native cases incomplete/failed/stale")
    for group in ["input_sha256", "artifact_sha256"]:
        for n, h in r[group].items():
            if sha(ROOT / n) != h:
                bad.append("native bound file mismatch:" + n)
    for n in ALL:
        if n in r["cases"]:
            bad += row_errors(n, r["cases"][n])
    native = r["cases"]["metal_geometry"]["statistics"]
    standalone = r["cases"]["standalone_metal_geometry"]["statistics"]
    if native != standalone:
        bad.append("standalone API differs from integrated metal")
    if (
        max(abs(x - y) for x, y in zip(native["max_mm"], [334, 188.4, 6.3])) > 1e-4
        or abs(native["min_mm"][2] + 18.2) > 1e-4
    ):
        bad.append("actual metal output bounds mismatch")
    cad = json.loads((OUT / "cad-verification.json").read_text())
    delta = abs(native["volume_mm3"] - cad["base_volume_mm3"]) / cad["base_volume_mm3"]
    if delta > 0.0001 or not cad["step_roundtrip_valid"] or not cad["base_valid"] or cad["base_solids"] != 1:
        bad.append("independent STEP/native mismatch")
    if cad["native_boolean_receipt_sha256"] != sha(OUT / "verification.json"):
        bad.append("CAD/native comparison uses another receipt")
    for n in SOLIDS:
        s = r["cases"][n]["statistics"]
        if (
            not s["closed_oriented_boundary"]
            or s["degenerate_triangles_excluded"]
            or s["volume_mm3"] <= 0.001
        ):
            bad.append("production mesh gate:" + n)
    if check_assembly:
        manifest = json.loads((OUT / "assembly-manifest.json").read_text())
        for n, h in manifest["source_sha256"].items():
            if sha(ROOT / n) != h:
                bad.append("assembly input mismatch:" + n)
        for n, h in manifest["artifact_sha256"].items():
            if sha(OUT / n) != h:
                bad.append("assembly artifact mismatch:" + n)
        bad += assembly_errors(manifest, OUT / "EB01-whole-unit-component-review.3mf")
    return bad


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-assembly", action="store_true")
    args = parser.parse_args()
    result = errors(not args.skip_assembly)
    print(json.dumps(dict(errors=result)))
    raise SystemExit(bool(result))
