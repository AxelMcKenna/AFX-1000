"""Generate an unmeasured bench plan/capture template for the current snapshot."""

import json

from .spec import REPO, build_plan


def template(plan):
    return dict(
        schema_version=1,
        evidence_kind="physical_measurement",
        profile=plan["profile"],
        plan_sha256=plan["plan_sha256"],
        source_sha256=plan["source_sha256"],
        operator=None,
        device=dict(
            assembly_serial=None,
            hardware_revision=None,
            board_variant=None,
            firmware_sha256=None,
            firmware_image={},
            source_commit=None,
            build_source_attestation=None,
        ),
        setup=dict(
            description=None,
            ambient_c=None,
            current_limit_a=None,
            dummy_load_description=None,
            ground_probe_method=None,
            supply_and_fuse_description=None,
            fixture_release={},
        ),
        instruments=[],
        cases=[
            dict(
                id=c["id"],
                state="blocked" if c["requires_completed_system_design"] else "not_run",
                reason="System design/fixture prerequisites remain open"
                if c["requires_completed_system_design"]
                else None,
                dut=dict(board_serial=None, assembly_revision=None),
                fixture_release=None,
                started_at_utc=None,
                finished_at_utc=None,
                instrument_ids=[],
                readings=[],
                captures=[],
            )
            for c in plan["cases"]
        ],
    )


def main():
    plan = build_plan()
    folder = REPO / "hardware/qualification/generated"
    folder.mkdir(exist_ok=True)
    (folder / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    (folder / "capture-template.json").write_text(json.dumps(template(plan), indent=2) + "\n")
    print(
        f"Generated {len(plan['cases'])} planned cases; zero measurements; full-unit power-up remains unreleased."
    )


if __name__ == "__main__":
    main()
