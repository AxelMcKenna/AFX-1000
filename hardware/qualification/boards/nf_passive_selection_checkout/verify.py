"""Checkout-location successor; the sealed NP01 and NP01-P1 bytes stay intact.

Only recognized absolute checkout prefixes are canonicalized. The original
strict geometry/hash/type policy and four-ULP five-term-sum rule remain in use.
"""

import argparse
import hashlib
import importlib.util
import json
import platform
from pathlib import Path

from hardware.fabrication.evidence_paths import REPO, recorded_path
from hardware.qualification.boards.nf_passive_selection_portable import capture_runtime, policy, verify

EXPECTED_P1 = "2dde4793e191de4d765d169bbe77050343170791ba1d5f341317d9cf2dd8a6a9"


def canonical_locations(value):
    if isinstance(value,dict):
        result = {}
        for key,item in value.items():
            normalized = canonical_locations(key)
            if normalized in result:
                raise ValueError("Checkout canonicalization collides with another recorded key")
            result[normalized] = canonical_locations(item)
        return result
    if isinstance(value,list):
        return [canonical_locations(item) for item in value]
    if isinstance(value,str) and Path(value).is_absolute():
        path = recorded_path(value)
        if path.is_relative_to(REPO):
            return "${REPOSITORY}/"+str(path.relative_to(REPO))
    return value


def checked_file(name,expected):
    path = Path(name)
    path = recorded_path(path) if path.is_absolute() else verify.old_verify.ROOT/path
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected


def saved_errors():
    # Execute the sealed verifier in a private namespace. Relocate only its
    # file lookups; retain its complete numerical/land/evidence checks.
    source = Path(verify.old_verify.__file__)
    spec = importlib.util.spec_from_file_location("np01_checkout_saved_verifier",source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.checked_file = checked_file
    return module.saved_errors()


def check():
    parent = capture_runtime.check_parent()
    p1_root = Path(verify.__file__).parent
    p1_seal = p1_root/"handoff.json"
    if hashlib.sha256(p1_seal.read_bytes()).hexdigest() != EXPECTED_P1:
        raise ValueError("Wrong NP01-P1 parent seal")
    p1 = json.loads(p1_seal.read_text())
    for name,digest in p1["files_sha256"].items():
        if hashlib.sha256((p1_root/name).read_bytes()).hexdigest() != digest:
            raise ValueError("Changed NP01-P1 sealed input: "+name)
    stored = canonical_locations(verify.reference())
    replayed = canonical_locations(verify.runtime_payload())
    errors,accepted = policy.compare(stored,replayed)
    inherited = saved_errors()
    allowed = {"Saved additional life scenarios disagree with recalculation"} if not errors else set()
    # External byte checking is preserved by the original verifier; unknown
    # errors still fail even after the model comparison succeeds.
    errors += [dict(reason=message) for message in inherited if message not in allowed]
    capture_runtime.check_parent()
    sources = [Path(__file__),Path(policy.__file__),Path(capture_runtime.__file__),Path(verify.__file__),
        Path(verify.old_verify.__file__),REPO/"hardware/fabrication/evidence_paths.py"]
    return dict(revision="NP01-P2-checkout-replay",runtime=platform.python_version(),
        errors=errors,accepted_computed_sum_differences=accepted,
        original_parent_seal_sha256=capture_runtime.EXPECTED,parent_files_verified=len(parent["files_sha256"]),
        P1_parent_seal_sha256=EXPECTED_P1,P1_parent_files_verified=len(p1["files_sha256"]),
        only_recognized_repository_locations_canonicalized=True,policy_MAX_ULP_steps=policy.MAX_ULP_STEPS,
        legacy_exact_comparison_failures_preserved=inherited,physical_qualified=False,electrical_qualified=False,
        fabrication_released=False,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        raise RuntimeError("Fresh report required")
    report = check()
    if args.output:
        args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(revision=report["revision"],errors=report["errors"],
        parent_files_verified=report["parent_files_verified"],P1_parent_files_verified=report["P1_parent_files_verified"])))
    raise SystemExit(bool(report["errors"]))
