"""Three-way authored-object composition; native checks remain mandatory.

Zone fill is discarded and must be recomputed. Conflicting UUID edits fail
closed; matching UUIDs are never treated as permission to concatenate copper.
"""

import copy
import hashlib

from ...common.sexpr import children, first, sexpr


def authored(obj):
    result = copy.deepcopy(obj)
    if result[0] == "zone":
        result[:] = [
            q
            for q in result
            if not isinstance(q, list) or not q or q[0] not in {"filled_polygon", "fill_segments"}
        ]
    return result


def inventory(tree):
    result = {}
    for obj in tree[1:]:
        if not isinstance(obj, list):
            continue
        if children(obj, "uuid"):
            key = f"{obj[0]}:{first(obj, 'uuid')[1]}"
        elif obj[0] == "net":
            key = f"net:{obj[-1]}"
        else:
            key = f"single:{obj[0]}"
        assert key not in result, f"Duplicate top-level object identity: {key}"
        result[key] = authored(obj)
    return result


def merge(base, left, right):
    states = [inventory(t) for t in (base, left, right)]
    before, lhs, rhs = states
    edits = []
    for branch in (lhs, rhs):
        edits.append({k for k in before.keys() | branch.keys() if before.get(k) != branch.get(k)})
    shared = edits[0] & edits[1]
    conflicts = [k for k in shared if lhs.get(k) != rhs.get(k)]
    assert not conflicts, f"Conflicting shared-source object edits: {sorted(conflicts)}"
    final = dict(before)
    ledger = []
    for name, branch, changed in zip(("AUX", "U10"), (lhs, rhs), edits):
        for key in sorted(changed):
            old, new = before.get(key), branch.get(key)
            if new is None:
                final.pop(key, None)
            else:
                final[key] = new
            ledger.append(
                dict(
                    branch=name,
                    key=key,
                    before_authored_sexpr=None if old is None else sexpr(old),
                    after_authored_sexpr=None if new is None else sexpr(new),
                )
            )
    # Preserve base ordering, then deterministic ordering for genuinely new UUIDs.
    keys = list(before) + sorted(final.keys() - before.keys())
    result = [base[0]] + [copy.deepcopy(final[k]) for k in keys if k in final]
    assert inventory(result) == final
    return result, dict(
        method="Common-source authored-object three-way merge; zone fills discarded for native refill",
        auxiliary_changed_objects=len(edits[0]),
        u10_changed_objects=len(edits[1]),
        shared_changed_objects=sorted(shared),
        conflicting_objects=[],
        exact_authored_object_edits=ledger,
        authored_result_sha256=hashlib.sha256(sexpr(result).encode()).hexdigest(),
        native_refill_erc_drc_parity_and_connectivity_required=True,
        inherited_thermal_result_accepted=False,
        physical_qualified=False,
    )
