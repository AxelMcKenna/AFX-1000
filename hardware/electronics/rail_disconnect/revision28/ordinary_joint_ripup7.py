"""Bounded joint multilayer ripup for one ALL_RAILS_ALLOW connection.

Only explicitly listed ordinary control traces and at most five associated
barrels may move. Pads, quiet references, force fields, ground references and
local latch feedback links remain hard obstacles. Every affected net must be
reconnected before acceptance.
"""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ..routing.check import point_segment, segment_distance
from .band_router import BandRouter
from .component_routes import connect_components

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u21-band-reconnect1-work"
WORK = ROOT / "generated/u21-ordinary-joint7-work"
ORDINARY = {
    "OK_ALL_OV",
    "OK_ANALOG",
    "OK_AUXILIARY",
    "E28_ARMED",
    "E28_FAULT",
    "E28_FAULT_SET",
    "E28_FAULT_ANY",
    "E28_MASTER_ENABLE",
    "E28_NORMAL_PRE",
    "E28_NORMAL_OK",
    "E28_NOT_NORMAL_OK",
    "E28_OUT_ARM_BAR",
    "E28_OUT_ARMED",
    "E28_OUT_READY",
    "E28_OUT_VALID_ACTIVE",
    "E28_NOT_OUT_READY",
    "E28_OUTPUT_READY",
    "E28_RESET",
    "E28_RESET_OUT",
    "E28_RUN_AND_SOURCE",
    "E28_NOT_RUN",
    "E28_NOT_AUX",
    "E28_RUN_LOGIC",
    "E28_NOT_FAULT",
    "E28_SOURCE_READY_LOGIC",
    "E28_SOURCE_READY",
    "E28_NOT_SOURCE_READY",
    "E28_NOT_ARMED",
    "E28_OUT_UV_FAULT",
    "E28_TIMEOUT_FAULT",
    "E28_REF_HEALTH_FAULT",
    "E28_USER_AUX",
    "E28_SAFE_STAGE",
    "E28_SAFE_REQUEST",
    "E28_AUX_VALID",
    "P03_SOURCES_READY",
    "POWER_RUN",
}
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def main():
    assert not WORK.exists()
    source = SOURCE / "rail_disconnect.kicad_pcb"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    tree = read_sexpr(original.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    filled_path = SOURCE / "generated/filled-u21-reconnect1.kicad_pcb"
    filled = read_sexpr(filled_path.read_text())
    pads_path = SOURCE / "generated/native-pads.json"
    pads = json.loads(pads_path.read_text())
    assert pads["source_pcb_sha256"] == hashlib.sha256(filled_path.read_bytes()).hexdigest()
    graph_path = SOURCE / "generated/residual-components.json"
    graph = json.loads(graph_path.read_text())
    assert [h for p, h in graph["source_sha256"].items() if Path(p).resolve() == source.resolve()] == [digest]
    row = graph["inventory"]["ALL_RAILS_ALLOW"]
    group = next(g for g in row["components"] if any(p.get("ref") == "U21" for p in g))
    start = next(p["position_mm"] for p in group if p["kind"] == "PCB_VIA")
    others = [g for g in row["components"] if g is not group]
    goals = [p["position_mm"] for g in others for p in g if p["kind"] == "PCB_VIA"]
    goals = sorted(goals, key=lambda p: math.dist(p, start))[:3]
    local_path = ROOT / "generated/u21-band-fanout-work/generated/local-escapes.json"
    local_data = json.loads(local_path.read_text())
    protected = []
    for net, points in local_data["local_crosscoupled_wires"]:
        protected.extend((net, p, q) for p, q in zip(points, points[1:]))

    def protected_local(g):
        if g["kind"] != "line" or g["layers"] != (5,):
            return False
        return any(
            g["net"] == net
            and (
                (math.dist(g["start"], p) < 1e-6 and math.dist(g["end"], q) < 1e-6)
                or (math.dist(g["start"], q) < 1e-6 and math.dist(g["end"], p) < 1e-6)
            )
            for net, p, q in protected
        )

    parts = json.loads((SOURCE / "components.json").read_text())
    monitor_contract = {}
    for net in ("OK_ALL_OV", "OK_ANALOG", "OK_AUXILIARY"):
        users = [(p, q) for p in parts for q in p["pins"] if q["net"] == net]
        assert users and all(
            p["part"] == "SN74LVC08APWR" and q["kind"] in ("input", "output") for p, q in users
        )
        monitor_contract[net] = [(p["ref"], str(q["number"]), q["kind"]) for p, q in users]
    candidates = []
    for kind in ("segment", "via"):
        for n in children(tree, kind):
            net = names[str(first(n, "net")[1])]
            if net not in ORDINARY:
                continue
            g = dict(
                kind="line" if kind == "segment" else "via", net=net, uuid=str(first(n, "uuid")[1]), node=n
            )
            if kind == "segment":
                g.update(
                    layers=(LAYERS.index(str(first(n, "layer")[1])),),
                    start=[float(v) - 100 for v in first(n, "start")[1:]],
                    end=[float(v) - 100 for v in first(n, "end")[1:]],
                    width=float(first(n, "width")[1]),
                )
            else:
                g.update(
                    layers=tuple(range(6)),
                    xy=[float(v) - 100 for v in first(n, "at")[1:]],
                    radius=float(first(n, "size")[1]) / 2,
                )
            if not protected_local(g):
                candidates.append(g)
    router = BandRouter(tree, filled, pads, step=0.05)
    router.geometry = [
        g
        for g in router.geometry
        if not (g["kind"] in ("line", "via") and g["net"] in ORDINARY and not protected_local(g))
    ]
    editable = {
        str(first(n, "uuid")[1]): names[str(first(n, "net")[1])]
        for k in ("segment", "via")
        for n in children(tree, k)
    }
    groups = []
    for group in row["components"]:
        points = []
        for p in group:
            if p["kind"] != "PAD" and editable.get(p["uuid"]) != "ALL_RAILS_ALLOW":
                continue
            for xy in [p["position_mm"]] + ([p["end_mm"]] if p["kind"] == "PCB_TRACK" else []):
                points.append(
                    dict(xy=xy, layers=p["layers"], uuid=p["uuid"], kind=p["kind"], ref=p.get("ref"))
                )
        groups.append(points)
    assert len(groups) == 2 and all(groups)
    result = connect_components(
        router, dict(net="ALL_RAILS_ALLOW", components=groups), width=0.2, budget=1500000
    )
    print("Joint", result, flush=True)
    added = [n for k in ("segment", "via") for n in children(tree, k) if not children(n, "uuid")]
    ripped = []
    for old in candidates:
        hit = False
        for n in added:
            if n[0] == "segment":
                layer = LAYERS.index(str(first(n, "layer")[1]))
                if layer not in old["layers"]:
                    continue
                one = [float(v) - 100 for v in first(n, "start")[1:]]
                two = [float(v) - 100 for v in first(n, "end")[1:]]
                w = float(first(n, "width")[1])
                if old["kind"] == "line":
                    hit |= (
                        segment_distance(one, two, old["start"], old["end"])
                        < 0.2 + w / 2 + old["width"] / 2 + 1e-6
                    )
                else:
                    hit |= point_segment(old["xy"], one, two) < 0.2 + w / 2 + old["radius"] + 1e-6
            else:
                xy = [float(v) - 100 for v in first(n, "at")[1:]]
                radius = float(first(n, "size")[1]) / 2
                if old["kind"] == "line":
                    hit |= (
                        point_segment(xy, old["start"], old["end"]) < 0.2 + radius + old["width"] / 2 + 1e-6
                    )
                else:
                    hit |= math.dist(xy, old["xy"]) < 0.2 + radius + old["radius"] + 1e-6
        if hit:
            ripped.append(old)
    affected = sorted({p["net"] for p in ripped})
    bounded = len(affected) <= 7 and len(ripped) <= 50 and sum(p["kind"] == "via" for p in ripped) <= 5
    assert affected == [
        "E28_FAULT",
        "E28_MASTER_ENABLE",
        "E28_RUN_AND_SOURCE",
        "OK_ALL_OV",
        "OK_ANALOG",
        "OK_AUXILIARY",
        "POWER_RUN",
    ]
    report = dict(
        source_pcb_sha256=digest,
        filled_pcb_sha256=hashlib.sha256(filled_path.read_bytes()).hexdigest(),
        actual_graph_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        pad_geometry_sha256=hashlib.sha256(pads_path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        explicit_ordinary_allowlist=sorted(ORDINARY),
        actual_monitor_gate_contract=monitor_contract,
        retained_local_latch_links=protected,
        local_latch_geometry_source_sha256=hashlib.sha256(local_path.read_bytes()).hexdigest(),
        joint_result=result,
        affected_nets=affected,
        removed_copper=[
            dict(uuid=p["uuid"], net=p["net"], kind=p["kind"], literal=sexpr(p["node"])) for p in ripped
        ],
        bounded_development_trial=bounded,
        no_rule_pad_ground_reference_force_or_Kelvin_primitive_changed=True,
        native_all_affected_connectivity_and_PDN_pending=True,
        qualified=False,
    )
    if not result["connected"] or not bounded:
        p = SOURCE / "generated/ordinary-joint7-rejected.json"
        assert not p.exists()
        p.write_text(json.dumps(report, indent=2) + "\n")
        raise AssertionError("Bounded joint trial rejected; original source unchanged")
    removed = [p["node"] for p in ripped]
    tree[:] = [n for n in tree if n not in removed]
    for i, n in enumerate(added):
        n.append(
            [a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:jointRipup:{digest}:{i}:{sexpr(n)}")))]
        )
    report["added_copper"] = [sexpr(n) for n in added]
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
    (WORK / "generated/ordinary-joint7.json").write_text(json.dumps(report, indent=2) + "\n")
    assert source.read_bytes() == original
    print("Accepted planning candidate", affected, len(ripped), flush=True)


if __name__ == "__main__":
    main()
