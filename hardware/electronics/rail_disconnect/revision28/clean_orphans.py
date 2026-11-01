"""Remove the actual native-identified padless copper objects, without exemptions."""

import hashlib
import json

from ...common.sexpr import children, first, read_sexpr, sexpr
from .manufacturer import ROOT


def main():
    rows = json.loads((ROOT / "generated/orphan-components.json").read_text())
    ids = {i["uuid"] for row in rows for i in row["items"]}
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    kept = []
    removed = []
    for n in tree:
        if (
            isinstance(n, list)
            and n
            and n[0] in ("segment", "via")
            and children(n, "uuid")
            and str(first(n, "uuid")[1]) in ids
        ):
            removed.append(sexpr(n))
        else:
            kept.append(n)
    path.write_text(sexpr(kept) + "\n")
    (ROOT / "generated/removed-native-orphans.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                removed_items=removed,
                native_evidence=rows,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Removed", len(removed), "actual padless tracks/vias")


if __name__ == "__main__":
    main()
