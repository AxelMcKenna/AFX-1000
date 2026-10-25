"""Remove only native-reported one-face redundant vias; retain every real pad/net."""

import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def main():
    out = ROOT / "generated"
    native = json.loads((out / "drc.json").read_text())
    pcb = ROOT / "rail_disconnect.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    points = {
        tuple(round(float(item["pos"][axis]), 6) for axis in ("x", "y"))
        for v in native["violations"]
        if v["type"] == "via_dangling"
        for item in v["items"]
        if item["description"].startswith("Via ")
    }
    removed = []
    for via in list(children(tree, "via")):
        xy = tuple(round(float(v), 6) for v in first(via, "at")[1:3])
        if xy in points:
            tree.remove(via)
            removed.append(dict(position_mm=xy, net=str(first(via, "net")[-1])))
    assert len(removed) == len(points), (len(removed), len(points))
    pcb.write_text(sexpr(tree) + "\n")
    (out / "verification.json").unlink(missing_ok=True)
    record = json.loads((out / "routing-inputs.json").read_text())
    record["vias"] = len(children(tree, "via"))
    record["native_one_face_vias_removed"] = removed
    record["ports_are_initial_reservations_not_a_claim_every_via_is_retained"] = True
    record["build_ready"] = False
    (out / "routing-inputs.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        "Removed",
        len(removed),
        "native-reported redundant one-face vias; no pad/net/component changes; fresh native check required",
    )


if __name__ == "__main__":
    main()
