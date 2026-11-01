"""Independent saved-native/actual-artifact gate; no physical qualification claims."""

import json
import math
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.cad.a12.thermal.verify import binary_stl

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
PCB = "37fd610961d78a1336227015df1c58f8b609aac7fb424adbef3729718547243c"
CASES = (
    "geometry",
    "component_collision",
    "link_collision",
    "case_collision",
    "positive_control",
    "source_front_witness",
    "J106_tail_witness",
)


def artifact_errors(report, geometry, output=OUT):
    errors = []
    rows = report.get("native_checks", {})
    if set(rows) != set(CASES) or report.get("accepted_native_evidence") is not True:
        errors.append("Missing/rejected required native case")
    if any(report.get(k) for k in ["failed_cases", "stale_inputs", "changed_inputs"]):
        errors.append("Rejected or stale native inputs")
    expected_volume = sum(geometry["volumes_mm3"].values())
    if not math.isclose(expected_volume, 249.06, abs_tol=1e-6):
        errors.append("Wrong declared LAND/TIM volume")
    for name in CASES:
        row = rows.get(name, {})
        p = output / (name + ".stl")
        logpath = output / (name + ".log")
        if not logpath.exists():
            errors.append(name + ": native log missing")
            continue
        log = logpath.read_text()
        if name.endswith("collision") and row.get("result") == "empty":
            if p.exists():
                errors.append(name + ": forged empty row with actual STL")
            if (
                row.get("returncode") != 1
                or "Current top level object is empty." not in log
                or any(t in log for t in ["WARNING", "ERROR"])
            ):
                errors.append(name + ": invalid native empty evidence")
            continue
        if row.get("result") != "valid native manifold" or not p.exists():
            errors.append(name + ": required actual geometry missing")
            continue
        if row.get("returncode") != 0 or "NoError" not in log or any(t in log for t in ["WARNING", "ERROR"]):
            errors.append(name + ": invalid native solid evidence")
        try:
            actual = json.loads(json.dumps(binary_stl(p)))
        except (ValueError, AssertionError, OSError) as exc:
            errors.append(name + ": invalid STL " + str(exc))
            continue
        if any(actual.get(k) != row.get(k) for k in actual):
            errors.append(name + ": actual STL/row mismatch")
        if name.endswith("collision") and actual["volume_mm3"] > 1e-6:
            errors.append(name + ": collision")
        if name == "geometry" and not math.isclose(actual["volume_mm3"], expected_volume, rel_tol=0.0005):
            errors.append("Required LAND/TIM absent or wrong volume")
        if (name == "positive_control" or name.endswith("witness")) and not math.isclose(
            actual["volume_mm3"], 0.008, rel_tol=0.005, abs_tol=1e-6
        ):
            errors.append(name + ": witness failed")
    for name, expected in geometry["volumes_mm3"].items():
        p = output / (name + ".stl")
        if not p.exists() or not math.isclose(binary_stl(p)["volume_mm3"], expected, rel_tol=0.0005):
            errors.append(name + ": actual separate part missing/wrong volume")
    return errors


def captured_native_errors(folder=ROOT / "repaired"):
    errors = []
    receipt = json.loads((folder / "generated/current-native.json").read_text())
    capture = json.loads((folder / "evidence-capture.json").read_text())
    if sha(folder / "power_p03.kicad_pcb") != PCB or receipt["pcb_sha256"] != PCB:
        errors.append("Wrong selected electrical PCB")
    if capture["unavailable_current_bytes"] or capture["captured_native_receipt_sha256"] != sha(
        folder / "generated/current-native.json"
    ):
        errors.append("Incomplete captured electrical evidence")
    actual = {}
    for path, row in capture["captured"].items():
        if not (REPO / path).exists() or sha(REPO / path) != row["sha256"]:
            errors.append("Changed captured input:" + path)
        actual[(row["group"], row["original"])] = row["sha256"]
    required = {
        (group, p): h for group in ["source_sha256", "artifact_sha256"] for p, h in receipt[group].items()
    }
    if actual != required:
        errors.append("Missing/extra electrical proof capture")
    summary = json.loads((folder / "generated/complete-scratch-verification.json").read_text())
    if (
        summary["pcb_sha256"] != PCB
        or any(summary[k] != 0 for k in ["ERC", "DRC", "parity", "opens"])
        or receipt["native_counts"] != dict(ERC=0, DRC=0, parity=0, opens=0)
    ):
        errors.append("Electrical native closure not established")
    drc = json.loads((folder / "generated/complete-scratch-drc.json").read_text())
    erc = json.loads((folder / "generated/complete-scratch-erc.json").read_text())
    if any(drc[k] for k in ["violations", "unconnected_items", "schematic_parity"]):
        errors.append("Nonzero raw DRC/parity/opens")
    if any(sheet.get("violations") for sheet in erc["sheets"]):
        errors.append("Nonzero raw ERC")
    return errors


def packet_errors():
    native = json.loads((OUT / "verification.json").read_text())
    geometry = json.loads((OUT / "geometry.json").read_text())
    thermal = json.loads((OUT / "front-cell-thermal.json").read_text())
    errors = artifact_errors(native, geometry) + captured_native_errors()
    if geometry["candidate_pcb_sha256"] != PCB or thermal["pcb_sha256"] != PCB:
        errors.append("Mixed selected thermal/MCAD/electrical source")
    if geometry["actual_component_count"] != 507:
        errors.append("Missing actual body records")
    for flag in ["physical_fit_verified", "thermal_path_qualified", "fabrication_released"]:
        if geometry[flag] is not False or native[flag] is not False:
            errors.append("Unsupported native qualification:" + flag)
    for flag in [
        "thermal_path_qualified",
        "stability_qualified",
        "fabrication_released",
        "canonical_modified",
    ]:
        if thermal[flag] is not False:
            errors.append("Unsupported thermal qualification:" + flag)
    for name in [
        "package_upper_k_per_w",
        "total_path_upper_k_per_w",
        "actual_local_base_upper_c",
        "actual_positive_expanded_uncertainty_c",
    ]:
        if thermal[name] is not None:
            errors.append("Unestablished bound:" + name)
    if thermal["physical_tests_performed"] != 0:
        errors.append("Invented physical measurements")
    for group in [
        geometry["source_sha256"],
        geometry["reference_shared_source_sha256"],
        native["source_sha256"],
        native["evidence_sha256"],
        thermal["source_sha256"],
    ]:
        for path, expected in group.items():
            if not (REPO / path).exists() or sha(REPO / path) != expected:
                errors.append("Stale bound source/artifact:" + path)
    return errors


def saved_seal_errors(report=None):
    if report is None:
        report = json.loads((ROOT / "handoff.json").read_text())
    errors = []
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    ]
    actual = {str(p.relative_to(REPO)): sha(p) for p in paths}
    if report.get("sha256") != actual:
        errors.append("Sealed input/artifact set or bytes changed")
    if report.get("packet_integrity_accepted") is not True or report.get("errors"):
        errors.append("Rejected seal")
    return errors


def main():
    errors = packet_errors()
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p != ROOT / "handoff.json"
    ]
    report = dict(
        selected_pcb_sha256=PCB,
        packet_integrity_accepted=not errors,
        errors=errors,
        sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(paths)},
        raw_native_electrically_closed=True,
        thermal_path_qualified=False,
        stability_qualified=False,
        physical_tests_performed=0,
        canonical_modified=False,
        frozen_heat_kit_modified=False,
        fabrication_released=False,
    )
    (ROOT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    if errors:
        raise SystemExit("\n".join(errors))
    print("Selected37fd source/actual7-case/native artifact gate accepted; physical qualification false.")


if __name__ == "__main__":
    main()
