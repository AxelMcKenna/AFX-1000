"""Reject stale/missing native solids or invented qualification claims before sealing."""

import json
import math

from hardware.cad.a12.thermal.candidates.u10.handoff import artifact_errors
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import read_sexpr

from .contract import ep_vias
from .synthesize import BASE, ROOT


def required_volume_errors(native, geometry):
    actual = native.get("native_checks", {}).get("geometry", {}).get("volume_mm3", 0)
    expected = sum(geometry.get("volumes_mm3", {}).values())
    if not expected or not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=0.0005):
        return ["Actual required LAND+TIM volume disagrees with declared CAD"]
    return []


def main():
    errors = []
    v = json.loads((ROOT / "generated/verification.json").read_text())
    errors.extend(artifact_errors(v, ROOT / "generated"))
    a = json.loads((ROOT / "generated/analysis.json").read_text())
    g = json.loads((ROOT / "generated/geometry.json").read_text())
    errors.extend(required_volume_errors(v, g))
    audit = json.loads((ROOT / "generated/u102-angle-audit.json").read_text())
    for report in [v, a, g, audit]:
        for p, expected in report["source_sha256"].items():
            if sha(REPO / p) != expected:
                errors.append("Stale input:" + p)
    h = json.loads((BASE / "handoff.json").read_text())
    for p, expected in h["sha256"].items():
        if sha(REPO / p) != expected:
            errors.append("Sealed U10 historical byte changed:" + p)
    if sha(ROOT / "sources/U102-network-frozen.py") != sha(ROOT.parent / "u102/network.py"):
        errors.append("Historical U102 model bytes differ from audited copy")
    pcb = ROOT / "variant/power_p03.kicad_pcb"
    ep = ep_vias(read_sexpr(pcb.read_text()))
    if a["native_electrical"]["electrically_complete"] or a["native_electrical"]["opens"] != 19:
        errors.append("Actual routing obligations misrepresented")
    if a["acceptance"]["total_path_upper_k_per_w"] is not None or a["package_upper_k_per_w"] is not None:
        errors.append("Unsupported upper thermal bound")
    for key in [
        "canonical_modified",
        "frozen_u10_modified",
        "thermal_path_qualified",
        "fabrication_released",
    ]:
        if a[key] is not False:
            errors.append("Unsupported claim:" + key)
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.name != "handoff.json"
    ]
    report = dict(
        packet_integrity_accepted=not errors,
        errors=errors,
        source_ep_contract=ep,
        sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(paths)},
        routing_complete=False,
        canonical_modified=False,
        frozen_sources_modified=False,
        thermal_path_qualified=False,
        physical_tests_performed=0,
        fabrication_released=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
