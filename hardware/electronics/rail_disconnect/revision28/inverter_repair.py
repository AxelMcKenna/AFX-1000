"""Localize actual high-impedance negative-rail inverter feedback in E28."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, read_sexpr, sexpr
from .relocate import main as move
from .repair import ROOT, Router

TARGETS = {
    "R50": (35, 24.5, 0, "B"),
    "R51": (38.5, 25.5, 270, "B"),
    "R52": (35, 27.5, 0, "B"),
    "R53": (49, 29.5, 0, "B"),
    "R54": (48.5, 25.5, 270, "B"),
    "R55": (52.5, 23.5, 0, "B"),
}


def main(targets=None):
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    prior = ROOT / "generated/inverter-local-feedback.json"
    if prior.exists():
        old_ids = set(json.loads(prior.read_text())["protected_ids"])
        old_tree = read_sexpr(before.decode())
        old_tree = [
            n
            for n in old_tree
            if not (
                isinstance(n, list)
                and n
                and n[0] in ("segment", "via")
                and children(n, "uuid")
                and str(children(n, "uuid")[0][1]) in old_ids
            )
        ]
        path.write_text(sexpr(old_tree) + "\n")
    move(TARGETS if targets is None else targets, "inverter-local-placement")
    tree = read_sexpr(path.read_text())
    rt = Router(tree)
    plans = []

    def pad(ref, pin):
        return next(p for p in rt.by_ref[ref] if p["pin"] == str(pin))

    def join(a_ref, a_pin, b_ref, b_pin, layer):
        p, q = pad(a_ref, a_pin), pad(b_ref, b_pin)
        assert p["net"] == q["net"]
        rt.path(p["net"], layer, [p["xy"], q["xy"]], 0.2)
        plans.append(
            dict(net=p["net"], ends=[(a_ref, a_pin), (b_ref, b_pin)], layer=layer, points=[p["xy"], q["xy"]])
        )

    # Feedback lands opposite the actual op-amp pin rows; these are complete
    # native traces and actual capped barrels, not logical connectivity waivers.
    for op, ref, res in ((1, "R51", 1), (2, "R51", 2), (6, "R54", 2), (7, "R54", 1)):
        join("U8", op, ref, res, 0)
    for r1, p1, r2, p2 in (
        ("R50", 2, "R51", 2),
        ("R52", 1, "R51", 1),
        ("R53", 2, "R54", 2),
        ("R55", 1, "R54", 1),
    ):
        join(r1, p1, r2, p2, 3 if r1 in ("R52", "R55") else 5)
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:local-inverter:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/inverter-local-feedback.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                feedback_connections=plans,
                protected_ids=ids,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Localized both negative-rail inverter feedback loops with8nativeconnections.")



def seal_networks():
    """Remove obsolete remote signal copper after all three actual pads moved.

    These four small-signal networks have exactly three physical terminals each.
    Their complete required copper is the explicit eight local connections plus
    six actual layer-changing barrels. Remote legacy stubs/loops serve no pad.
    """
    from ...common.sexpr import first

    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    expected = {
        "N19_SUM": {("U8", "2"), ("R51", "2"), ("R50", "2")},
        "N12_SUM": {("U8", "6"), ("R54", "2"), ("R53", "2")},
        "N19_INV": {("U8", "1"), ("R51", "1"), ("R52", "1")},
        "N12_INV": {("U8", "7"), ("R54", "1"), ("R55", "1")},
    }
    for net, refs in expected.items():
        assert {(p["ref"], p["pin"]) for p in rt.pads if p["net"] == net} == refs
    receipt = json.loads((ROOT / "generated/inverter-local-feedback.json").read_text())
    keep_ids = set(receipt["protected_ids"])
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    kept = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] in ("segment", "via"):
            net = names[str(first(node, "net")[1])]
            if net in expected:
                drop = node[0] == "via" or str(first(node, "uuid")[1]) not in keep_ids
        if drop:
            removed.append(sexpr(node))
        else:
            kept.append(node)
    tree = kept
    rt = Router(tree)
    for ref, pin in (("R51", "1"), ("R51", "2"), ("R54", "1"), ("R54", "2"), ("R52", "1"), ("R55", "1")):
        p = next(p for p in rt.by_ref[ref] if p["pin"] == pin)
        rt.via(p["net"], p["xy"])
    new_ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:sealed-inverter:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            new_ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/inverter-obsolete-copper-removal.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                actual_pad_contract={k: sorted(v) for k, v in expected.items()},
                removed_items=removed,
                protected_ids=sorted(keep_ids | set(new_ids)),
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Removed",
        len(removed),
        "obsolete remote inverter copper objects; four actual3-terminal networks retained.",
    )


if __name__ == "__main__":
    main()
    seal_networks()
