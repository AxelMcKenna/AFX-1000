"""Reproduce a saved source-exit search candidate in the full native checker.

The profile table is extended only in this CLI process under a scoped restore.
The exact receipt, wrapper and all searched source/obstacle bytes are bound to
the generated report. Shared code and canonical hardware are not edited.
"""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from ..generate import REPO, sha
from . import output_formed

ROOT = Path(__file__).resolve().parent


def run(receipt_file, executable):
    chosen = json.loads(receipt_file.read_text())
    candidate = REPO / chosen["source_candidate"]
    assert sha(candidate / "rail_disconnect.kicad_pcb") == chosen["source_candidate_expected_pcb_sha256"]
    assert chosen["position_allocation_each_wire_mm"] == 0.65
    assert chosen["clearance_mm"] == 0.25 and chosen["geometry_reserve_mm"] == 0.005
    dependencies = dict(chosen["original_source_evidence_sha256"])
    for name, expected in chosen["local_input_evidence_sha256"].items():
        path = (receipt_file.parent / name).resolve()
        relative = str(path.relative_to(REPO))
        dependencies[relative] = expected
    assert all(sha(REPO / n) == h for n, h in dependencies.items()), "Search receipt is stale"
    key = chosen["profile_key_for_private_wrapper"]
    out = ROOT / "generated" / ("selected-exit-" + receipt_file.stem)
    before = dict(output_formed.PROFILES)
    with patch.dict(output_formed.PROFILES, {key: chosen["profiles"]}):
        report = output_formed.generate(out, key, candidate)
    assert output_formed.PROFILES == before
    report["source_sha256"].update(dependencies)
    for p in [Path(__file__), receipt_file]:
        report["source_sha256"][str(p.relative_to(REPO))] = sha(p)
    report["saved_profile_receipt"] = str(receipt_file.relative_to(REPO))
    report["source_search_is_native_evidence"] = False
    assert all(sha(REPO / n) == h for n, h in report["source_sha256"].items())
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Native-checking saved profiles", chosen["profiles"], flush=True)
    return output_formed.verify(executable, out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--openscad", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.receipt.resolve(), args.openscad)
    raise SystemExit(0 if result["local_formed_escape_clear"] else 1)
