"""Read-only native connectivity test of one unlocked fault-network cage."""

import hashlib
import json
import tempfile
from pathlib import Path

import pcbnew

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "generated/u14-residual-batch1-work"


def groups(board):
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    items = [t for t in board.GetTracks() if t.GetNetname().lstrip("/") == "E28_FAULT"]
    items += [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname().lstrip("/") == "E28_FAULT"]
    by_id = {p.m_Uuid.AsString(): p for p in items}
    parent = {u: u for u in by_id}

    def root(u):
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    for u, p in by_id.items():
        for q in connection.GetConnectedItems(p):
            v = q.m_Uuid.AsString()
            if v in parent:
                parent[root(v)] = root(u)
    result = {}
    for u, p in by_id.items():
        entry = result.setdefault(root(u), dict(objects=0, pads=[]))
        entry["objects"] += 1
        if p.GetClass() == "PAD":
            entry["pads"].append(p.GetParentFootprint().GetReference() + "." + p.GetNumber())
    return sorted(
        (dict(objects=r["objects"], pads=sorted(r["pads"])) for r in result.values()),
        key=lambda r: (r["pads"], r["objects"]),
    )


def main():
    path = WORK / "generated/filled-surface-batch1.kicad_pcb"
    blob = path.read_bytes()
    board = pcbnew.LoadBoard(str(path))
    before = groups(board)
    targets = {"24368a33-4443-5a3b-9a96-b1958a4bb6f2", "93e0b220-8954-5d78-87ee-32ccee816e59"}
    removed = []
    for t in list(board.GetTracks()):
        pos = t.GetPosition()
        via = (
            t.GetClass() == "PCB_VIA"
            and abs(pcbnew.ToMM(pos.x) - 233.7) < 1e-6
            and abs(pcbnew.ToMM(pos.y) - 132.7) < 1e-6
        )
        if t.m_Uuid.AsString() in targets or via:
            assert t.GetNetname().lstrip("/") == "E28_FAULT"
            removed.append(dict(uuid=t.m_Uuid.AsString(), kind=t.GetClass(), net=t.GetNetname()))
    assert len(removed) == 3
    locked = {
        r["uuid"]
        for r in json.loads((ROOT / "generated/leaf-prune-source-lock-contract.json").read_text())[
            "locked_copper"
        ]
    }
    assert not locked & {r["uuid"] for r in removed}
    ids = {r["uuid"] for r in removed}
    tree = read_sexpr(blob.decode())
    retained = [
        n
        for n in tree
        if not (
            isinstance(n, list)
            and n
            and n[0] in ("segment", "via")
            and children(n, "uuid")
            and str(first(n, "uuid")[1]) in ids
        )
    ]
    assert len(tree) - len(retained) == 3
    # KiCad10's Python Remove container ownership is unreliable here. Load a
    # distinct, explicit three-object edit instead; never save the source.
    with tempfile.TemporaryDirectory(prefix="afx-e28-fault-cycle-") as directory:
        trial = Path(directory) / "trial.kicad_pcb"
        trial.write_text(sexpr(retained) + "\n")
        after = groups(pcbnew.LoadBoard(str(trial)))
    result = dict(
        source_filled_sha256=hashlib.sha256(blob).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        before_components=before,
        after_components=after,
        simulation_removed_objects=removed,
        logical_pad_partition_unchanged=sorted(r["pads"] for r in before) == sorted(r["pads"] for r in after),
        simulated_only_no_source_or_product_written=True,
        qualification=False,
    )
    (WORK / "generated/fault-cycle-probe.json").write_text(json.dumps(result, indent=2) + "\n")
    assert path.read_bytes() == blob
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
