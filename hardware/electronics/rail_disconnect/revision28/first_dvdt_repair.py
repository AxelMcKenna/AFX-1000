"""Install the actual first DIGITAL dV/dt escape beside its ground channel."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import ROOT, Router


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    keep = []
    removed = []
    for n in tree:
        if (
            isinstance(n, list)
            and n
            and n[0] in ("segment", "via")
            and names[str(first(n, "net")[1])] == "E28_DIG_0_DVDT"
        ):
            removed.append(sexpr(n))
        else:
            keep.append(n)
    tree = keep
    rt = Router(tree)
    p = next(p for p in rt.by_ref["U15"] if p["pin"] == "7")
    q = next(p for p in rt.by_ref["R106"] if p["pin"] == "1")
    assert p["net"] == q["net"] == "E28_DIG_0_DVDT"
    points = [p["xy"], (132.6, 6.175), (133.15, 6.725), (133.5, 6.95)]
    rt.path(p["net"], 0, points, 0.2)
    rt.via(p["net"], points[-1])
    rt.path(p["net"], 5, [q["xy"], points[-1]], 0.2)
    ids = []
    for i, n in enumerate(tree):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            u = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:DVdt0:{i}:{sexpr(n)}"))
            n.append([a("uuid"), a(u)])
            ids.append(u)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/first-dvdt-escape-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                actual_front_path=points,
                actual_back_path=[q["xy"], points[-1]],
                protected_ids=ids,
                removed_items=removed,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
