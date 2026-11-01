"""Explicit same-gate U34 input commutation and actual MASTER surface joins."""

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .. import generate as sg
from . import control
from .receiver_surface_path import connect
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/pg-whole-components-reconnect-work"
ESCAPES = ROOT / "generated/pg-receiving-pad-escapes-work"
WORK = ROOT / "generated/pg-master-local-repair-work"


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == "b279b8dbe0706eee26361bb74152940fd3c86e3f415ec140e9a51d4de6f912be"
    tree = read_sexpr(blob.decode())
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert graph["source_sha256"][str((SOURCE / "rail_disconnect.kicad_pcb").resolve())] == digest
    parts = json.loads((SOURCE / "components.json").read_text())
    before_parts = copy.deepcopy(parts)
    sch = read_sexpr((SOURCE / "rail_disconnect.kicad_sch").read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    codes = {v: k for k, v in names.items()}
    objects = {str(first(n, "uuid")[1]): n for k in ("segment", "via") for n in children(tree, k)}
    master = graph["inventory"]["E28_MASTER_ENABLE"]["components"]
    main_group = max(master, key=len)
    targets = []
    for item in main_group:
        for xy in [item["position_mm"]] + ([item["end_mm"]] if item["kind"] == "PCB_TRACK" else []):
            targets.append(dict(xy=xy, layers=item["layers"], uuid=item["uuid"]))
    routes = []
    rt = Router(tree)
    pad = next(p for p in rt.by_ref["U29"] if p["pin"] == "7")
    result, reason = connect(
        rt, pad, [p for p in targets if pad["layers"][0] in p["layers"]], radius=6, budget=300000
    )
    assert result, reason
    routes.append(dict(ref="U29", pin="7", net=pad["net"], **result))
    original_ids = set(objects)
    escape_tree = read_sexpr((ESCAPES / "rail_disconnect.kicad_pcb").read_text())
    coherent_tree = read_sexpr(
        (ROOT / "generated/c83-pg2-reconnected-work/rail_disconnect.kicad_pcb").read_text()
    )
    coherent_ids = {str(first(n, "uuid")[1]) for k in ("segment", "via") for n in children(coherent_tree, k)}
    receiving_ids = {
        str(first(n, "uuid")[1])
        for n in children(escape_tree, "segment")
        if names[str(first(n, "net")[1])] == "DIG_PG2_SCHMITT"
        and str(first(n, "uuid")[1]) not in coherent_ids
    }
    assert receiving_ids and receiving_ids <= original_ids
    isolated = next(g for g in master if any(p.get("ref") == "U34" and p.get("pin") == "1" for p in g))
    stubs = {p["uuid"] for p in isolated if p["kind"] == "PCB_TRACK"}
    assert len(stubs) == 2
    removed = []
    for uid in sorted(receiving_ids | stubs):
        node = objects[uid]
        assert str(first(node, "layer")[1]) == "B.Cu"
        removed.append(dict(uuid=uid, net=names[str(first(node, "net")[1])], literal=sexpr(node)))
        tree.remove(node)
    fp = next(
        f
        for f in children(tree, "footprint")
        if any(p[1:3] == ["Reference", "U34"] for p in children(f, "property"))
    )
    part = next(p for p in parts if p["ref"] == "U34")
    pin_delta = []
    for number, net in [("1", "DIG_PG2_SCHMITT"), ("2", "E28_MASTER_ENABLE")]:
        pin = next(p for p in part["pins"] if p["number"] == number)
        pin_delta.append(dict(pin=number, old_net=pin["net"], new_net=net))
        pin["net"] = net
        label = next(
            l for l in children(sch, "label") if str(first(l, "uuid")[1]) == sg.uid("labelU34." + number)
        )
        label[1] = net
        pad_node = next(p for p in children(fp, "pad") if str(p[1]) == number)
        first(pad_node, "net")[:] = [a("net"), a(codes[net]), "/" + net]
    rt = Router(tree)
    pad = next(p for p in rt.by_ref["U34"] if p["pin"] == "1")
    result, reason = connect(rt, pad, [dict(xy=(124.775, 40.075), layers=[5])], radius=5, budget=300000)
    assert result, reason
    routes.append(dict(ref="U34", pin="1", net=pad["net"], **result))
    rt = Router(tree)
    pad = next(p for p in rt.by_ref["U34"] if p["pin"] == "2")
    result, reason = connect(
        rt, pad, [p for p in targets if pad["layers"][0] in p["layers"]], radius=6, budget=300000
    )
    assert result, reason
    routes.append(dict(ref="U34", pin="2", net=pad["net"], **result))
    # Primary SCES681F p3: DCU 1A/1B are pins1/2, with output1Y pin7.
    # Exhaust both gate inputs independently; other inputs retain actual safe values.
    cases = []
    for bits in range(4):
        inputs = control.safe_inputs(before_parts)
        inputs.update(E28_MASTER_ENABLE=bits & 1, DIG_PG2_SCHMITT=(bits >> 1) & 1)
        before = control.StaticLogic(before_parts).settle(**inputs)
        after = control.StaticLogic(parts).settle(**inputs)
        assert before["E28_DIG_FOLLOW3"] == after["E28_DIG_FOLLOW3"]
        cases.append(dict(inputs=bits, output=after["E28_DIG_FOLLOW3"]))
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:PGmaster:{digest}:{index}:{sexpr(node)}")
                        )
                    ),
                ]
            )
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for path in SOURCE.iterdir():
        if path.is_file() and (
            path.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or path.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(path, WORK / path.name)
        elif path.suffix == ".pretty":
            shutil.copytree(path, WORK / path.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    (WORK / "rail_disconnect.kicad_sch").write_text(sexpr(sch) + "\n")
    (WORK / "components.json").write_text(json.dumps(parts, indent=2) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        source_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        removed_original_control_objects=removed,
        actual_U34_same_gate_pin_delta=pin_delta,
        truth_cases=cases,
        surface_routes=routes,
        no_new_drills=True,
        all_other_parts_and_force_sense_timing_ground_copper_fixed=True,
        filled_force_return_diagnostics_require_renewal=True,
        native_verified=False,
        physical_qualified=False,
    )
    (WORK / "generated/master-local-repair.json").write_text(json.dumps(report, indent=2) + "\n")
    print("MASTER local candidate written", flush=True)


if __name__ == "__main__":
    main()
