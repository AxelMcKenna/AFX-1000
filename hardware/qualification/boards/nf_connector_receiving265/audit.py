"""Strict actual-artifact and source-bound local NC265 evidence audit."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from hardware.qualification.boards.nf_connector_receiving265 import (
    facet_audit,
    proposal,
    revision2,
    verify_guards,
    verify_mechanics,
)
from hardware.qualification.boards.nf_passive_selection.audit import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_sources(mapping):
    return [
        "Missing/changed source:" + name
        for name, expected in mapping.items()
        if not Path(name).is_file() or sha(Path(name)) != expected
    ]


def native_row_errors(name, row, folder, role):
    errors = []
    p = folder / (name + ".stl")
    log = folder / (name + ".log")
    if not log.is_file() or sha(log) != row["log_sha256"]:
        return [name + ":missing/changed log"]
    text = log.read_text()
    if row["role"] != role:
        errors.append(name + ":wrong role")
    if role == "empty":
        if (
            row["returncode"] != 1
            or p.exists()
            or row.get("STL_sha256") is not None
            or "Current top level object is empty" not in text
            or not row.get("passed")
            or "WARNING" in text
            or "ERROR" in text
        ):
            errors.append(name + ":not actual strict empty")
    else:
        if not p.is_file():
            return errors + [name + ":missing required nonempty STL"]
        if sha(p) != row["STL_sha256"]:
            errors.append(name + ":changed nonempty STL")
        try:
            actual = verify_mechanics.mesh(p)
        except (ValueError, IndexError):
            return errors + [name + ":unparseable required STL"]
        if (
            not actual["valid"]
            or "Status:     NoError" not in text
            or row["returncode"] != 0
            or "WARNING" in text
            or "ERROR" in text
        ):
            errors.append(name + ":invalid required Boolean solid")
        if actual != row.get("mesh"):
            errors.append(name + ":actual STL disagrees with saved geometry")
        if role == "part" and actual["connected_components"] != 1:
            errors.append(name + ":part disconnected")
        if role == "control":
            expected = row.get("expected_volume_mm3", 0.008)
            if abs(actual["volume_mm3"] - expected) > (2e-7 if expected < 1e-4 else 2e-6):
                errors.append(name + ":wrong positive-control volume")
    return errors


def current_physical_pads():
    pcb = ROOT / "prototype-v3/NC265_ports_strain_v3.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    result = {}
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        at = first(f, "at")
        u, v = float(at[1]), float(at[2])
        pads = {}
        for p in children(f, "pad"):
            a = first(p, "at")
            n = children(p, "net")
            d = first(p, "drill")
            size = first(p, "size")
            pads[p[1]] = dict(
                net=str(n[0][-1]) if n else None,
                at_mm=[u + float(a[1]), v + float(a[2])],
                drill_mm=float(d[1]),
                size_mm=[float(size[1]), float(size[2])],
            )
        result[ref] = pads
    return result


def checks():
    errors = []
    cap = json.loads((ROOT / "capture.json").read_text())
    for source in cap["sealed_sources"]:
        folder = ROOT / "inputs" / source["name"]
        hand = folder / "handoff.json"
        if sha(hand) != source["seal_sha256"]:
            errors.append("Changed captured seal:" + source["name"])
            continue
        for name, expected in json.loads(hand.read_text())["files_sha256"].items():
            if not (folder / name).is_file() or sha(folder / name) != expected:
                errors.append("Changed captured design:" + source["name"] + "/" + name)
    for name, d in cap["extra_captured_references"].items():
        if sha(ROOT / name) != d["sha256"]:
            errors.append("Changed extra captured reference:" + name)
    ports = json.loads((ROOT / "ports-v2.json").read_text())
    if ports != revision2.revised():
        errors.append("Wrong bounded v2 overlay")
    expected = proposal.native_net_contract(json.loads((ROOT / "inputs/NF265/components.json").read_text()))
    actual = current_physical_pads()
    for p in ports["ports"]:
        ref = p["ref"]
        if {n: v["net"] for n, v in actual[ref].items()} != expected[ref]:
            errors.append("Actual physical net mismatch:" + ref)
        fp = read_sexpr(Path(p["footprint_file"]).read_text())
        for pad in children(fp, "pad"):
            at = first(pad, "at")
            required_xy = [p["anchor_mm"][i] + float(at[i + 1]) for i in range(2)]
            saved = actual[ref][pad[1]]
            if (
                any(abs(a - b) > 1e-6 for a, b in zip(saved["at_mm"], required_xy))
                or saved["drill_mm"] != float(first(pad, "drill")[1])
                or saved["size_mm"] != list(map(float, first(pad, "size")[1:3]))
            ):
                errors.append("Actual serialized pad geometry mismatch:" + ref + "." + pad[1])
        if sha(Path(p["footprint_file"])) != p["footprint_sha256"]:
            errors.append("Changed candidate library:" + ref)
    for ref, u in [("H101", 61), ("H102", 90)]:
        if actual[ref][""]["at_mm"] != [u, 21] or actual[ref][""]["drill_mm"] != 2.6:
            errors.append("Wrong actual mechanical hole:" + ref)
    original = ROOT / "mechanical-v2/native-run1"
    a = json.loads((original / "verification.json").read_text())
    known = {
        "own_PCB_seats",
        "hardware_receiving_threads",
        "hardware_matched_nominal_PCB",
        "base_cap_nonseat_overlap",
    }
    if set(a["cases"]) != set(verify_mechanics.CASES):
        errors.append("Missing original native coverage")
    for name, row in a["cases"].items():
        if name in known:
            if row["passed"] or row["returncode"] != 0 or not (original / (name + ".stl")).exists():
                errors.append("Original strict contact failure erased:" + name)
            elif (
                sha(original / (name + ".stl")) != row["STL_sha256"]
                or sha(original / (name + ".log")) != row["log_sha256"]
            ):
                errors.append("Changed original contact diagnostic:" + name)
            elif abs(verify_mechanics.mesh(original / (name + ".stl"))["volume_mm3"]) > 1e-9:
                errors.append("Original contact diagnostic now has physical volume:" + name)
        else:
            errors += native_row_errors(name, row, original, verify_mechanics.CASES[name])
    errors += check_sources(a["source_sha256"])
    face = json.loads((ROOT / "mechanical-v2/facet-boundary-audit.json").read_text())
    if set(face["cases"]) != known:
        errors.append("Incomplete facet proof")
    for name, c in face["cases"].items():
        if c["unresolved_triangle_indices"] or not c["each_entire_triangle_inside_one_convex_mask"]:
            errors.append("Unproved convex facet:" + name)
        data = (original / (name + ".stl")).read_bytes()
        count = struct.unpack_from("<I", data, 80)[0]
        masks = facet_audit.masks(name)
        if count != c["triangles"] or len(data) != 84 + 50 * count:
            errors.append("Changed raw contact face count:" + name)
        for i in range(count):
            row = struct.unpack_from("<12fH", data, 84 + 50 * i)
            tri = [row[3:6], row[6:9], row[9:12]]
            if not any(all(facet_audit.vertex_inside(v, m) for v in tri) for m in masks):
                errors.append("Actual triangle bridges masks:" + name + ":" + str(i))
                break
    errors += check_sources(face["source_sha256"])
    guarded = ROOT / "mechanical-v2/native-guards"
    g = json.loads((guarded / "verification.json").read_text())
    if (
        set(g["cases"]) != set(verify_guards.CASES)
        or g["changed_inputs"]
        or not g["actual_parts_ports_datums_and_prior_STL_bytes_unchanged"]
    ):
        errors.append("Wrong guarded coverage/source state")
    for name, row in g["cases"].items():
        errors += native_row_errors(name, row, guarded, verify_guards.CASES[name])
    errors += check_sources(g["source_sha256"])
    for file in [
        "identity-review.json",
        "control-fanout.json",
        "prototype-v1/native-ports.json",
        "prototype-v2/native-overlay.json",
        "prototype-v3/repair.json",
        "mechanical-v2/BREP/BREP.json",
        "fresh-control-proof/proof.json",
    ]:
        d = json.loads((ROOT / file).read_text())
        errors += check_sources(d["source_sha256"])
    fresh = json.loads((ROOT / "fresh-control-proof/proof.json").read_text())
    if (
        len(fresh["certificates"]) != 406
        or not all(c["certified"] for c in fresh["certificates"].values())
        or fresh["unstaggered_samecolumn_negative_control"]["certified"]
    ):
        errors.append("Fresh continuous wire proof/control failure")
    errors += check_sources(fresh["captured_source_sha256"])
    drc = json.loads((ROOT / "prototype-v3/drc.json").read_text())
    if drc["violations"] or drc["unconnected_items"]:
        errors.append("Nonzero actual v3 native DRC")
    for name, required in [
        ("foreign_copper_inside_NPTH", "hole_clearance"),
        ("foreign_copper_in_strain_annulus", "items_not_allowed"),
    ]:
        d = json.loads((ROOT / "prototype-v3" / (name + "-drc.json")).read_text())
        if not any(x["type"] == required and x["severity"] == "error" for x in d["violations"]):
            errors.append("Real native Cu mutation did not fail:" + name)
    for flag in [
        "full_board_fit_certified",
        "full_unit_harness_fit_certified",
        "physical_qualified",
        "fabrication_released",
    ]:
        if ports.get(flag) is not False:
            errors.append("Unsupported port promotion:" + flag)
    f = json.loads((ROOT / "control-fanout.json").read_text())
    if len(f["routes"]) != 29 or len(f["certificates"]) != 406 or any(r["circuit"] == 4 for r in f["routes"]):
        errors.append("Wrong live PHD wire subset")
    return errors


def run(output=None):
    result = checks()
    if output:
        if output.exists():
            raise RuntimeError("Fresh audit output required")
        output.write_text(
            json.dumps(
                dict(errors=result, actual_physical_pads=current_physical_pads(), physical_qualified=False),
                indent=2,
            )
            + "\n"
        )
    print(json.dumps(dict(errors=result, physical_qualified=False)))
    raise SystemExit(bool(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    run(parser.parse_args().output)
