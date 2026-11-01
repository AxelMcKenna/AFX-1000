"""Independent CP01 saved geometry, source closure and component review checks."""

import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .assembly import GROUPS, NS, digest, triangles
from .stage import EB, OUT, PS, ROOT, audit_parent, closure, sha
from .verify import row_errors


def model_errors(model, cfg, erratum):
    bad = []
    if "-12.00002])cylinder(d=3.02,h=5.80004" not in model or "-16.2])cylinder(d=3.02,h=10.00002" in model:
        bad.append("wrong actual-overlap foot receiving interval")
    if erratum["foot_thread_gauge"]["new_receiving_abstraction"] != [-12.00002, -6.19998]:
        bad.append("wrong declared foot end guards")
    pot_ids = {
        "input",
        "output",
        "low",
        "mid",
        "high",
        "scene_depth",
        "x_level",
        "x_pitch",
        "scene_time",
        "scene_resonance",
    }
    openings = [r for r in cfg["openings"] if r[0] in pot_ids]
    if len(openings) != 10 or any(r[4:6] != [9.5, 9.5] for r in openings):
        bad.append("missing PS01panelbore or wrong receiving diameter")
    expected = json.loads((ROOT / "parent_evidence/pot_stack/generated/analysis.json").read_text())[
        "candidate_openings"
    ]
    if cfg["openings"] != expected:
        bad.append("panel aperture changed beyond exact PS01contract")
    if erratum["originals_modified"] is not False:
        bad.append("parent edit not permitted")
    return bad


def assembly_errors(manifest, target):
    bad = []
    with zipfile.ZipFile(target) as z:
        model = ET.fromstring(z.read("3D/3dmodel.model"))
    objects = model.findall(f"{{{NS}}}resources/{{{NS}}}object")
    if len(objects) != 11 or {o.attrib.get("name") for o in objects} != set(GROUPS):
        return ["missing/duplicated assembly scene family"]
    items = model.findall(f"{{{NS}}}build/{{{NS}}}item")
    if (
        len(items) != 11
        or {i.attrib["objectid"] for i in items} != {o.attrib["id"] for o in objects}
        or any("transform" in i.attrib for i in items)
    ):
        bad.append("missing or repositioned assembly build item")
    for o in objects:
        n = o.attrib["name"]
        expected = manifest["objects"][n]
        m = o.find(f"{{{NS}}}mesh")
        vs = [tuple(float(v.attrib[k]) for k in ["x", "y", "z"]) for v in m.find(f"{{{NS}}}vertices")]
        ts = [tuple(vs[int(t.attrib[k])] for k in ["v1", "v2", "v3"]) for t in m.find(f"{{{NS}}}triangles")]
        if len(ts) != expected["triangles"] or digest(ts) != expected["triangle_coordinate_digest"]:
            bad.append("assembly surfaces changed/deleted:" + n)
        p = ROOT / expected["source_path"]
        if (
            sha(p) != expected["source_sha256"]
            or digest(triangles(p)) != expected["triangle_coordinate_digest"]
        ):
            bad.append("assembly source differs:" + n)
    return bad


def independent_witness_errors():
    bad = []
    folder = OUT / "foot-witness"
    w = json.loads((folder / "verification.json").read_text())
    if not w["all_clear"]:
        bad.append("independent foot witness rejected")
    for k in ["source_sha256", "artifact_sha256"]:
        for n, h in w[k].items():
            if sha(Path(n)) != h:
                bad.append("foot witness stale:" + n)
    for n, row in w["cases"].items():
        spec = dict(
            role="empty" if n == "engaged_region_void" else "control",
            expected_volume=None if n == "engaged_region_void" else 0.002,
        )
        bad += row_errors(n, row, spec, folder)
    for kind in ["empty", "positive"]:
        folder = OUT / "captured-replay-proof" / kind
        proof = json.loads((folder / "verification.json").read_text())
        manifest = json.loads((folder / "rebind-manifest.json").read_text())
        if not proof["all_requested_clear"] or proof["changed_inputs"] or proof["full_required_set"]:
            bad.append("captured replay failed/stale or falsely complete")
        roots = {
            str(Path(n).parent)
            for n in manifest["rebound_sha256"]
            if Path(n).name == "context-derived.scad" and Path(n).parent.name != "generated"
        }
        if len(roots) != 1:
            bad.append("cannot locate exact rebound source root")
            continue
        tmp = Path(next(iter(roots)))
        reconstructed = {}
        for n, h in manifest["rebound_sha256"].items():
            p = Path(n)
            relative = p.relative_to(tmp)
            original = ROOT / relative if str(relative).startswith("context/") else OUT / relative
            data = original.read_bytes()
            if original.suffix == ".scad":
                data = data.decode().replace(str(ROOT / "context"), str(tmp / "context")).encode()
            if hashlib.sha256(data).hexdigest() != h:
                bad.append("rebound geometry not reconstructible:" + n)
            reconstructed[n] = h
        reconstructed[str(tmp / "rebind-manifest.json")] = sha(folder / "rebind-manifest.json")
        for n, h in proof["input_sha256"].items():
            actual = reconstructed.get(n)
            if actual is None:
                actual = sha(Path(n))
            if actual != h:
                bad.append("captured replay input mismatch:" + n)
        for n, h in proof["artifact_sha256"].items():
            if sha(folder / Path(n).name) != h:
                bad.append("captured replay artifact mismatch:" + n)
        specs = json.loads((OUT / "cases.json").read_text())
        for n, row in proof["cases"].items():
            bad += row_errors(n, row, specs[n], folder)
    return bad


def errors(check_assembly=True):
    bad = []
    cases = json.loads((OUT / "cases.json").read_text())
    report = json.loads((OUT / "verification.json").read_text())
    cfg = json.loads((OUT / "config.json").read_text())
    erratum = json.loads((ROOT / "EB01-erratum.json").read_text())
    model = (OUT / "context-derived.scad").read_text()
    bad += model_errors(model, cfg, erratum)
    cap = json.loads((ROOT / "capture.json").read_text())
    for n, h in cap["derived_context_sha256"].items():
        if sha(ROOT / n) != h:
            bad.append("capturedcontextstale:" + n)
    for n, h in report["input_sha256"].items():
        if sha(Path(n)) != h:
            bad.append("nativeinputstale:" + n)
    for n, h in report["artifact_sha256"].items():
        if sha(Path(n)) != h:
            bad.append("nativeartifactstale:" + n)
    if (
        len(cases) != 122
        or set(report["cases"]) != set(cases)
        or not report["all_native_checks_clear"]
        or not report["complete_required_set"]
        or report["changed_inputs"]
    ):
        bad.append("native case set incomplete/failed/stale")
    for n, spec in cases.items():
        if n in report["cases"]:
            bad += row_errors(n, report["cases"][n], spec, OUT)
    # Literal include/use/import closure of EVERY copied SCAD source, not just
    # the active scene. This catches the original PS01flat-map omission.
    for p in [OUT / "context-derived.scad", *(ROOT / "context").rglob("*.scad")]:
        for q in closure(p):
            if not q.is_relative_to(ROOT):
                bad.append("geometry escapes captured context:" + str(q))
    source = ROOT / "context/hardware/cad/a12/enclosure_growth/integration_repaired/generated/checks.scad"
    ui = source.read_text()
    line = next(l for l in ui.splitlines() if l.startswith("ui_inherited_envelopes="))
    rows = json.loads(line.split("=", 1)[1].rstrip(";"))
    if any(r[0].endswith("_pot") for r in rows):
        bad.append("old pot body class duplicated")
    if "if(include_pots)ps_body();" not in ui or "shell_height+3.6])ps_knob" not in ui:
        bad.append("revised body/knob absent from actual whole scene")
    eb = json.loads((EB / "generated/verification.json").read_text())
    for n in [
        "metal_geometry",
        "feet_geometry",
        "carrier_geometry",
        "attachment_geometry",
        "interface_geometry",
    ]:
        if report["cases"]["eb_" + n]["statistics"] != eb["cases"][n]["statistics"]:
            bad.append("unintended original part change:" + n)
    ps = json.loads((PS / "generated/verification.json").read_text())
    for n in ["panel_geometry", "body_geometry", "knob_0", "knob_1", "knob_2", "knob_3"]:
        got = report["cases"]["ps_" + n]["statistics"]
        if any(got[k] != v for k, v in ps["cases"][n]["statistics"].items()):
            bad.append("PS01actualpartchanged:" + n)
    pa = json.loads((ROOT / "parent-audit.json").read_text())
    if len(pa["PS01_missing_transitive_entries"]) != 2 or not pa["all_transitive_sources_in_private_context"]:
        bad.append("PS01supplementaryclosure gap not recorded")
    for name, p in [("EB01", EB), ("PS01", PS)]:
        if audit_parent(p) != cap["parents"][name]:
            bad.append("parent seal changed:" + name)
    for name in ["physical_qualified", "thermal_qualified", "fabrication_released"]:
        if report.get(name) is not False:
            bad.append("unsupportedqualification:" + name)
    if check_assembly:
        a = json.loads((OUT / "assembly-manifest.json").read_text())
        for n, h in a["source_sha256"].items():
            if sha(ROOT / n) != h:
                bad.append("assemblyinputstale:" + n)
        for n, h in a["artifact_sha256"].items():
            if sha(OUT / n) != h:
                bad.append("assemblyartifactstale:" + n)
        bad += assembly_errors(a, OUT / "CP01-whole-unit-component-review.3mf")
    bad += independent_witness_errors()
    return bad


if __name__ == "__main__":
    result = errors()
    print(json.dumps(dict(errors=result)))
    raise SystemExit(bool(result))
