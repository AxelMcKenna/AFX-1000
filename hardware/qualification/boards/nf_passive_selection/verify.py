"""Strict saved NP01 evidence checks. No live parent state is substituted."""

import argparse
import hashlib
import json
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection import audit, lifetime

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def checked_file(name, expected):
    p = Path(name)
    if not p.is_absolute():
        p = ROOT / p
    return p.is_file() and sha(p) == expected


def saved_errors(root=ROOT):
    errors = []
    d = json.loads((root / "analyses/analysis.json").read_text())
    errors.extend(audit.report_errors(d))
    selections = json.loads((root / "generated/selections.json").read_text())
    if d["selections"] != selections:
        errors.append("Analysis embeds a different selection table")
    parts = json.loads((root / "sources/NF261/components.json").read_text())
    parameters = json.loads((root / "sources/reference-baseline/parameters.json").read_text())
    if d["monitor_scenarios"] != audit.monitor_scenarios(parts, parameters):
        errors.append("Saved monitor bounds disagree with captured-source recalculation")
    if d["DC_power_screens"] != audit.dc_power_screens():
        errors.append("Saved power/derating disagrees with independent recalculation")
    life = json.loads((root / "analyses/lifetime-scenarios.json").read_text())
    pure_life = {k: v for k, v in life.items() if k != "source_sha256"}
    if pure_life != lifetime.analysis():
        errors.append("Saved additional life scenarios disagree with recalculation")
    for name, expected in life["source_sha256"].items():
        if not checked_file(name, expected):
            errors.append(f"Life input missing/changed: {name}")
    for label, mapping in [
        ("analysis sources", d["source_sha256"]),
        ("selection sources", selections["source_sha256"]),
        ("primary bytes", selections["primary_sha256"]),
        ("footprints", d["candidate_footprint_sha256"]),
        ("captured repository bytes", json.loads((root / "capture.json").read_text())["copied_sha256"]),
    ]:
        for name, expected in mapping.items():
            if not checked_file(name, expected):
                errors.append(f"{label}: missing/changed {name}")
    # Re-extract actual original source pads to detect a forged saved land row.
    expected = audit.land_comparison(
        selections["rows"],
        audit.native_footprints(root / "sources/NF233-physical/negative_startup_ready.kicad_pcb"),
    )
    if expected != d["land_comparison"]:
        errors.append("Saved native-land comparison disagrees with actual PCB")
    native = json.loads((root / "analyses/native-lands.json").read_text())
    for name, expected in native["source_sha256"].items():
        if not checked_file(name, expected):
            errors.append(f"Native parser source missing/changed: {name}")
    if len(native["rows"]) != len(audit.LANDS):
        errors.append("Missing native land output")
    names = set()
    for row in native["rows"]:
        name = Path(row["file"]).stem
        names.add(name)
        if name not in audit.LANDS or not checked_file(row["file"], row["sha256"]):
            errors.append(f"Unknown/changed native land: {name}")
            continue
        land = audit.LANDS[name]
        pads = sorted(row["pads"], key=lambda p: p["number"])
        if len(pads) != 2:
            errors.append(f"Native two-pad count: {name}")
            continue
        for n, sign in [(0, -1), (1, 1)]:
            actual = pads[n]
            expected_xy = [sign * land["center_mm"], 0]
            if (
                actual["number"] != str(n + 1)
                or any(abs(a - b) > 1e-6 for a, b in zip(actual["xy_mm"], expected_xy))
                or any(abs(a - b) > 1e-6 for a, b in zip(actual["size_mm"], land["size_mm"]))
            ):
                errors.append(f"Native pad geometry mismatch: {name}.{n + 1}")
    if names != set(audit.LANDS):
        errors.append("Native library set mismatch")
    if native["physical_qualified"] or native["fabrication_released"]:
        errors.append("Unsupported native parser qualification")
    return errors


def verify_handoff(path=ROOT / "handoff.json"):
    d = json.loads(path.read_text())
    errors = handoff_contract_errors(d)
    for name, expected in d["files_sha256"].items():
        p = path.parent / name
        if not p.is_file() or sha(p) != expected:
            errors.append(f"Sealed byte mismatch: {name}")
    errors.extend(saved_errors())
    return errors


def handoff_contract_errors(d):
    errors = []
    for name in [
        "complete_0p1pct_closed",
        "production_selection_adopted",
        "physical_qualified",
        "electrical_qualified",
        "fabrication_released",
        "current_parent_electrical_board_claim",
    ]:
        if d.get(name) is not False:
            errors.append(f"Unsupported handoff contract: {name}")
    if d.get("passive_refs") != 196 or d.get("actual_native_land_candidates") != 9:
        errors.append("Handoff inventory mismatch")
    return errors


def seal():
    p = ROOT / "handoff.json"
    if p.exists():
        raise RuntimeError("Refusing to replace sealed evidence")
    errors = saved_errors()
    if errors:
        raise ValueError(errors)
    paths = sorted(
        x
        for x in ROOT.rglob("*")
        if x.is_file() and "__pycache__" not in x.parts and not x.name.endswith(".pyc")
    )
    data = dict(
        revision="NP01-passive-proposal-handoff",
        files_sha256={str(x.relative_to(ROOT)): sha(x) for x in paths},
        passive_refs=196,
        actual_native_land_candidates=9,
        complete_0p1pct_closed=False,
        production_selection_adopted=False,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        current_parent_electrical_board_claim=False,
        scopes=[
            "Immutable historical249 and pre-pin-correction261 passive identities",
            "Primary catalog-supported candidate order codes, no stock/RFQ guarantee",
            "Actual old233 pad extraction and nine NEW native-parsed two-pad land patterns",
            "Declared monitor/tolerance and DC power scenarios; no complete startup transient simulation",
        ],
    )
    p.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(dict(sealed_files=len(paths), sha256=sha(p), production_selection_adopted=False)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    if args.seal:
        seal()
    else:
        errors = verify_handoff() if (ROOT / "handoff.json").exists() else saved_errors()
        print(json.dumps(dict(errors=errors, electrical_qualified=False)))
        raise SystemExit(bool(errors))
