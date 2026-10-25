"""Validate a source-bound physical bench record without inventing measurements."""

import argparse
import datetime as dt
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path

from .spec import REPO, build_plan, digest

STATES = {"planned", "not_run", "measured_pass", "failed", "blocked"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(text):
    require(isinstance(text, str) and text.endswith("Z"), "Timestamp must be an explicit UTC ...Z value")
    try:
        return dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc


def number(value, label):
    require(type(value) in (int, float) and math.isfinite(value), "Non-finite/non-numeric " + label)
    return value


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), "Missing " + label)


def artifact(item, directory):
    require(isinstance(item, dict), "Capture/certificate reference must be an object")
    name = item.get("path")
    nonempty(name, "artifact path")
    path = Path(name)
    require(
        not path.is_absolute() and ".." not in path.parts, "Artifact path must stay inside capture directory"
    )
    path = (directory / path).resolve()
    require(path.is_relative_to(directory.resolve()), "Artifact symlink escapes capture directory")
    require(path.is_file() and path.stat().st_size > 0, "Missing/empty raw artifact: " + name)
    expected = item.get("sha256", "")
    require(
        isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
        "Missing/invalid artifact SHA-256",
    )
    require(digest(path) == expected, "Raw artifact checksum mismatch: " + name)


def valid_commit_format(commit):
    require(
        isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), "Invalid source commit context"
    )


def available_commit(commit, repo):
    return (
        subprocess.run(
            ["git", "cat-file", "-e", commit + "^{commit}"], cwd=repo, capture_output=True
        ).returncode
        == 0
    )


def commit_context(commit, repo, *, ancestor=None):
    valid_commit_format(commit)
    if not available_commit(commit, repo) or (ancestor and not available_commit(ancestor, repo)):
        return dict(
            verified=False,
            reason="Physical source ancestry is unavailable locally; fetch the required Git history before passing",
        )
    if ancestor:
        if (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, commit], cwd=repo, capture_output=True
            ).returncode
            != 0
        ):
            return dict(
                verified=False,
                reason="Physical source ancestry is not established; history may be incomplete or divergent",
            )
    return dict(verified=True, reason=None)


def validate_plan(plan, repo):
    require(isinstance(plan, dict), "Plan must be an object")
    base = plan.get("source_base_commit")
    valid_commit_format(base)
    expected = build_plan(repo, source_base_commit=base)
    # A caller cannot relax limits or remove holds by editing just the JSON plan.
    require(plan == expected, "Plan is edited/stale; regenerate and review its current source snapshot")
    # The base is informational: default shallow CI clones may lack its object.
    # Explicit input hashes and reconstructed requirements still define freshness.
    present = available_commit(base, repo)
    ancestry = (
        present
        and subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=repo, capture_output=True
        ).returncode
        == 0
    )
    return dict(
        base_object_available=present,
        base_is_current_ancestor=bool(ancestry),
        informational_context_verified=bool(ancestry),
    )


def physical_context(record, entry, case, plan, directory, now, repo):
    require(record.get("profile") == plan["profile"], "Wrong hardware/profile")
    device = record.get("device", {})
    for key in ["assembly_serial", "hardware_revision", "board_variant", "firmware_sha256", "source_commit"]:
        nonempty(device.get(key), "device." + key)
    require(
        device["board_variant"] == "E14/E25-baseline",
        "P01 or another hardware variant needs a separate reviewed plan",
    )
    require(re.fullmatch(r"[0-9a-f]{64}", device["firmware_sha256"]), "Invalid firmware SHA-256")
    artifact(device.get("firmware_image"), directory)
    require(
        device["firmware_image"]["sha256"] == device["firmware_sha256"],
        "Firmware image checksum disagrees with device record",
    )
    source_context = commit_context(device["source_commit"], repo, ancestor=plan["source_base_commit"])
    nonempty(device.get("build_source_attestation"), "firmware build/source attestation")
    dut = entry.get("dut", {})
    nonempty(dut.get("board_serial"), "case DUT board serial")
    nonempty(dut.get("assembly_revision"), "case DUT assembly revision")
    nonempty(record.get("operator"), "operator")
    setup = record.get("setup", {})
    for key in [
        "description",
        "dummy_load_description",
        "ground_probe_method",
        "supply_and_fuse_description",
    ]:
        nonempty(setup.get(key), "setup." + key)
    number(setup.get("ambient_c"), "ambient temperature")
    require(
        number(setup.get("current_limit_a"), "source current limit") > 0,
        "Source current limit must be positive",
    )
    release = entry.get("fixture_release") or setup.get("fixture_release", {})
    require(release.get("plan_sha256") == plan["plan_sha256"], "Fixture review does not bind this plan")
    nonempty(release.get("reviewer"), "fixture reviewer")
    require(
        release.get("scope") == ("system" if case["requires_completed_system_design"] else "isolated_board"),
        "Wrong fixture-release scope",
    )
    artifact(release.get("document"), directory)
    start, finish = timestamp(entry.get("started_at_utc")), timestamp(entry.get("finished_at_utc"))
    require(start <= finish <= now, "Measurement time interval is invalid or in the future")
    require(timestamp(release.get("approved_at_utc")) <= start, "Fixture approval postdates the test")
    instruments = record.get("instruments", [])
    require(isinstance(instruments, list), "Instruments must be a list")
    by_id = {}
    for instrument in instruments:
        require(isinstance(instrument, dict), "Instrument record must be an object")
        for key in ["id", "kind", "model", "serial"]:
            nonempty(instrument.get(key), "instrument." + key)
        require(instrument["id"] not in by_id, "Duplicated instrument ID")
        by_id[instrument["id"]] = instrument
    ids = entry.get("instrument_ids", [])
    require(
        isinstance(ids, list) and ids and len(ids) == len(set(ids)), "Missing/duplicated case instrument IDs"
    )
    used_kinds = set()
    for identifier in ids:
        require(identifier in by_id, "Unknown case instrument ID")
        instrument = by_id[identifier]
        used_kinds.add(instrument["kind"])
        calibration = instrument.get("calibration", {})
        require(calibration.get("state") == "current", "Instrument calibration is missing/not current")
        require(
            timestamp(calibration.get("valid_from_utc")) <= start
            and timestamp(calibration.get("valid_until_utc")) >= finish,
            "Calibration does not cover the measurement interval",
        )
        artifact(calibration.get("certificate"), directory)
    require(set(case["instrument_kinds"]) <= used_kinds, "Required instrument kinds are missing")
    captures = entry.get("captures", [])
    require(isinstance(captures, list) and captures, "Measured data requires hashed raw captures")
    covered = set()
    for capture in captures:
        artifact(capture, directory)
        conditions = capture.get("conditions", [])
        require(isinstance(conditions, list) and conditions, "Capture needs its condition labels")
        require(set(conditions) <= set(case["conditions"]), "Unknown capture condition")
        covered.update(conditions)
    require(covered == set(case["conditions"]), "Raw captures do not cover every required condition")
    return (finish - start).total_seconds(), source_context


def evaluate(plan, record, directory, *, repo=REPO, now=None, allow_synthetic=False):
    directory = Path(directory)
    now = now or dt.datetime.now(dt.timezone.utc)
    base_context = validate_plan(plan, repo)
    require(isinstance(record, dict), "Capture record must be an object")
    require(record.get("schema_version") == 1, "Wrong capture schema")
    require(record.get("plan_sha256") == plan["plan_sha256"], "Capture refers to another plan")
    synthetic = record.get("evidence_kind") == "synthetic_fixture"
    require(
        record.get("evidence_kind") == "physical_measurement" or (allow_synthetic and synthetic),
        "Synthetic fixtures cannot be submitted as physical bench evidence",
    )
    require(
        record.get("source_sha256") == plan["source_sha256"], "Capture source snapshot is incomplete/stale"
    )
    specs = {case["id"]: case for case in plan["cases"]}
    entries = record.get("cases", [])
    require(isinstance(entries, list), "Cases must be a list")
    require(all(isinstance(entry, dict) for entry in entries), "Case record must be an object")
    require(
        len(entries) == len(specs) and {e.get("id") for e in entries} == set(specs),
        "Missing, duplicate or unknown cases",
    )
    outcomes = []
    claimed_states = {entry["id"]: entry.get("state") for entry in entries}
    for entry in entries:
        case = specs[entry["id"]]
        requested = entry.get("state")
        require(requested in STATES, "Unknown case state")
        readings = entry.get("readings", [])
        require(isinstance(readings, list), "Readings must be a list")
        if not readings:
            require(requested in {"planned", "not_run", "blocked"}, "A measured result cannot omit readings")
            require(
                not entry.get("captures")
                and not entry.get("started_at_utc")
                and not entry.get("finished_at_utc"),
                "Partially measured cases require complete evidence/context",
            )
            if requested == "blocked":
                nonempty(entry.get("reason"), "blocked-case reason")
            outcomes.append(
                dict(
                    id=case["id"],
                    state=requested,
                    reasons=[entry.get("reason")] if entry.get("reason") else [],
                )
            )
            continue
        require(
            requested in {"measured_pass", "failed", "blocked"},
            "Measured data cannot be labeled planned/not_run",
        )
        elapsed, source_context = physical_context(record, entry, case, plan, directory, now, repo)
        require(all(isinstance(reading, dict) for reading in readings), "Reading must be an object")
        require(
            isinstance(readings, list)
            and len(readings) == len(case["conditions"])
            and {r.get("condition") for r in readings} == set(case["conditions"]),
            "Incomplete or duplicated condition readings",
        )
        failures, pending = [], []
        if not source_context["verified"]:
            pending.append(source_context["reason"])
        for reading in readings:
            values = reading.get("values", {})
            require(isinstance(values, dict), "Measured values must be an object")
            require(set(values) == set(case["metrics"]), "Missing or unknown measured metrics")
            for key, limit in case["metrics"].items():
                value = values[key]
                if limit["unit"] == "bool":
                    require(type(value) is bool, "Boolean observation must be true/false")
                    if value != limit["expected"]:
                        failures.append(reading["condition"] + ": " + key)
                else:
                    number(value, key)
                    minimum, maximum = limit["minimum"], limit["maximum"]
                    if (
                        case["id"] == "audio_quality"
                        and key == "snr_db"
                        and reading["condition"] == "send_return"
                    ):
                        minimum = 102
                    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
                        failures.append(reading["condition"] + ": " + key)
                    if key == "duration_s" and value > elapsed + 1:
                        failures.append("Claimed duration exceeds timestamp interval")
                if limit["limit_status"] == "unqualified":
                    pending.append("Unqualified acceptance limit/method: " + key)
            if "minimum_v" in values:
                require(values["minimum_v"] <= values["maximum_v"], "Voltage extrema are reversed")
        if case["requires_completed_system_design"]:
            pending.extend(plan["hard_holds"].values())
            pending.extend(
                "Earlier stage is not passed: " + identifier
                for identifier in case["requires_case_ids"]
                if claimed_states[identifier] != "measured_pass"
            )
        result = "failed" if failures else "blocked" if pending else "measured_pass"
        require(requested == result, f"Claimed {requested} cannot be substantiated; derived {result}")
        outcomes.append(dict(id=case["id"], state=result, reasons=sorted(set(failures + pending))))
    counts = dict(Counter(case["state"] for case in outcomes))
    return dict(
        schema_version=1,
        profile=plan["profile"],
        plan_sha256=plan["plan_sha256"],
        source_base_context=base_context,
        evidence_kind=record["evidence_kind"],
        cases=outcomes,
        state_counts=counts,
        all_case_comparisons_passed=counts.get("measured_pass", 0) == len(specs),
        physical_measurements_claimed=any(e["readings"] for e in entries) and not synthetic,
        raw_artifact_authenticity_independently_verified=False,
        firmware_build_to_source_linkage="operator_attestation_not_independently_rebuilt",
        full_unit_power_up_released=False,
        build_ready=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--plan", type=Path, default=REPO / "hardware/qualification/generated/plan.json")
    parser.add_argument("--captures-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Exit 2 unless every physical case comparison passes; still never grants a power-up release",
    )
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    record = json.loads(args.record.read_text())
    result = evaluate(plan, record, args.captures_root or args.record.parent)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(json.dumps(result["state_counts"], sort_keys=True))
    print("Build-ready: false. An evidence-format check does not grant a power-up release.")
    if args.require_pass and not result["all_case_comparisons_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
