"""Reviewable exact board-object delta and byte-checked replay.

This records literal physical edits; it does not prove electrical correctness.
Native, copper, MCAD and physical evidence remain separate required artifacts.
"""

import argparse
import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path

from ...common.sexpr import read_sexpr, sexpr


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make(original, candidate):
    old_bytes, new_bytes = original.read_bytes(), candidate.read_bytes()
    old, new = read_sexpr(old_bytes.decode()), read_sexpr(new_bytes.decode())
    # Every source occurrence retains its identity, including duplicate nodes.
    available = defaultdict(deque)
    for index, node in enumerate(old):
        available[sexpr(node)].append(index)
    plan, retained = [], set()
    for node in new:
        text = sexpr(node)
        if available[text]:
            index = available[text].popleft()
            plan.append(dict(source_index=index))
            retained.add(index)
        else:
            plan.append(dict(new_literal=text))
    assert (sexpr(new) + "\n").encode() == new_bytes, "Candidate must use declared serializer"
    return dict(
        format="E28 literal top-level board-object delta v1",
        source_pcb_sha256=sha(old_bytes),
        target_pcb_sha256=sha(new_bytes),
        serializer_sha256=sha(Path(__file__).parents[2].joinpath("common/sexpr.py").read_bytes()),
        recipe_sha256=sha(Path(__file__).read_bytes()),
        plan=plan,
        removed_original_nodes=[
            dict(source_index=i, original_literal=sexpr(n)) for i, n in enumerate(old) if i not in retained
        ],
        electrical_and_physical_correctness_proved=False,
    )


def replay(original, delta, destination):
    original_bytes = original.read_bytes()
    assert sha(original_bytes) == delta["source_pcb_sha256"], "Wrong source bytes"
    assert (
        sha(Path(__file__).parents[2].joinpath("common/sexpr.py").read_bytes()) == delta["serializer_sha256"]
    ), "Wrong serializer"
    source = read_sexpr(original_bytes.decode())
    target = []
    used = set()
    for row in delta["plan"]:
        assert set(row) in ({"source_index"}, {"new_literal"})
        if "source_index" in row:
            index = row["source_index"]
            assert isinstance(index, int) and 0 <= index < len(source) and index not in used
            target.append(source[index])
            used.add(index)
        else:
            target.append(read_sexpr(row["new_literal"]))
    actual_removed = [
        dict(source_index=i, original_literal=sexpr(n)) for i, n in enumerate(source) if i not in used
    ]
    assert actual_removed == delta["removed_original_nodes"], "Removed-object ledger changed"
    output = (sexpr(target) + "\n").encode()
    assert sha(output) == delta["target_pcb_sha256"], "Replay does not reproduce target bytes"
    assert not destination.exists(), "Replay output must be new"
    destination.write_bytes(output)
    return sha(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("make", "replay"))
    parser.add_argument("source", type=Path)
    parser.add_argument("candidate_or_delta", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.operation == "make":
        assert not args.output.exists()
        args.output.write_text(json.dumps(make(args.source, args.candidate_or_delta), indent=2) + "\n")
    else:
        print(replay(args.source, json.loads(args.candidate_or_delta.read_text()), args.output))
