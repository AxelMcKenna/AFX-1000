"""Remove native dangling legacy barrels, preserving explicit repair bundles."""

import argparse
import hashlib
import json
import math

from ...common.sexpr import children, first, read_sexpr, sexpr
from .repair import ROOT, Router


def main(label, remove_unneeded_pad_barrels=False):
    output = ROOT / "generated"
    path = ROOT / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    receipt = json.loads((output / f"native-{label}.json").read_text())
    assert hashlib.sha256(before).hexdigest() == receipt["pcb_sha256"], "Fresh native report required"
    raw = (output / f"drc-{label}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt["drc_sha256"]
    report = json.loads(raw)
    tree = read_sexpr(before.decode())
    rt = Router(tree)
    reported = {
        i["uuid"] for row in report["violations"] if row["type"] == "via_dangling" for i in row["items"]
    }
    protected = set()
    for name in (
        "joint-escape-repair",
        "terminal-stitching",
        "analog-local-timing-repair",
        "digital-local-timing-repair",
        "inverter-local-feedback",
        "u29-joint-escape-repair",
        "force-stem-repair",
        "control-pin-bundles",
        "first-bias-escape-repair",
        "first-dvdt-escape-repair",
        "ic-row-bundle-repair",
    ):
        p = output / f"{name}.json"
        if p.exists():
            protected.update(json.loads(p.read_text()).get("protected_ids", []))
    if remove_unneeded_pad_barrels:
        from .lock_contract import build

        # A native single-layer dangling barrel is electrically unused in the
        # checked snapshot, even when centred in an SMD pad. Preserve actual
        # force, gate/feedback, timing and explicit local repair contracts;
        # remove other unused drills physically and recheck every open/warning.
        protected = {row["uuid"] for row in build(path, recipe_root=ROOT)["locked_copper"]}
    removed = []
    keep = []
    for node in tree:
        drop = False
        if isinstance(node, list) and node and node[0] == "via" and children(node, "uuid"):
            uid = str(first(node, "uuid")[1])
            xy = tuple(float(x) - 100 for x in first(node, "at")[1:3])
            # Actual pad-centre barrels are retained even if a new connection is
            # still missing; this is cleanup of obsolete remote routing stubs.
            at_pad = any(math.dist(xy, p["xy"]) <= 0.15 for p in rt.pads)
            drop = uid in reported and uid not in protected and (remove_unneeded_pad_barrels or not at_pad)
        if drop:
            removed.append(sexpr(node))
        else:
            keep.append(node)
    path.write_text(sexpr(keep) + "\n")
    (output / f"removed-unused-vias-{label}.json").write_text(
        json.dumps(
            dict(
                before_sha256=hashlib.sha256(before).hexdigest(),
                after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                native_drc_sha256=hashlib.sha256(raw).hexdigest(),
                removed_items=removed,
                preserved_repair_bundle_ids=sorted(protected),
                removed_unneeded_pad_barrels=remove_unneeded_pad_barrels,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "Removed",
        len(removed),
        "actual reported dangling legacy barrels; all native findings remain visible.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    main(parser.parse_args().label)
