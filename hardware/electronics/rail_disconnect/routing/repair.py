"""Attempt unresolved native connections at a finer grid; never certify generation."""

import json
import re
from pathlib import Path

from ...common.sexpr import children, read_sexpr, sexpr
from . import router as aid

ROOT = Path(__file__).resolve().parent


def main():
    out = ROOT / "generated"
    native = json.loads((out / "drc.json").read_text())
    assert not native["violations"] and not native["schematic_parity"], (
        "Repair requires a clean native starting candidate"
    )
    (out / "verification.json").unlink(missing_ok=True)
    aid.STEP = 0.125
    tree = read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text())
    r = aid.Router(tree)
    r.max_search_nodes = 60000
    r.search_bias = 1.8
    r.load_existing_copper()
    failed = []
    for i, item in enumerate(native["unconnected_items"], 1):
        nodes = []
        net = None
        for endpoint in item["items"]:
            text = endpoint["description"]
            name = re.search(r"\[/(.*?)\]", text).group(1)
            assert net in (None, name)
            net = name
            xy = (endpoint["pos"]["x"] - 100, endpoint["pos"]["y"] - 100)
            layers = (
                tuple(range(6))
                if "Via " in text or "on F.Cu - B.Cu" in text
                else tuple(j for j, layer in enumerate(aid.LAYERS) if layer in text)
            )
            if re.search(r"\b[Pp]ad ", text):
                ref = re.search(r" of (\w+)(?: on |$)", text).group(1)
                match = min(
                    (p for p in r.by_ref[ref] if p["net"] == net),
                    key=lambda p: (p["xy"][0] - xy[0]) ** 2 + (p["xy"][1] - xy[1]) ** 2,
                )
                layers = match["layers"]
            assert layers, (text, layers)
            nodes.append(dict(net=net, xy=xy, layers=layers))
        width = (
            1.0
            if net in ("5V_DIG", "5V_DIG_SRC")
            else 0.5
            if net
            in (
                "P19",
                "P19_SRC",
                "N19",
                "N19_SRC",
                "P12",
                "P12_SRC",
                "N12",
                "N12_SRC",
                "V5_REG",
                "V5_REG_SRC",
                "AGND",
            )
            else 0.25
        )
        success = r.connect(nodes[0], nodes[1], width)
        if not success:
            failed.append(item)
        print(f"E25 repair {i}/{len(native['unconnected_items'])} {net}: {success}", flush=True)
    (ROOT / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    packet = json.loads((out / "routing-inputs.json").read_text())
    packet["routed_segments"] = len(children(tree, "segment"))
    packet["through_vias"] = len(children(tree, "via"))
    packet["native_repair_attempts"] = dict(
        starting_native_opens=len(native["unconnected_items"]),
        grid_mm=aid.STEP,
        failed_attempts=len(failed),
        routes=r.routes,
    )
    packet["pcb_routed"] = False
    (out / "routing-inputs.json").write_text(json.dumps(packet, indent=2) + "\n")
    print("Native checks required:", packet["routed_segments"], "segments", packet["through_vias"], "vias")


if __name__ == "__main__":
    main()
