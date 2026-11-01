"""Generate a completely unmeasured Q02 packet for the three pictured boards."""

import csv
import json
from pathlib import Path

from .check import COLUMNS
from .requirements import build_plan


def template(plan):
    return dict(
        schema_version=2,
        evidence_kind="physical_measurement",
        plan_sha256=plan["plan_sha256"],
        source_sha256=plan["source_sha256"],
        operator=None,
        devices={},
        instruments=[],
        cases=[
            dict(
                id=c["id"],
                state="not_run" if not c["powered"] else "blocked",
                reason=None
                if not c["powered"]
                else "Selected assembly, fixture and physical measurement prerequisites are not satisfied",
                measurements_csv=None,
                started_at_utc=None,
                finished_at_utc=None,
                raw_captures=[],
            )
            for c in plan["cases"]
        ],
    )


def main():
    plan = build_plan()
    folder = Path(__file__).parent / "generated"
    folder.mkdir(exist_ok=True)
    (folder / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    (folder / "capture-template.json").write_text(json.dumps(template(plan), indent=2) + "\n")
    with (folder / "measurements-header.csv").open("w", newline="") as stream:
        csv.writer(stream).writerow(COLUMNS)
    print(f"Q02: {len(plan['cases'])} cases for three exact PCB snapshots; zero measurements")


if __name__ == "__main__":
    main()
