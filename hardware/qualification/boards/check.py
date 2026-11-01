"""Q02 physical capture checks with an explicit uncertainty decision rule."""

import argparse
import csv
import datetime as dt
import json
import math
from collections import Counter
from pathlib import Path

from ..check import artifact, nonempty, number, require, timestamp
from ..spec import REPO
from .requirements import build_plan

COLUMNS = ["case_id", "condition", "metric", "value", "expanded_uncertainty", "unit", "instrument_id"]


def decision(value, uncertainty, criterion):
    """Project rule, not a claim of laboratory accreditation or stated risk."""
    number(value, "measurement")
    number(uncertainty, "expanded uncertainty")
    require(uncertainty >= 0, "Negative uncertainty")
    low, high = value - uncertainty, value + uncertainty
    require(math.isfinite(low) and math.isfinite(high), "Uncertainty interval overflows")
    if criterion["unit"] == "count":
        require(value >= 0 and int(value) == value and uncertainty == 0, "Invalid exact count")
    else:
        require(uncertainty > 0, "Continuous physical measurements require positive expanded uncertainty")
    minimum, maximum = criterion["minimum"], criterion["maximum"]
    if (minimum is not None and high < minimum) or (maximum is not None and low > maximum):
        return "failed"
    if (minimum is not None and low < minimum) or (maximum is not None and high > maximum):
        return "blocked"
    if criterion["status"] != "defined_project_target":
        return "blocked"
    return "measured_pass"


def read_rows(reference, directory, case):
    artifact(reference, directory)
    rows = {}
    with (directory / reference["path"]).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == COLUMNS, "Unexpected measurement CSV columns/order")
        for row in reader:
            require(set(row) == set(COLUMNS) and None not in row.values(), "Malformed CSV row")
            require(row["case_id"] == case["id"], "CSV row belongs to another case")
            key = (row["condition"], row["metric"])
            require(key not in rows, "Duplicate condition/metric row")
            try:
                value, uncertainty = float(row["value"]), float(row["expanded_uncertainty"])
            except ValueError as error:
                raise ValueError("Invalid CSV numeric value") from error
            rows[key] = dict(
                value=value, uncertainty=uncertainty, unit=row["unit"], instrument_id=row["instrument_id"]
            )
    expected = {(c, m) for c in case["conditions"] for m in case["metrics"]}
    require(set(rows) == expected, "Missing/extra conditions or metrics in measurement CSV")
    return rows


def context(record, entry, case, plan, directory, now):
    board = plan["boards"][case["board"]]
    device = record.get("devices", {}).get(case["board"], {})
    for key in ["serial", "assembly_revision", "source_to_device_attestation"]:
        nonempty(device.get(key), "device." + key)
    require(
        device.get("variant") == board["variant"], "Wrong board variant; another candidate needs its own plan"
    )
    require(device.get("pcb_source_sha256") == board["pcb_sha256"], "Wrong fabricated PCB source")
    artifact(device.get("as_built_manifest"), directory)
    artifact(device.get("fabrication_package"), directory)
    nonempty(record.get("operator"), "operator")
    start, finish = timestamp(entry.get("started_at_utc")), timestamp(entry.get("finished_at_utc"))
    require(start <= finish <= now, "Invalid/future measurement interval")
    fixture = entry.get("fixture", {})
    require(fixture.get("plan_sha256") == plan["plan_sha256"], "Fixture review refers to another plan")
    require(fixture.get("board") == case["board"], "Fixture review refers to another board")
    nonempty(fixture.get("reviewer"), "fixture reviewer")
    require(timestamp(fixture.get("approved_at_utc")) <= start, "Fixture review postdates measurement")
    artifact(fixture.get("document"), directory)
    settings = fixture.get("condition_settings", {})
    require(set(settings) == set(case["conditions"]), "Fixture needs settings for every condition")
    for value in settings.values():
        nonempty(value, "declared condition settings")
    used = entry.get("instrument_ids", [])
    require(
        isinstance(used, list) and used and len(used) == len(set(used)), "Missing/duplicate instrument IDs"
    )
    instruments = record.get("instruments", [])
    require(
        isinstance(instruments, list) and all(isinstance(i, dict) for i in instruments),
        "Invalid instrument catalog",
    )
    by_id = {i.get("id"): i for i in instruments}
    require(len(by_id) == len(instruments) and None not in by_id, "Duplicate/missing instrument identifier")
    for identifier in used:
        require(identifier in by_id, "Unknown instrument")
        instrument = by_id[identifier]
        for key in ["id", "kind", "model", "serial"]:
            nonempty(instrument.get(key), "instrument." + key)
        if instrument["kind"] == "inspection":
            artifact(instrument.get("method_reference"), directory)
        else:
            calibration = instrument.get("calibration", {})
            require(
                timestamp(calibration.get("valid_from_utc"))
                <= start
                <= finish
                <= timestamp(calibration.get("valid_until_utc")),
                "Calibration does not cover measurement interval",
            )
            artifact(calibration.get("certificate"), directory)
    require(
        set(case["instrument_kinds"]) <= {by_id[i]["kind"] for i in used}, "Required instrument kinds missing"
    )
    if any(m["unit"] != "count" for m in case["metrics"].values()):
        budget = entry.get("uncertainty_budget", {})
        nonempty(budget.get("reviewer"), "uncertainty-budget reviewer")
        require(
            number(budget.get("coverage_probability"), "coverage probability") >= 0.95
            and budget["coverage_probability"] < 1,
            "Require declared coverage probability at least 0.95 and below 1",
        )
        require(number(budget.get("coverage_factor"), "coverage factor") >= 1, "Invalid coverage factor")
        require(timestamp(budget.get("approved_at_utc")) <= start, "Uncertainty review postdates measurement")
        artifact(budget.get("document"), directory)
    captures = entry.get("raw_captures", [])
    require(isinstance(captures, list) and captures, "Missing original instrument captures")
    covered = set()
    for capture in captures:
        artifact(capture, directory)
        require(
            capture["sha256"] != entry["measurements_csv"]["sha256"],
            "Summary CSV is not an independent raw capture",
        )
        conditions = capture.get("conditions", [])
        require(
            isinstance(conditions, list) and conditions and set(conditions) <= set(case["conditions"]),
            "Invalid raw-capture conditions",
        )
        covered.update(conditions)
    require(covered == set(case["conditions"]), "Raw captures do not cover every condition")
    return {identifier: by_id[identifier]["kind"] for identifier in used}


def evaluate(plan, record, directory, *, repo=REPO, now=None, allow_synthetic=False):
    directory = Path(directory)
    require(plan == build_plan(repo), "Plan is stale or its limits/holds were edited; regenerate/review")
    require(
        record.get("schema_version") == 2 and record.get("plan_sha256") == plan["plan_sha256"],
        "Wrong capture schema/plan",
    )
    require(
        record.get("source_sha256") == plan["source_sha256"], "Capture source snapshot is incomplete/stale"
    )
    synthetic = record.get("evidence_kind") == "synthetic_fixture"
    require(
        record.get("evidence_kind") == "physical_measurement" or (allow_synthetic and synthetic),
        "Synthetic fixtures cannot be accepted as physical measurements",
    )
    entries = record.get("cases", [])
    require(isinstance(entries, list) and all(isinstance(e, dict) for e in entries), "Invalid case list")
    specs = {c["id"]: c for c in plan["cases"]}
    require(
        len(entries) == len(specs) and {e.get("id") for e in entries} == set(specs),
        "Missing/duplicate/unknown case",
    )
    outcomes = []
    for entry in entries:
        case = specs[entry["id"]]
        state = entry.get("state")
        require(state in {"not_run", "blocked", "failed", "measured_pass"}, "Unknown case state")
        if not entry.get("measurements_csv"):
            require(state in {"not_run", "blocked"}, "A measured result requires the actual measurement CSV")
            require(
                not any(entry.get(k) for k in ["raw_captures", "started_at_utc", "finished_at_utc"]),
                "Partial measurement metadata is not an unrun case",
            )
            if state == "blocked":
                nonempty(entry.get("reason"), "blocked reason")
            outcomes.append(
                dict(
                    id=case["id"],
                    board=case["board"],
                    state=state,
                    reasons=[entry.get("reason")] if entry.get("reason") else [],
                )
            )
            continue
        require(state in {"blocked", "failed", "measured_pass"}, "Measured CSV cannot be labeled unrun")
        used = context(record, entry, case, plan, directory, now or dt.datetime.now(dt.timezone.utc))
        rows = read_rows(entry["measurements_csv"], directory, case)
        failed, pending = [], []
        for (condition, metric), row in rows.items():
            criterion = case["metrics"][metric]
            require(row["unit"] == criterion["unit"], "Measurement unit mismatch")
            require(row["instrument_id"] in used, "CSV instrument not listed for the case")
            require(
                used[row["instrument_id"]] in criterion["instrument_kinds"],
                "Instrument kind cannot measure this metric",
            )
            result = decision(row["value"], row["uncertainty"], criterion)
            if result == "failed":
                failed.append(condition + ": " + metric)
            elif result == "blocked":
                pending.append(condition + ": " + metric + " has an unresolved limit or uncertainty overlap")
        board = plan["boards"][case["board"]]
        if case["powered"] and not board["native_connectivity_closed"]:
            pending.append(
                "Selected board has native opens/DRC/parity issues; powered qualification is blocked"
            )
        derived = "failed" if failed else "blocked" if pending else "measured_pass"
        require(state == derived, f"Claimed {state} is unsupported; derived {derived}")
        outcomes.append(dict(id=case["id"], board=case["board"], state=derived, reasons=failed + pending))
    counts = dict(Counter(e["state"] for e in outcomes))
    boards = {
        key: dict(
            all_case_comparisons_passed=all(
                e["state"] == "measured_pass" for e in outcomes if e["board"] == key
            ),
            design_holds=board["holds"],
            qualified=False,
        )
        for key, board in plan["boards"].items()
    }
    return dict(
        revision="Q02",
        boards=boards,
        state_counts=counts,
        cases=outcomes,
        physical_cases_claimed=0 if synthetic else sum(bool(e.get("measurements_csv")) for e in entries),
        uncertainty_model_and_raw_capture_authenticity="operator/reviewer attested; not independently authenticated",
        fabrication_released=False,
        build_ready=False,
        complete_unit_qualified=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--plan", type=Path, default=Path(__file__).parent / "generated/plan.json")
    parser.add_argument("--captures-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    result = evaluate(
        json.loads(args.plan.read_text()),
        json.loads(args.record.read_text()),
        args.captures_root or args.record.parent,
    )
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["state_counts"], sort_keys=True))
    print("Board qualification: incomplete; no fabrication or complete-unit release")
    if args.require_pass and (
        not all(b["all_case_comparisons_passed"] for b in result["boards"].values())
        or any(b["design_holds"] for b in result["boards"].values())
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
