"""Localize the actual three eFuse timing/current-setting networks in E28."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .relocate import main as move
from .repair import ROOT, Router

TARGETS = {
    "R97": (36.5, 5, 90, "B"),
    "R98": (36.2, 10.25, 0, "B"),
    "R101": (38.3, 12.7, 0, "B"),
    "R102": (41.1, 13, 270, "B"),
    "R117": (36.5, 15.5, 270, "B"),
    "R118": (43.3, 19, 270, "B"),
}


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    move(TARGETS, "analog-local-timing-placement", via_pins={"R118": {"2"}})
    positions = json.loads((ROOT / "generated/analog-local-timing-placement.json").read_text())["placements"]
    tree = read_sexpr(path.read_text())
    nets = {f"E28_ANA_{i}_{suffix}" for i in range(3) for suffix in ("DVDT", "DVDT_CAP", "ILM")}
    numbers = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    keep = []
    for node in tree:
        if (
            isinstance(node, list)
            and node
            and node[0] in ("segment", "via")
            and numbers[str(first(node, "net")[1])] in nets
        ):
            removed.append(sexpr(node))
        else:
            keep.append(node)
    tree = keep
    rt = Router(tree)

    def pad(ref, pin):
        return next(p for p in rt.by_ref[ref] if p["pin"] == str(pin))

    # Preserve the already-native-checked joint pin escapes; discard their old
    # remote runs and obsolete barrels, then attach actual new local terminals.
    plans = json.loads((ROOT / "generated/joint-escape-repair.json").read_text())["plans"]
    retained = []
    for plan in plans:
        if plan["net"] not in nets:
            continue
        assert plan["layer"] == "F.Cu"
        rt.path(plan["net"], 0, plan["points"], 0.2)
        rt.via(plan["net"], plan["points"][-1])
        retained.append(plan)
    for ref in TARGETS:
        p = pad(ref, 1)
        if ref != "R118":
            rt.via(p["net"], p["xy"])
        if ref in ("R98", "R102", "R118"):
            p = pad(ref, 2)
            rt.via(p["net"], p["xy"])
    for ref in ("C39", "C41", "C49"):
        p = pad(ref, 1)
        rt.via(p["net"], (43.8, 11.6) if ref == "C41" else p["xy"])
    p = pad("R118", 1)
    rt.path(p["net"], 5, [p["xy"], (43.65, 17)], 0.2)
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:analogtiming:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/analog-local-timing-repair.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                actual_positions=positions,
                removed_obsolete_items=removed,
                retained_joint_pin_escapes=retained,
                protected_ids=ids,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Localized six analog timing/current-setting resistors and removed", len(removed), "obsolete objects."
    )


if __name__ == "__main__":
    main()
