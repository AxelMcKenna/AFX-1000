"""Bind E27 native and diagnostic findings; never substitute them for measurements."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_fingerprints(report):
    fingerprints = report.get("source_sha256", {})
    assert fingerprints, "Missing source fingerprints"
    for name, expected in fingerprints.items():
        path = (REPO / name).resolve()
        assert path.is_relative_to(REPO) and path.is_file(), name
        assert sha(path) == expected, ("Changed source/evidence", name)
    return len(fingerprints)


def validate_native(report, native):
    assert report["native_drc_violations"] == len(native["violations"])
    assert report["native_open_connections"] == len(native["unconnected_items"])
    assert report["schematic_parity_issues"] == len(native["schematic_parity"])
    assert report["connectivity_closed"] == (not native["unconnected_items"])
    assert report["strict_native_check_passed"] == (
        not native["violations"] and not native["schematic_parity"] and report["native_erc_violations"] == 0
    )
    assert not report["build_ready"] and not report["physical_fit_verified"]


def analyze():
    out = ROOT / "generated"

    def read(name):
        return json.loads((out / name).read_text())

    native = read("pilot-findings.json")
    raw = read("drc.json")
    copper = read("copper-diagnostic.json")
    returns = read("return-diagnostic.json")
    devices = read("device-review.json")
    counts = {
        name: verify_fingerprints(r)
        for name, r in [("native", native), ("copper", copper), ("return", returns), ("devices", devices)]
    }
    validate_native(native, raw)
    board_hash = sha(out / "filled.kicad_pcb")
    assert copper["board_sha256"] == returns["board_sha256"] == board_hash, "Model uses another filled board"
    assert native["pcb_sha256"] == sha(ROOT / "rail_disconnect.kicad_pcb")
    dimensions = devices["mosfet_land_review"]
    unapproved = [
        r["ref"]
        for r in dimensions
        if not r["recommended_pattern_matched"]
        and not r["alternate_manufacturer_or_assembly_approval_present"]
    ]
    report = dict(
        revision="E27-design-qualification-audit",
        scope="Independent source-bound circuit, native routing, geometry diagnostics and manufacturer consistency; zero physical measurements",
        native={
            k: native[k]
            for k in [
                "native_erc_violations",
                "native_drc_violations",
                "native_open_connections",
                "schematic_parity_issues",
                "routed_segments",
                "through_vias",
                "strict_native_check_passed",
            ]
        },
        source_records_checked=counts,
        model_copper_positive_path_sums=copper["positive_path_sums"],
        manufacturer_land_pattern_unapproved_references=unapproved,
        dielectric_stackup_defined=copper["dielectric_stackup_defined"],
        findings=[
            dict(
                id="CONNECTIVITY",
                status="failed" if native["native_open_connections"] else "passed",
                detail="Every remaining native open and warning retained; incomplete OV/control branches can prevent or defeat the interlock.",
            ),
            dict(
                id="MOSFET_LANDS",
                status="unqualified" if unapproved else "review_required",
                detail="Source/gate lands differ from TI recommended geometry; no alternative manufacturing/assembly approval recorded.",
            ),
            dict(
                id="ANALOG_COPPER",
                status="diagnostic_exceeds_allocation"
                if any(r["estimate_exceeds_allocation"] for r in copper["positive_path_sums"]["analog"])
                else "unqualified",
                detail="Actual filled-copper diagnostic versus P02 3mohm positive-path allocation; mesh is not a certified bound.",
            ),
            dict(
                id="RETURN_CONTACTS",
                status="unimplemented",
                detail="Proposed source straps/studs/lands remain absent. Header-pair resistance is not multiport transfer or full strap/contact resistance.",
            ),
            dict(
                id="GATE_TIMING",
                status="unqualified",
                detail="Four digital FETs have 612x the datasheet 100pF test charge at the specified manufacturer test point; no system 125us fault bound follows.",
            ),
            dict(
                id="LATE_CLOSURE_SOA",
                status="unqualified",
                detail="No independent current limiter; stored/charging energy and current pulses require real VDS/ID/time waveforms and hot SOA review, not avalanche-rating comparison.",
            ),
            dict(
                id="STACKUP_THERMAL",
                status="unqualified",
                detail="70um finished copper and 25um plating are assumptions, not a purchased or verified dielectric/copper/plating process.",
            ),
            dict(
                id="PARTIAL_POWER",
                status="unqualified",
                detail="OV-only level interlock adds no undervoltage qualification, fault latch, rapid protected-bulk discharge or complete signal-pin backfeed isolation.",
            ),
        ],
        physical_tests_required=[
            "Manufacturer/assembler approval of terminal, mask, paste, drill/plating and completed manufacturing outputs",
            "Four-wire hot/cold source/common/protected and return/contact measurements, including diagonal digital current sharing",
            "Loaded threshold and all-gate turn-off captures over input, fault and temperature conditions",
            "Cold and partial-charge late closure: simultaneous device VDS/ID/VGS and protected rail overshoot; hot transient SOA assessment",
            "Auxiliary loss, reference open/short, negative-rail partial power, backfeed and protected-bulk hold-up/discharge",
            "Enclosed thermal, ripple/EMI and actual bypass/contact recovery with the completed compatible assembly",
        ],
        physical_measurements_performed=0,
        electrical_performance_qualified=False,
        physical_fault_or_startup_verified=False,
        copper_loss_qualified=False,
        manufacturer_land_pattern_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    files = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.name != "qualification.json"
    ]
    files += [REPO / "tests/tooling/test_disconnect_revision27.py"]
    report["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in sorted(set(files))}
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    r = analyze()
    content = json.dumps(r, indent=2) + "\n"
    path = ROOT / "generated/qualification.json"
    if args.check:
        assert path.read_text() == content, "Stale qualification audit"
    else:
        path.write_text(content)
    print(
        "E27 audit:",
        r["native"]["native_open_connections"],
        "opens;",
        r["native"]["native_drc_violations"],
        "DRC findings;",
        len(r["manufacturer_land_pattern_unapproved_references"]),
        "unapproved FET footprints; physical measurements=0; build-ready=false",
    )


if __name__ == "__main__":
    main()
