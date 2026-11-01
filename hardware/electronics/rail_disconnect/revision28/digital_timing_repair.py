"""Local native DIGITAL timing networks, preserving their exact values and pins."""

import hashlib
import json
import uuid

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .relocate import main as move
from .repair import ROOT, Router

TARGETS = {
    "C43": (121.5, 4.5, 90, "B"),
    "C45": (121.5, 9.5, 90, "B"),
    "R106": (133.15, 6.25, 90, "B"),
    "R105": (135.2, 4.5, 90, "B"),
    "R110": (132.9, 10.5, 90, "B"),
    "R109": (141, 9, 90, "B"),
    "R114": (131, 24, 90, "B"),
    "R113": (130.25, 27.5, 90, "B"),
    "R122": (135, 22.5, 0, "B"),
    "R121": (144.95, 14.5, 90, "B"),
}
VIA_PINS = {"R106": set()}


def main():
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    move(TARGETS, "digital-local-timing-placement", via_pins=VIA_PINS)
    positions = json.loads((ROOT / "generated/digital-local-timing-placement.json").read_text())["placements"]
    tree = read_sexpr(path.read_text())
    nets = {f"E28_DIG_{i}_{suffix}" for i in range(4) for suffix in ("DVDT", "DVDT_CAP", "ILM")}
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

    plans = json.loads((ROOT / "generated/joint-escape-repair.json").read_text())["plans"]
    retained = []
    for plan in plans:
        if plan["net"] not in nets:
            continue
        assert plan["layer"] == "F.Cu"
        if plan["ref"] == "U15" and str(plan["pin"]) == "7":
            plan = dict(plan, points=[plan["points"][0], (132.6, 6.175), (133.15, 6.725), (133.5, 6.95)])
        elif plan["ref"] == "U15" and str(plan["pin"]) == "9":
            plan = dict(plan, points=[plan["points"][0], (132.5, 5.275), (132.5, 3.5), (133.5, 3.5)])
        rt.path(plan["net"], 0, plan["points"], 0.2)
        rt.via(plan["net"], plan["points"][-1])
        retained.append(plan)
    for ref in TARGETS:
        if not ref.startswith("R"):
            continue
        for pin in (1, 2):
            p = pad(ref, pin)
            if ref in VIA_PINS and str(pin) not in VIA_PINS[ref]:
                continue
            rt.via(p["net"], p["xy"])
    for ref in ("C43", "C45", "C47", "C51"):
        p = pad(ref, 1)
        rt.via(p["net"], p["xy"])
    # These lands use the already present, inspected joint barrels instead of
    # drilling a second overlapping hole. The resistor positions are explicit.
    assert positions["R106"] == list(TARGETS["R106"]), positions["R106"]
    p = pad("R106", 1)
    rt.path(p["net"], 5, [p["xy"], (133.5, 6.95)], 0.2)
    p = pad("R106", 2)
    rt.path(p["net"], 5, [p["xy"], (133.15, 4.5)], 0.2)
    rt.via(p["net"], (133.15, 4.5))
    ids = []
    for i, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:digitaltiming:{i}:{sexpr(node)}"))
            node.append([a("uuid"), a(uid)])
            ids.append(uid)
    path.write_text(sexpr(tree) + "\n")
    (ROOT / "generated/digital-local-timing-repair.json").write_text(
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
        "Localized eight DIGITAL setting resistors and two timing capacitors; removed",
        len(removed),
        "obsolete objects.",
    )


if __name__ == "__main__":
    main()
