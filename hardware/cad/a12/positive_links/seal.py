"""Seal the reviewable prototype only after its declared evidence is complete."""

import json

from .contract import problems
from .generate import OUT, REPO, ROOT, load, sha
from .verify import saved_report_errors, stale_paths


def main():
    assert not problems(load())
    r = json.loads((OUT / "verification.json").read_text())
    assert r.get("accepted_native_evidence") is True and r.get("validation_errors") == [], (
        "Native evidence was not accepted"
    )
    assert (
        not r["collision_failures"] and not r["stale_sources"] and not r["native_inputs_changed_during_run"]
    )
    assert r["positive_control_detected"] and len(r["native_checks"]) == 10
    assert not r["native_failures"]
    geometry = json.loads((OUT / "geometry.json").read_text())
    assert not saved_report_errors(r, geometry, OUT), "Cannot seal failed or absent actual native geometry"
    for group in ("source_sha256", "geometry_sha256", "native_input_sha256", "native_evidence_sha256"):
        assert not stale_paths(r[group], REPO), group
    for file in ("analysis.json", "geometry.json", "self-fit.json"):
        assert not stale_paths(json.loads((OUT / file).read_text())["source_sha256"], ROOT), file
    source = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".py", ".json", ".md")]
    source.append(REPO / "tests/tooling/test_positive_links.py")
    artifacts = [p for p in OUT.rglob("*") if p.is_file() and p.name != "review-packet.json"]
    report = dict(
        revision=load()["revision"],
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in source},
        evidence_sha256={str(p.relative_to(REPO)): sha(p) for p in artifacts},
        native_geometry_sources=r["source_sha256"],
        scope="Unreleased nominal/matched-configuration positive-link prototype; declared native screens and finite BREP witnesses only",
        all_continuous_receiving_support_tolerances_proved=False,
        physical_fit_verified=False,
        dielectric_qualified=False,
        complete_link_resistance_verified=False,
        mechanical_lifetime_qualified=False,
        fabrication_released=False,
        selected_for_production=False,
    )
    (OUT / "review-packet.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Sealed prototype review packet; all physical/release flags remain false.")


if __name__ == "__main__":
    main()
