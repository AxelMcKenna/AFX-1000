"""Real local wiring for the unchanged U19 supervisor circuit."""

import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .band_local_escape import escape
from .band_router import BandRouter
from .component_routes import connect_components
from .filled_surface_path import path_between
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u28-aux-supervisor-placement-work"
FORCE = ROOT / "generated/u28-run-pulldown-routed-work/generated/filled-run-pulldown-routed1.kicad_pcb"
WORK = ROOT / "generated/u28-aux-supervisor-local-work"
LOCAL = {"U19", "C58", "C60", "R135", "R137", "R138", "R139"}
INTERNAL = {"E28_AUX_DIV", "E28_AUX_SENSE", "E28_AUX_CT"}


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    parts = json.loads((SOURCE / "components.json").read_text())
    nets = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    for net in INTERNAL:
        users = {(p["ref"], str(q["number"])) for p in parts for q in p["pins"] if q["net"] == net}
        assert users and all(ref in LOCAL for ref, pin in users)
    removed = [
        n
        for kind in ("segment", "via")
        for n in children(tree, kind)
        if nets[str(first(n, "net")[1])] in INTERNAL
    ]
    locks = {
        r["uuid"]
        for r in json.loads((ROOT / "generated/leaf-prune-source-lock-contract.json").read_text())[
            "locked_copper"
        ]
    }
    assert not {str(first(n, "uuid")[1]) for n in removed} & locks
    tree[:] = [n for n in tree if n not in removed]
    router = Router(tree)

    def pad(ref, pin):
        found = [p for p in router.by_ref[ref] if p["pin"] == str(pin)]
        assert len(found) == 1
        return found[0]

    def xy(ref, pin):
        return pad(ref, pin)["xy"]

    local_wires = []

    def wire(net, points):
        router.path(net, 5, points, 0.2)
        local_wires.append(dict(net=net, points_mm=points))

    wire("V2V5_AUX", [xy("U19", 4), xy("U19", 3)])
    wire("V2V5_AUX", [xy("C58", 1), (68.2, 48.45), xy("U19", 3)])
    wire("V2V5_AUX", [xy("C58", 1), (66.5, 49.4), (63.5, 49.4), xy("R137", 1)])
    wire("V2V5_AUX", [xy("C58", 1), (67.7, 49.4), (67.7, 51.3), (70.7, 51.3), (70.7, 52.2125), xy("R135", 2)])
    wire("E28_AUX_CT", [xy("U19", 5), (69.5, 46.0), (72.05, 46.0), xy("C60", 1)])
    wire("E28_AUX_DIV", [xy("R137", 2), xy("R138", 1)])
    wire("E28_AUX_SENSE", [xy("U19", 1), (70.8, 48.75), (72, 48.75), xy("R139", 1)])
    wire("E28_AUX_SENSE", [xy("R138", 2), (67.4625, 53.35), (71.5, 53.35), (71.5, 50.3875), xy("R139", 1)])
    for row in local_wires:
        assert all(
            legal_line(router, row["net"], 5, p, q, 0.2)
            for p, q in zip(row["points_mm"], row["points_mm"][1:])
            if math.dist(p, q) > 1e-8
        ), row
    escaped = {}
    for ref, pin in (("U19", 6), ("R135", 1), ("C58", 1), ("U19", 2), ("C58", 2), ("C60", 2), ("R139", 2)):
        result, reason = escape(router, pad(ref, pin), maxdistance=2, step=0.025)
        assert result is not None, (ref, pin, reason)
        escaped[f"{ref}.{pin}"] = result
    zones = []
    for layer in ("In1.Cu", "In4.Cu"):
        candidate = next(
            z
            for z in children(tree, "zone")
            if children(z, "net_name")
            and str(first(z, "net_name")[1]).lstrip("/") == "AGND"
            and first(z, "layer")[1] == layer
        )
        z = copy.deepcopy(candidate)
        z[:] = [
            n for n in z if not (isinstance(n, list) and n and n[0] in ("filled_polygon", "fill_segments"))
        ]
        first(z, "uuid")[1] = a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:auxGround:{digest}:{layer}")))
        first(z, "priority")[1] = a("0")
        first(z, "min_thickness")[1] = a(".2")
        first(z, "polygon")[:] = read_sexpr(
            "(polygon (pts (xy 162 144) (xy 175.75 144) (xy 175.75 153.875) (xy 162 153.875)))"
        )
        tree.append(z)
        zones.append(sexpr(z))
    filled = read_sexpr(FORCE.read_text())
    native_pads = json.loads((SOURCE / "generated/native-pads.json").read_text())
    assert native_pads["source_pcb_sha256"] == digest
    anchors_path = SOURCE / "generated/external-native-anchors.json"
    anchors = json.loads(anchors_path.read_text())
    assert anchors["source_pcb_sha256"] == digest
    router = BandRouter(tree, filled, native_pads, step=0.1)
    connections = []

    def join(net, one, options):
        all_options = options
        options = sorted(options, key=lambda p: math.dist(one, p))[:5]
        attempts = []
        for two in options:
            for layer in (1, 4, 5):
                try:
                    points, visited = path_between(
                        router, one, two, layer, filled, native_pads, margin=4, step=0.025, net=net
                    )
                except AssertionError as error:
                    attempts.append(dict(target_mm=two, layer=layer, failure=str(error)))
                    continue
                router.path(net, layer, points, 0.2)
                attempts.append(dict(target_mm=two, layer=layer, points_mm=points, visited=visited))
                connections.append(dict(net=net, source_mm=one, attempts=attempts))
                return
        # The single-layer search cannot cross retained control routes. Search
        # all actual connected source barrels jointly with physical layer
        # changes; the force guard still forbids holes through force copper.
        router.cached = {}
        result = connect_components(
            router,
            dict(
                net=net,
                components=[
                    [dict(xy=one, layers=list(range(6)), kind="PCB_VIA")],
                    [dict(xy=p, layers=list(range(6)), kind="PCB_VIA") for p in all_options],
                ],
            ),
            width=0.2,
            budget=500000,
        )
        attempts.append(dict(joint_multilayer_search=result))
        assert result["connected"], (net, one, attempts)
        connections.append(dict(net=net, source_mm=one, attempts=attempts))

    join("E28_AUX_RESET_N", escaped["U19.6"]["via"], [escaped["R135.1"]["via"]])
    join(
        "V2V5_AUX",
        escaped["C58.1"]["via"],
        [r["xy_mm"] for r in anchors["nets"]["V2V5_AUX"]["connected_actual_source_vias"]],
    )
    join(
        "E28_AUX_RESET_N",
        escaped["U19.6"]["via"],
        [r["xy_mm"] for r in anchors["nets"]["E28_AUX_RESET_N"]["connected_actual_source_vias"]],
    )
    added = []
    for index, node in enumerate(tree):
        if isinstance(node, list) and node and node[0] in ("segment", "via") and not children(node, "uuid"):
            node.append(
                [
                    a("uuid"),
                    a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:auxCell:{digest}:{index}:{sexpr(node)}"))),
                ]
            )
            added.append(sexpr(node))
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / source.name).write_text(sexpr(tree) + "\n")
    report = dict(
        source_pcb_sha256=digest,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        force_obstacles_source_sha256=hashlib.sha256(FORCE.read_bytes()).hexdigest(),
        actual_external_anchor_sha256=hashlib.sha256(anchors_path.read_bytes()).hexdigest(),
        removed_unlocked_internal_copper=[sexpr(n) for n in removed],
        local_B_wires=local_wires,
        actual_barrel_escapes=escaped,
        new_ground_zones=zones,
        actual_external_connections=connections,
        actual_added_copper=added,
        all_other_copper_and_parts_preserved=True,
        circuit_values_and_pin_nets_unchanged=True,
        old_AUX_DIV_SENSE_CT_only_relocated_as_complete_internal_networks=True,
        all_native_and_PDN_required=True,
        qualified=False,
    )
    (WORK / "generated/local-supervisor-cell.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original
    print("Local supervisor cell wired; fresh native checks required", flush=True)


if __name__ == "__main__":
    main()
