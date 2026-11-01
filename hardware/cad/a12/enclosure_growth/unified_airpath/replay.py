"""New-output replay of the captured scene; never recaptures live PCB sources."""

import argparse
from pathlib import Path

from . import audit, verify_review, verify_service, verify_v6
from .ground_route import ROOT


def validate_destination(out):
    out = Path(out).resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError("Use a NEW output directory outside the immutable UA01 packet")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kind", required=True, choices=["main42", "service8", "review2"])
    p.add_argument("--outdir", required=True, type=Path)
    a = p.parse_args()
    out = validate_destination(a.outdir)
    bad = audit.errors()
    if bad:
        raise RuntimeError(bad)
    tool = {"main42": verify_v6, "service8": verify_service, "review2": verify_review}[a.kind]
    result = tool.run(out)
    # main42 is deliberately expected to fail the guide-left-in-place case.
    return int(not result["all_requested_clear"])


if __name__ == "__main__":
    raise SystemExit(main())
