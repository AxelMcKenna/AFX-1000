"""Separate same-face U102 bypass/delay repair; no canonical promotion.

Native connectivity alone is not LDO stability. This trial authors real local
front-side paths and retains all displaced source objects for reconstruction.
"""

import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

from ...common.placement import footprint_root, placed_footprint
from ...common.sexpr import children, first, read_sexpr, sexpr
from ...output_stage.check_placement import courtyard
from ...power_supply.place import overlap
from . import generate, route
from .route import PowerRouter, coded, named
from .spec import ROOT

POSES = {
    "C106": (26.1, 23.6, 0, "F"),
    "C110": (29.3, 23.4, 270, "F"),
    "R118": (32, 23, 0, "B"),
    "Q103": (25.25, 28.5, 0, "F"),
    "C101": (31.9, 23.5, 90, "F"),
    "C107": (29, 27.1, 90, "F"),
    "C113": (29, 16.5, 180, "F"),
}


def implement(destination, cli):
    source = ROOT / "candidates/u102-consolidated-on-138931"
    destination = destination.resolve()
    assert not destination.exists() and destination != ROOT.resolve()
    canonical_hash = hashlib.sha256((ROOT / "power_p03.kicad_pcb").read_bytes()).hexdigest()
    shutil.copytree(source, destination)
    parts = json.loads((destination / "components.json").read_text())
    by_ref = {c["ref"]: c for c in parts}
    by_ref["C106"].update(
        part="10uF 25V X7R 10% TDK C3225X7R1E106K250AC",
        source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7R1E106K250AC",
        note="Required local U102 output capacitor. Same-face direct OUT/GND loop. Effective>=2.2uF over actual bias/temp/tolerance/aging is a received-part/physical acceptance requirement; typical characterization is not an effective minimum guarantee. Body maximum2.8mm plus0.1mm seat.",
    )
    by_ref["C110"].update(
        part="10nF 25V C0G 5% KEMET C0603C103J3GACTU",
        footprint="Capacitor_SMD:C_0603_1608Metric",
        source="https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf",
        note="Local front-side U102 DELAY capacitor. Table1A103/0603/25V isCG; Table2A0.8+/-0.1mm body. Original timing value/tolerance retained; actual PG startup/delay qualification remains open.",
    )
    by_ref["C102"]["note"] += (
        " Remote VIN_IC input bulk; local same-face bypass is C113, not an assumed opposite-face local capacitor."
    )
    by_ref["C107"]["note"] = (
        "Remote AUX-load bypass near the FAST_OV section; C106 is the required local LDO output capacitor."
    )
    by_ref["C108"]["note"] = "Remote AUX network/load bypass; not credited as required local U102 Cout."
    new = copy.deepcopy(by_ref["C107"])
    new.update(
        ref="C113",
        part="1uF 100V X7S 10% TDK C2012X7S2A105K125AE",
        x=1143.0,
        y=3238.5,
        source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X7S2A105K125AE",
        note="Required same-face VIN_IC/GND local bypass; retains100V rating. Effective>=0.1uF under actual bias/temp/tolerance/aging is a physical requirement, not nominal arithmetic. X7S +/-22%, soft-termination body maximum2.45x1.50x1.50mm plus0.1mm seat.",
    )
    new["pins"] = [dict(p, net="VIN_IC" if p["number"] == "1" else "AGND") for p in new["pins"]]
    parts.append(new)
    by_ref["C113"] = new
    pcb = destination / "power_p03.kicad_pcb"
    original = pcb.read_bytes()
    tree = coded(read_sexpr(original.decode()))
    r = PowerRouter(tree)
    oldpads = [p for ref in POSES if ref in r.by_ref for p in r.by_ref[ref] if p["layers"]]
    used = []
    for f in list(children(tree, "footprint")):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        if ref in POSES:
            tree.remove(f)
            continue
        side = str(first(f, "layer")[1])[0]
        used.append((ref, side, [float(p) - 100 for p in courtyard(f, side + ".CrtYd")]))
    library = footprint_root(str(cli))
    for ref, pose in POSES.items():
        c = by_ref[ref]
        a, b = c["footprint"].split(":")
        fp = placed_footprint(
            dict(c, value=c["part"], mpn=c["part"], nets={p["number"]: p["net"] for p in c["pins"]}),
            pose,
            library / (a + ".pretty") / (b + ".kicad_mod"),
            r.nets,
        )
        box = [float(p) - 100 for p in courtyard(fp, pose[3] + ".CrtYd")]
        assert not [(name, old) for name, side, old in used if side == pose[3] and overlap(box, old, 0.15)], (
            ref
        )
        used.append((ref, pose[3], box))
        tree.append(fp)
    r = PowerRouter(tree)
    pads = oldpads + [p for ref in POSES for p in r.by_ref[ref] if p["layers"]]
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    removed = []
    for obj in list(children(tree, "segment")):
        a, b = [tuple(float(q) - 100 for q in first(obj, k)[1:3]) for k in ("start", "end")]
        dx, dy = b[0] - a[0], b[1] - a[1]

        def distance(p):
            v = (
                max(0, min(1, ((p["xy"][0] - a[0]) * dx + (p["xy"][1] - a[1]) * dy) / (dx * dx + dy * dy)))
                if dx or dy
                else 0
            )
            return math.dist(p["xy"], (a[0] + v * dx, a[1] + v * dy))

        # Native pin identities must survive moving parts. Author all old/new
        # affected pad attachments afresh, on only their actual copper face.
        layer = route.LAYERS.index(str(first(obj, "layer")[1]))
        if any(
            layer in p["layers"]
            and distance(p) < max(p["size"]) / 2 + 0.17 + float(first(obj, "width")[1]) / 2
            for p in pads
        ):
            removed.append(dict(kind="segment", net=nets[str(first(obj, "net")[1])], exact_sexpr=sexpr(obj)))
            tree.remove(obj)
    # Only a via colliding with a newly placed foreign pad may be displaced.
    for obj in list(children(tree, "via")):
        xy = tuple(float(q) - 100 for q in first(obj, "at")[1:3])
        net = nets[str(first(obj, "net")[1])]
        conflicts = []
        for p in pads[len(oldpads) :]:
            if p["net"] == net:
                continue
            dd = math.hypot(
                max(0, abs(xy[0] - p["xy"][0]) - p["size"][0] / 2),
                max(0, abs(xy[1] - p["xy"][1]) - p["size"][1] / 2),
            )
            if dd < float(first(obj, "size")[1]) / 2 + 0.16:
                conflicts.append((p["ref"], p["pin"]))
        if conflicts:
            assert not (25.5 <= xy[0] <= 27 and 19.25 <= xy[1] <= 20.75), (
                "Direct U102 EP field cannot be removed"
            )
            removed.append(dict(kind="via", net=net, exact_sexpr=sexpr(obj), new_pad_conflicts=conflicts))
            tree.remove(obj)
    pcb.write_text(sexpr(named(tree)) + "\n")
    # The new native schematic includes the actual added bypass, exact MPNs and
    # physical packages. No canonical generator/library path is written.
    generate.ROOT = destination
    generate.components = lambda: parts
    generate.footprints.write = lambda: None
    generate.schematic(cli)
    (destination / "generated/aux-cell-layout.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(original).hexdigest(),
                poses_local_mm=POSES,
                displaced_source_objects=removed,
                required_same_face_nodes={
                    "C106": ["V2V5_AUX", "AGND"],
                    "C113": ["VIN_IC", "AGND"],
                    "C110": ["AUX_START_DELAY", "AGND"],
                },
                C102_role="Remote100Vinputbulk",
                C107_C108_role="Remote AUX load/network decoupling, not required local Cout",
                native_routing_and_filled_thermal_ground_fit_replay_required=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    assert hashlib.sha256((ROOT / "power_p03.kicad_pcb").read_bytes()).hexdigest() == canonical_hash
    print("Actual same-face AUX cell placed; native loop reconstruction required", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--kicad-cli", type=Path, required=True)
    q = p.parse_args()
    implement(q.destination, q.kicad_cli)
