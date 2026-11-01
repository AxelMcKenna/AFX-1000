"""Independent saved native/source/part/area/assembly review; no solver."""

import json
import math
import re
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base_pot.stage import closure
from hardware.cad.a12.thermal.interior_airpath.assembly import triangles
from hardware.cad.a12.thermal.interior_airpath.audit import header_errors
from hardware.cad.a12.thermal.interior_airpath.port_boundary_audit import distance

from .assembly import CHANGED, GROUPS, roundtrip_errors
from .channel_budget import report, source_errors
from .mating import CONTROLS, EMPTY
from .mating_audit import PLANES, polygon_edges
from .seated_stage import CONTROL_GUARD, EXTRA, GUARDED
from .stage import MODEL, OUT, PARENT, ROOT, require_parent, sha
from .verify import row_errors, specs


def raw_contact_errors(surfaces, domains):
    """Reclassify actual saved vertices; saved 'certified' booleans cannot pass alone."""
    bad=[]
    for name,(axis,planes) in PLANES.items():
        path=OUT/"mating-raw"/(name+".stl")
        tris=triangles(path)
        classes={"named-plane":0,"named-cylinder-facet":0,"uncertified":0}
        curves=[]
        if name=="frame_gasket_tray":
            curves=[(polygon_edges(cx+x,cy+y,3.1),(0,1),2,[-25.2,-24.7]) for cx,cy in [[80,165.5],[254,165.5]] for x in [-16,16] for y in [-16,16]]
        if name=="feedthrough_wall":
            curves=[(polygon_edges(x,-10,2.2),(0,2),1,[137,139]) for x in [46,235.5]]
        worst=0
        for tri in tris:
            delta=min(max(abs(v[axis]-plane) for v in tri) for plane in planes)
            if delta<=.00002:
                classes["named-plane"]+=1
                worst=max(worst,delta)
                continue
            best=float("inf")
            for edges,axes,along,interval in curves:
                if any(v[along]<interval[0]-.00002 or v[along]>interval[1]+.00002 for v in tri):
                    continue
                best=min(best,min(max(distance((v[axes[0]],v[axes[1]]),a,b) for v in tri) for a,b in edges))
            if best<=.00002:
                classes["named-cylinder-facet"]+=1
                worst=max(worst,best)
            else:
                classes["uncertified"]+=1
        saved=surfaces["cases"][name]
        if classes!=saved["classes"] or classes["uncertified"] or len(tris)!=saved["triangles"] or not math.isclose(worst,saved["max_certified_distance_mm"],abs_tol=1e-14) or sha(path)!=saved["raw_STL_sha256"]:
            bad.append("raw-contact-classification-not-actual:"+name)
        if name in domains["cases"]:
            if name.startswith("M3"):
                axes=(0,1)
                centres=[(p[0]+x,p[1]+y) for p in [[80,165.5],[254,165.5]] for x in [-16,16] for y in [-16,16]]
                radius=3.71
            else:
                axes=(0,2)
                centres=[(x+dx,-8.9) for x in [80,254] for dx in [-7,7]]
                radius=2.73
            actual=max(min(max(math.hypot(v[axes[0]]-cx,v[axes[1]]-cy) for v in tri) for cx,cy in centres) for tri in tris)
            row=domains["cases"][name]
            if actual>radius or row["proposed_guard_radius"]!=radius or not math.isclose(actual,row["max_actual_triangle_radius"],abs_tol=1e-12):
                bad.append("raw-local-guard-domain-not-actual:"+name)
    return bad


def guard_errors(contract, guard, fixture, raw):
    bad=[]
    if contract["test_only_guard_mm"]!=.00002 or "mg=.00002;" not in guard:
        bad.append("wrong-seat-guard-scale")
    for exact in ["y=[134,139]","mg_Y(136.5);mg_Y(137)","mg_Y(137);mg_Y(139)",
                  "[x,137-mg,-10]","cylinder(r=3.71","cylinder(r=2.73"]:
        if exact not in guard:
            bad.append("missing-scoped-translated-mask:"+exact)
    if contract["guarded_empty_cases"]!=GUARDED or contract["positive_controls_use_the_same_guard"]!=CONTROL_GUARD or contract["additional_radial_and_axial_controls"]!=EXTRA:
        bad.append("missing-guarded-coverage")
    branches=dict(re.findall(r'^if\(mate_case=="([^\"]+)"\)(.*)$',raw,re.M))
    actual=dict(re.findall(r'^if\(mate_seated_case=="([^\"]+)"\)(.*)$',fixture,re.M))
    for n,b in branches.items():
        g=n if n in GUARDED else CONTROL_GUARD.get(n)
        expected="difference(){"+b+"mate_guard_for("+json.dumps(g)+");}" if g else b
        if actual.get(n)!=expected:
            bad.append("raw-branch-or-same-guard-control-changed:"+n)
    if contract["raw_source_or_actual_AP03_parts_modified"] or contract["deliberate_penetration_mm"]!=.02:
        bad.append("actual-part-edit-or-weakened-control")
    return bad


def base_errors(d):
    if not all(d[k] for k in ["valid","roundtrip_valid"]) or d["solids"]!=1 or d["roundtrip_solids"]!=1:
        return ["invalid-base-BREP"]
    expected=d["original_volume_mm3"]-19*108
    if any(abs(d[k]-expected)>.001 for k in ["actual_volume_mm3","independent_expected_mm3","roundtrip_volume_mm3"]):
        return ["wrong-whole-pin-only-volume"]
    if abs(d["actual_volume_mm3"]-d["native_faceted_volume_mm3"])>5:
        return ["native-curve-base-mismatch"]
    return []


def proof_errors(path, definitions, selector):
    d=json.loads(path.read_text())
    bad=header_errors(d,definitions,selector)
    for n,row in d["cases"].items():
        if n in definitions:
            bad += [n+":"+e for e in row_errors(n,row,definitions[n],path.parent)]
    for key in ["input_sha256","artifact_sha256"]:
        for n,h in d[key].items():
            if sha(Path(n))!=h:
                bad.append("changed-native-bound-input/artifact:"+n)
    return bad


def pin_errors(data,source_values):
    old=json.loads((PARENT/"generated/analysis.json").read_text())["pins"]["kept_centres"]
    removed=data["additional_whole_removed"]
    expected=[p for p in old if p not in removed]
    if len(removed)!=19 or len(expected)!=899 or data["kept_pins"]!=expected or source_values!=expected:
        return ["wrong-actual-whole-pin-field"]
    return []


def assembly_errors(m):
    bad=[]
    if set(m["objects"])!=set(GROUPS):
        return ["missing-complete-review-family"]
    if m["unchanged_parent_families"]!=16 or m["fresh_changed_families"]!=5:
        bad.append("false-new-native-family-count")
    for n,row in m["objects"].items():
        for path,expected in [(ROOT/row["source_path"],row["source_sha256"]),
             (Path(row["origin_path"]),row["origin_sha256"]),(Path(row["native_proof"]),row["native_proof_sha256"])]:
            if sha(path)!=expected:
                bad.append("stale-review-source:"+n)
        if row["unchanged_parent_mesh_reused"]!=(n not in CHANGED):
            bad.append("false-review-reuse:"+n)
        d=json.loads(Path(row["native_proof"]).read_text())
        if d["cases"][n]["statistics"]!=row["native_statistics"] or not d["cases"][n]["clear"]:
            bad.append("false-review-proof:"+n)
    bad += roundtrip_errors(OUT/"AP03-complete-modeled-component-review.3mf",m["objects"])
    return bad


def errors():
    require_parent()
    bad=[]
    cap=json.loads((ROOT/"capture.json").read_text())
    for n,h in cap["source_sha256"].items():
        if sha(ROOT/n)!=h:
            bad.append("captured-source-changed:"+n)
    for p in closure(OUT/"current-checks.scad"):
        if not p.is_relative_to(ROOT):
            bad.append("uncaptured-SCAD-literal:"+str(p))
    data=json.loads((OUT/"analysis.json").read_text())
    bad += source_errors((OUT/"checks.scad").read_text(),data)
    for p,prefix in [(MODEL/"parts.scad","eb_part_pins="),
            (MODEL/"context/hardware/cad/a12/thermal/generated/thermal-base.scad","thermal_pins=")]:
        values=json.loads(next(l for l in p.read_text().splitlines() if l.startswith(prefix)).split("=",1)[1].rstrip(";"))
        bad += pin_errors(data,values)
    main=OUT/"current-native/verification.json"
    bad += proof_errors(main,specs(),"ap_case")
    if not json.loads(main.read_text())["complete_set"]:
        bad.append("incomplete-main-cases")
    definitions={n:dict(role="empty" if n in EMPTY else "control" if n in CONTROLS else "witness") for n in EMPTY+CONTROLS+EXTRA}
    for n in CONTROLS:
        definitions[n]["expected_volume"]=.0016
    bad += proof_errors(OUT/"mating-seated/verification.json",definitions,"mate_seated_case")
    contract=json.loads((OUT/"mating-seat-contract.json").read_text())
    bad += guard_errors(contract,(ROOT/"mating_guards.scad").read_text(),(OUT/"mating-seated.scad").read_text(),(ROOT/"mating.scad").read_text())
    for n,h in contract["source_sha256"].items():
        if sha(ROOT/n)!=h:
            bad.append("guard-contract-source-changed:"+n)
    if sha(OUT/"mating-seated.scad")!=contract["fixture_sha256"]:
        bad.append("guard-fixture-changed")
    raw=json.loads((OUT/"mating-raw/verification.json").read_text())
    for key in ["input_sha256","artifact_sha256"]:
        if any(sha(Path(n))!=h for n,h in raw[key].items()):
            bad.append("raw-mating-evidence-changed")
    surfaces=json.loads((OUT/"raw-mating-surface-audit.json").read_text())
    if not surfaces["all_raw_triangles_certified"] or any(r["uncertified"] or r["max_certified_distance_mm"]>.00002 for r in surfaces["cases"].values()):
        bad.append("unclassified-raw-contact-facet")
    domains=json.loads((OUT/"raw-mating-bolt-domain-audit.json").read_text())
    if not domains["all_raw_bolt_facets_inside_proposed_local_masks"]:
        bad.append("uncontained-contact-facet")
    bad += raw_contact_errors(surfaces,domains)
    if json.loads((OUT/"channel-budget.json").read_text())!=report():
        bad.append("channel-report-not-exact-source-replay")
    brep=json.loads((OUT/"base-BREP-verification.json").read_text())
    bad += base_errors(brep)
    for name in ["base-BREP-verification.json","assembly-manifest.json","drawing-provenance.json"]:
        d=json.loads((OUT/name).read_text())
        for n,h in d["source_sha256"].items():
            p=PARENT/"generated/AP02-BASE.step" if n=="AP02_BASE_STEP" else ROOT/n
            if sha(p)!=h:
                bad.append("producer-source-changed:"+n)
        for n,h in d["artifact_sha256"].items():
            if sha(OUT/n)!=h:
                bad.append("produced-artifact-changed:"+n)
    bad += assembly_errors(json.loads((OUT/"assembly-manifest.json").read_text()))
    history=json.loads((ROOT/"history/reconstruction-map.json").read_text())
    for name in ["first-preflight","configured-preflight"]:
        d=json.loads((OUT/name/"verification.json").read_text())
        row=history["trials"][name]
        if row["receipt_sha256"]!=sha(OUT/name/"verification.json"):
            bad.append("historical-preflight-receipt-changed:"+name)
        for n,h in d["input_sha256"].items():
            p=ROOT/row["input_aliases"][n]["copy"] if n in row["input_aliases"] else Path(n)
            if sha(p)!=h:
                bad.append("historical-preflight-input-not-reconstructible:"+n)
        for n,h in d["artifact_sha256"].items():
            if sha(Path(n))!=h:
                bad.append("historical-preflight-artifact-changed:"+n)
    if any(data[k] for k in ["actual_flow_split_verified","physical_qualified","thermal_qualified","fabrication_released","adopted"]):
        bad.append("unsupported-qualification")
    return bad


if __name__=="__main__":
    d=errors()
    print(json.dumps(dict(errors=d)))
    raise SystemExit(bool(d))
