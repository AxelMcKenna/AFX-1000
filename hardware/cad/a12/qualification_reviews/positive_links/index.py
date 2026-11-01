"""Complete direct file inventory supplement; the sealed PB02 packet stays unchanged."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
PACKET = REPO / "hardware/cad/a12/positive_links/proposals/dig-leg-y121p3"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    handoff = json.loads((PACKET / "handoff.json").read_text())
    for n, expected in handoff["files_sha256"].items():
        assert sha(PACKET / n) == expected, n
    files = {
        str(p.relative_to(PACKET)): sha(p)
        for p in sorted(PACKET.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    omitted = sorted(set(files) - set(handoff["files_sha256"]) - {"handoff.json"})
    assert len(omitted) == 18 and all(Path(n).name == "handoff.json" for n in omitted)
    # The original generator excluded that basename at all levels. Bind those
    # captured parent receipts directly here, plus the original handoff itself.
    result = dict(
        scope=__doc__,
        original_handoff_sha256=sha(PACKET / "handoff.json"),
        original_flat_file_entries=len(handoff["files_sha256"]),
        complete_direct_file_entries=len(files),
        additionally_directly_indexed_nested_receipts=omitted,
        original_packet_modified=False,
        new_geometry_or_release_approval_granted=False,
        files_relative_to=str(PACKET.relative_to(REPO)),
        files_sha256=files,
        index_script_sha256=sha(Path(__file__)),
    )
    (ROOT / "packet-index.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PB02 complete direct inventory:", len(files), "files;18nestedreceipts additionally bound")


if __name__ == "__main__":
    main()
