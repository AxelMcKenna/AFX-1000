"""Complete explicit graph-cut gaps using only raw native failed boundary tracks."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .schmitt_cone_candidate import GROUPS, ROOT

SOURCE = ROOT / "generated/schmitt-near-receiver-trial-work"
WORK = ROOT / "generated/schmitt-near-receiver-clear-work"


def main():
    assert not WORK.exists()
    p = SOURCE / "rail_disconnect.kicad_pcb"
    blob = p.read_bytes()
    t = read_sexpr(blob.decode())
    d = SOURCE / "generated/drc-schmitt-near-receiver.json"
    raw = json.loads(d.read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    allowed = set(GROUPS[0])
    by = {str(first(n, "uuid")[1]): n for k in ("segment", "via") for n in children(t, k)}
    ids = set()
    for v in raw["violations"]:
        if v["severity"] != "error":
            continue
        assert v["type"] in ("clearance", "shorting_items")
        ns = [names[str(first(by[q["uuid"]], "net")[1])] for q in v["items"]]
        assert len(ns) == 2
        source = next(n for n in ns if n in allowed)
        assert source + "_SCHMITT" in ns
        ids.update(q["uuid"] for q in v["items"] if names[str(first(by[q["uuid"]], "net")[1])] == source)
    assert len(ids) == 4
    removed = []
    for uid in sorted(ids):
        n = by[uid]
        assert n[0] == "segment"
        removed.append(sexpr(n))
        t.remove(n)
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for q in SOURCE.iterdir():
        if q.is_file() and (
            q.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or q.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(q, WORK / q.name)
        elif q.suffix == ".pretty":
            shutil.copytree(q, WORK / q.name)
    (WORK / p.name).write_text(sexpr(t) + "\n")
    (WORK / "generated/boundary-clearance.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                raw_native_DRC_sha256=hashlib.sha256(d.read_bytes()).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                additional_raw_boundary_tracks_removed=removed,
                all_force_primitives_and_other_copper_preserved=True,
                native_recheck_pending=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("four exact native-failed ordinary boundary tracks removed; no clearance changed")


if __name__ == "__main__":
    main()
