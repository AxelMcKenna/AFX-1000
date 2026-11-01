"""FF02 source/topology/energy gate; no physical implementation acceptance."""

import json
import math

from hardware.cad.a12.thermal.fanless_feasibility import validate as ff01_validate
from hardware.cad.a12.thermal.fanless_feasibility.native_geometry import metadata

from .analyze import OUT, ROOT, read, sha


def errors(a):
    bad = []
    if a["thermal_qualified"] or a["cooling_design_adopted"] or a["physical_tests_performed"] != 0:
        bad.append("Unsupported FF02 adoption")
    if a["fin_top_z"] > a["control_top_nominal_z"] or a["envelope_overall_nominal_mm"] != 87.6:
        bad.append("Changed envelope")
    if a["fin_neighbor_preheat_or_installed_h_bound"] is not None:
        bad.append("Invented installed airflow")
    if not a["no_extra_fin_radiation_credit"]:
        bad.append("Unproved extra fin radiation")
    for key in ["vertical_area_residual_m2", "root_area_residual_m2"]:
        if abs(a["areas"][key]) > 1e-10:
            bad.append("Native-to-model area mismatch")
    for r in a["cases"]:
        if (
            not r["converged"]
            or not math.isfinite(r["heat_accepted_from_base_w"])
            or abs(r["conduction_and_surface_energy_residual_w"]) > 1e-6
        ):
            bad.append("Rejected FF02 solve")
        if r["installed_guarantee"] or r["target_heat_w"] != 35.43154587633119:
            bad.append("Changed target/physical guarantee")
        if r["extra_fin_radiation_credit_w"] != 0:
            bad.append("Unproved extra fin radiation")
    return bad


def packet_errors():
    a = read(OUT / "analysis.json")
    bad = errors(a) + ff01_validate.seal_errors()
    for p, h in a["source_sha256"].items():
        if not (ROOT.parent / p).exists() or sha(ROOT.parent / p) != h:
            bad.append("Changed source:" + p)
    for p, h in read(OUT / "drawing-inputs.json")["source_sha256"].items():
        if sha(ROOT.parent / p) != h:
            bad.append("Changed drawing source:" + p)
    for name, file in [("lid_with_fins", "lid-with-fins.stl"), ("fins", "fins.stl")]:
        if not (OUT / file).exists():
            bad.append("Missing native solid:" + name)
            continue
        r = metadata(OUT / file)
        if r != a["native"][name]:
            bad.append("Changed native solid:" + name)
        if r["nonmanifold_edges"] or r["inconsistent_oriented_edges"] or r["zero_area_faces"]:
            bad.append("Invalid closed native solid:" + name)
        if name == "lid_with_fins" and (r["connected_components"] != 1 or r["bounds_mm"][1][2] != 56):
            bad.append("Finned lid topology/datum failure")
    if "NoError" not in (OUT / "native.log").read_text():
        bad.append("Rejected native model")
    return bad


def seal_errors(a=None):
    a = read(ROOT / "handoff.json") if a is None else a
    expected = {
        str(p.relative_to(ROOT)): sha(p)
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    }
    return (
        []
        if a.get("sha256") == expected and a.get("packet_integrity_accepted") is True
        else ["Changed FF02 seal"]
    )


def main():
    bad = packet_errors()
    a = dict(
        packet_integrity_accepted=not bad,
        errors=bad,
        sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in ROOT.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
        },
        thermal_qualified=False,
        cooling_design_adopted=False,
        physical_tests_performed=0,
    )
    (ROOT / "handoff.json").write_text(json.dumps(a, indent=2) + "\n")
    if bad:
        raise SystemExit("\n".join(bad))
    print("FF02 native/source/energy evidence accepted; no installed cooling qualification.")


if __name__ == "__main__":
    main()
