"""Portable source-only readers for frozen native CAD audit evidence.

Historical native generators retain their exact recorded source bytes. These
readers verify the same removal inventories and hashes in a relocated checkout
without importing KiCad's native Python bindings.
"""

import copy
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.evidence_paths import recorded_path

ROOT = Path(__file__).resolve().parent


def normalize_annotation_half_turns(tree):
    result = copy.deepcopy(tree)
    for fp in children(result, 'footprint'):
        for node in children(fp, 'property')+children(fp, 'fp_text'):
            at = children(node, 'at')
            if at and len(at[0]) > 3:
                at[0][3] = float(at[0][3]) % 180
    return result


def verified_removed_objects(receipts, expected_count):
    rows = []
    for path in receipts:
        report = json.loads(path.read_text())
        for name, digest in report["source_sha256"].items():
            assert sha(recorded_path(name)) == digest, "Changed recorded removal dependency: "+name
        rows.extend(report["removed_objects"])
    assert len(rows) == expected_count
    assert len({str(first(row, "uuid")[1]) for row in rows}) == expected_count, "Duplicate removal UUID"
    return rows, receipts


def removed_logic_swap_nodes():
    receipts = [ROOT / "staging" / name / "construction.json"
                for name in ("nf-logic-swap-prepared-01", "nf-logic-swap-leaves-01")]
    return verified_removed_objects(receipts, 203)


def removed_stage_repack_nodes():
    receipts = [ROOT / "staging" / name / "construction.json"
                for name in ("nf-logic-swap-reserved-01", "nf-stage-escape-repack-01")]
    return verified_removed_objects(receipts, 188)
