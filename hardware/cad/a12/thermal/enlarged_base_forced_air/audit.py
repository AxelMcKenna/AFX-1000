"""FI01 read-only review: actual parts, source closures and honest recovery."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_pot.stage import audit_parent, closure

from .assembly import GROUPS, NS, digest, triangles
from .coverage import audit as coverage_audit
from .stage import CP, FA, OUT, ROOT, sha
from .verify import row_errors


def pin_stack_errors(pins, stack):
    bad = []
    original = set(map(tuple, pins["original"]))
    removed = set(map(tuple, pins["removed"]))
    kept = set(map(tuple, pins["kept"]))
    if (
        len(original) != 1037
        or len(removed) != 77
        or len(kept) != 960
        or removed & kept
        or removed | kept != original
    ):
        bad.append("actual whole-pin partition wrong")
    if (
        stack["screw_overall_including_countersunk_head_mm"] != 20
        or stack["plate"] != 6.2
        or stack["tray_flange"] != 2
        or stack["spacer"] != 6
        or not math.isclose(
            stack["screw_overall_including_countersunk_head_mm"]
            - stack["plate"]
            - stack["tray_flange"]
            - stack["spacer"],
            5.8,
        )
        or stack["nominal_engagement"] != 5.8
        or stack["nominal_actual_thread_overlap"] != [-20, -14.2]
        or stack["receiving_thread_interval"] != [-20.00002, -14.19998]
        or stack["foot_translation"] != -8
    ):
        bad.append("actualM3x20/8mmfootstack or receiving guards wrong")
    if (
        stack["original_plastic_case_has_no_conditional_metal_wall_lid_heat_credit"] is not True
        or stack["fan_current_ledger_or_full_wiring_implemented"] is not False
    ):
        bad.append("unimplemented thermal/electrical credit")
    return bad


def runtime_claim_errors(main, retry):
    bad = []
    if main["all_native_checks_clear"] is not False or retry["all_native_checks_clear"] is not False:
        bad.append("137execution failure relabeled as pass")
    return bad


def component_errors(manifest, target):
    bad = []
    with zipfile.ZipFile(target) as z:
        model = ET.fromstring(z.read("3D/3dmodel.model"))
    objects = model.findall(f"{{{NS}}}resources/{{{NS}}}object")
    if len(objects) != 16 or {o.attrib.get("name") for o in objects} != set(GROUPS):
        return ["component scene missing/duplicated family"]
    items = model.findall(f"{{{NS}}}build/{{{NS}}}item")
    if (
        len(items) != 16
        or {i.attrib["objectid"] for i in items} != {o.attrib["id"] for o in objects}
        or any("transform" in i.attrib for i in items)
    ):
        bad.append("scene pose/builditem changed")
    for o in objects:
        name = o.attrib["name"]
        expected = manifest["objects"][name]
        m = o.find(f"{{{NS}}}mesh")
        vs = [tuple(float(v.attrib[k]) for k in ["x", "y", "z"]) for v in m.find(f"{{{NS}}}vertices")]
        ts = [tuple(vs[int(t.attrib[k])] for k in ["v1", "v2", "v3"]) for t in m.find(f"{{{NS}}}triangles")]
        if len(ts) != expected["triangles"] or digest(ts) != expected["triangle_coordinate_digest"]:
            bad.append("scene surfaces changed/deleted:" + name)
        source = ROOT / expected["source_path"]
        if (
            sha(source) != expected["source_sha256"]
            or digest(triangles(source)) != expected["triangle_coordinate_digest"]
        ):
            bad.append("scene source mismatch:" + name)
    return bad


def captured_replay_errors():
    folder = OUT / "captured-replay-proof"
    proof = json.loads((folder / "verification.json").read_text())
    manifest = json.loads((folder / "rebind-manifest.json").read_text())
    bad = []
    if (
        len(proof["cases"]) != 3
        or not proof["all_requested_clear"]
        or proof["full_required_set"]
        or proof["changed_inputs"]
    ):
        bad.append("capturedsubsetreplayincomplete/failed/falselyfull")
    roots = {
        str(Path(n).parent)
        for n in manifest["rebound_sha256"]
        if Path(n).name == "context-derived.scad" and Path(n).parent.name != "generated"
    }
    if len(roots) != 1:
        return bad + ["replayrootambiguous"]
    tmp = Path(next(iter(roots)))
    reconstructed = {}
    for n, h in manifest["rebound_sha256"].items():
        relative = Path(n).relative_to(tmp)
        original = ROOT / relative if str(relative).startswith("context/") else OUT / relative
        data = original.read_bytes()
        if original.suffix == ".scad":
            data = data.decode().replace(str(ROOT / "context"), str(tmp / "context")).encode()
        actual = hashlib.sha256(data).hexdigest()
        if actual != h:
            bad.append("reboundsourcecannotreconstruct:" + n)
        reconstructed[n] = actual
    reconstructed[str(tmp / "rebind-manifest.json")] = sha(folder / "rebind-manifest.json")
    for n, h in proof["input_sha256"].items():
        if reconstructed.get(n, sha(Path(n)) if Path(n).exists() else None) != h:
            bad.append("replayinputchanged:" + n)
    for n, h in proof["artifact_sha256"].items():
        if sha(folder / Path(n).name) != h:
            bad.append("replayartifactchanged:" + n)
    specs = json.loads((OUT / "cases.json").read_text())
    for n, row in proof["cases"].items():
        bad += row_errors(n, row, specs[n], folder)
    return bad


def errors(check_components=True):
    bad = coverage_audit()
    main = json.loads((OUT / "verification.json").read_text())
    retry = json.loads((OUT / "retry-ps-hardware/verification.json").read_text())
    bad += runtime_claim_errors(main, retry)
    cap = json.loads((ROOT / "capture.json").read_text())
    for name, folder in [("CP01", CP), ("FA01", FA)]:
        if audit_parent(folder) != cap["parents"][name]:
            bad.append("sealedparentchanged:" + name)
    for n, h in cap["derived_context_sha256"].items():
        if sha(ROOT / n) != h:
            bad.append("captured context changed:" + n)
    for p in [OUT / "context-derived.scad", *(ROOT / "context").rglob("*.scad")]:
        if any(not q.is_relative_to(ROOT) for q in closure(p)):
            bad.append("geometry escapes captured closure:" + str(p))
    pins = json.loads((OUT / "pin-datum.json").read_text())
    stack = json.loads((ROOT / "FI01-stack.json").read_text())
    bad += pin_stack_errors(pins, stack)
    for path, prefix in [
        (ROOT / "context/hardware/cad/a12/thermal/generated/thermal-base.scad", "thermal_pins="),
        (OUT / "parts.scad", "eb_part_pins="),
    ]:
        l = next(x for x in path.read_text().splitlines() if x.startswith(prefix))
        actual = json.loads(l.split("=", 1)[1].rstrip(";"))
        if actual != pins["kept"]:
            bad.append("actualbase/API pinlist differs")
    model = (OUT / "context-derived.scad").read_text()
    if "-20.00002])cylinder(d=3.02,h=5.80004" not in model or "cylinder(d=3,h=18.35" not in model:
        bad.append("actual foot-screw overlap/length wrong")
    if "for(z=[-27.7,-26.7,-26.2,-12.2])" not in model or "cylinder(r=3.71,h=.00004,$fn=128)" not in model:
        bad.append("nominalcorrelatedseatguard changed")
    cad = json.loads((OUT / "cad-verification.json").read_text())
    for n, h in cad["artifact_sha256"].items():
        if sha(OUT / n) != h:
            bad.append("base/footSTEPartifactchanged:" + n)
    native = main["cases"]["eb_metal_geometry"]["statistics"]
    if (
        not cad["step_roundtrip_valid"]
        or cad["base_solids"] != 1
        or abs(native["volume_mm3"] - cad["base_volume_mm3"]) / cad["base_volume_mm3"] > 0.0001
    ):
        bad.append("independent actualbase STEP mismatch")
    if cad["native_boolean_receipt_sha256"] != sha(OUT / "verification.json"):
        bad.append("baseCADwrongsourceattempt")
    cp_native = json.loads((CP / "generated/verification.json").read_text())["cases"]["eb_metal_geometry"][
        "statistics"
    ]["volume_mm3"]
    # Different reviewed kernels may serialize roundedvertices differently;
    # this is a numeric regression screen, not a manufactured dimension limit.
    if abs(cp_native - 8316 - native["volume_mm3"]) > 0.01:
        bad.append("wrong actualwholepin volume removal")
    attachments = json.loads((OUT / "cad-attachments-verification.json").read_text())
    expected = {"AFX-FI01-TRAY": 1, "AFX-FI01-GUARDS": 2, "AFX-FI01-SPACERS": 4}
    for name, count in expected.items():
        r = attachments["parts"][name]
        if (
            not r["valid"]
            or r["solids"] != count
            or not r["step_roundtrip_valid"]
            or sha(OUT / (name + ".step")) != r["sha256"]
        ):
            bad.append("attachmentSTEPinvalid/stale:" + name)
    analytical = json.loads((OUT / "analytical-geometry.json").read_text())
    if analytical["perforations_per_guard"] != 37:
        bad.append("guardpattern count wrong")
    for name, r in analytical["rows"].items():
        if abs(r["native_minus_polygon_mm3"]) > 0.01:
            bad.append("independent polygonprofile numeric check:" + name)
    for report in [cad, attachments, analytical]:
        for n, h in report.get("source_sha256", {}).items():
            p = Path(n) if Path(n).is_absolute() else ROOT / n
            if sha(p) != h:
                bad.append("independentCADinputstale:" + n)
    pre = OUT / "preflight-seated"
    r = json.loads((pre / "verification.json").read_text())
    specs = json.loads((OUT / "cases.json").read_text())
    if (
        len(r["cases"]) != 17
        or not r["all_native_checks_clear"]
        or r["complete_required_set"]
        or r["changed_inputs"]
    ):
        bad.append("actual17interfacepreflightfailed/stale")
    for n, row in r["cases"].items():
        bad += row_errors(n, row, specs[n], pre)
    if check_components:
        a = json.loads((OUT / "assembly-manifest.json").read_text())
        for n, h in a["source_sha256"].items():
            if sha(ROOT / n) != h:
                bad.append("component inputstale:" + n)
        for n, h in a["artifact_sha256"].items():
            if sha(OUT / n) != h:
                bad.append("component artifactstale:" + n)
        bad += component_errors(a, OUT / "FI01-whole-unit-component-review.3mf")
    bad += captured_replay_errors()
    for flag in ["physical_qualified", "thermal_qualified", "fabrication_released"]:
        if main.get(flag) is not False:
            bad.append("unsupportedqualification:" + flag)
    return bad


if __name__ == "__main__":
    result = errors()
    print(json.dumps(dict(errors=result)))
    raise SystemExit(bool(result))
