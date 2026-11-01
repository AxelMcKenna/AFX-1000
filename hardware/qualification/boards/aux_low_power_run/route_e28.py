"""Join only AX03 receiver terminals to actual native copper components.

Existing footprints, copper and rule areas are immutable in this pass. Filled
power copper is reserved during search; native refill/DRC remain authoritative.
"""

import hashlib
import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision28.band_router import BandRouter
from hardware.electronics.rail_disconnect.revision28.component_routes import connect_components

REPO = Path(__file__).resolve().parents[4]
WORK = REPO / "hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    source = WORK / "rail_disconnect.kicad_pcb"
    inputs = WORK / "generated/routing-inputs"
    out = WORK / "generated/receiver-routes"
    out.mkdir(exist_ok=False)
    original = source.read_bytes()
    digest = sha(source)
    inventory = json.loads((inputs / "components.json").read_text())
    assert inventory["source_sha256"][str(source)] == digest
    filled = WORK / "generated/native-placement/rail_disconnect.kicad_pcb"
    pads = json.loads((inputs / "pads.json").read_text())
    assert pads["source_pcb_sha256"] == sha(filled)
    tree = read_sexpr(original.decode())
    original_count = len(tree)
    existing = sexpr(tree)
    router = BandRouter(tree, read_sexpr(filled.read_text()), pads, step=0.05)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    editable = {
        str(first(n, "uuid")[1]): names[str(first(n, "net")[1])]
        for kind in ("segment", "via") for n in children(tree, kind)
    }

    def anchors(group, net):
        points = []
        for obj in group:
            if obj["kind"] != "PAD" and editable.get(obj["uuid"]) != net:
                continue
            for xy in [obj["position_mm"]] + ([obj["end_mm"]] if obj["kind"] == "PCB_TRACK" else []):
                points.append(dict(xy=xy, layers=obj["layers"], uuid=obj["uuid"],
                                   kind=obj["kind"], ref=obj.get("ref")))
        return points

    results = []
    for net in ("RUN_BUFFERED", "POWER_RUN", "V2V5_AUX", "AGND"):
        row = inventory["inventory"][net]
        groups = row["components"]
        new = [g for g in groups if any(p.get("ref") in ("U43", "C86") for p in g)]
        old = [g for g in groups if g not in new]
        # The native largest pad-connected component is the existing rail.
        # RUN_BUFFERED has the old U28 input and the new U43 output only.
        assert old, (net, "No existing destination")
        target = max(old, key=lambda g: sum(p["kind"] == "PAD" for p in g))
        joined = anchors(target, net)
        for group in new:
            router.cached = {}
            addition = anchors(group, net)
            result = connect_components(router, dict(net=net, components=[addition, joined]),
                                        width=0.2, budget=750000)
            results.append(dict(net=net, **result))
            print(net, result.get("connected"), result.get("visited"), result.get("reason"), flush=True)
            if result.get("connected"):
                joined += addition
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL,
                        f"rmx:AX03:receiver:{digest}:{index}:{sexpr(node)}")))])
    assert sexpr(tree[:original_count]) == existing
    pcb = out / source.name
    pcb.write_text(sexpr(tree) + "\n")
    report = dict(source_pcb_sha256=digest, candidate_pcb_sha256=sha(pcb),
                  recipe_sha256=sha(Path(__file__)), attempts=results, routes=router.routes,
                  native_components_sha256=sha(inputs / "components.json"),
                  native_pads_sha256=sha(inputs / "pads.json"),
                  no_existing_footprints_or_copper_or_rules_changed=True,
                  filled_power_copper_reserved=True, native_checks_pending=True,
                  fabrication_released=False)
    (out / "routes.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original


if __name__ == "__main__":
    run()
