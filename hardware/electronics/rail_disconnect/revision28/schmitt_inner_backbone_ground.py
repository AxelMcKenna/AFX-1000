"""Use the existing two barrels for an inner buffered backbone, opening U36 GND exit."""

import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .band_router import BandRouter
from .component_routes import connect_components
from .receiver_surface_path import connect
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-translated-cell-routes-work"
FILL_BASE = ROOT / "generated/schmitt-translation-backbone-work"
WORK = ROOT / "generated/schmitt-inner-backbone-ground-work"
PATH = [(11.125, 12.5), (10.6, 12.275), (9.15, 12.275), (8.125, 11.25)]


class InnerOnly(BandRouter):
    def masks(self, net, width):
        blocked, via = super().masks(net, width)
        blocked = blocked.copy()
        via = via.copy()
        blocked[0] = True
        blocked[5] = True
        via[:] = True
        return blocked, via


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    base = read_sexpr((FILL_BASE / "rail_disconnect.kicad_pcb").read_text())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}

    def inner(tree):
        return sorted(
            sexpr(n)
            for k in ("segment", "via")
            for n in children(tree, k)
            if k == "via" or first(n, "layer")[1] != "B.Cu"
        )

    assert inner(t) == inner(base), (
        "Prior native fill can only be reused for identical inner physical copper/holes"
    )
    removed = []
    edges = [{tuple(x), tuple(y)} for x, y in zip(PATH, PATH[1:])]
    for n in list(children(t, "segment")):
        if names[str(first(n, "net")[1])] == "P19_OV_OK_SCHMITT" and first(n, "layer")[1] == "B.Cu":
            ends = {tuple(round(float(v) - 100, 6) for v in first(n, k)[1:]) for k in ("start", "end")}
            if ends in edges:
                removed.append(sexpr(n))
                t.remove(n)
    assert len(removed) == 3
    filled = FILL_BASE / "generated/filled-schmitt-translation-backbone.kicad_pcb"
    pads = FILL_BASE / "generated/native-pads.json"
    rt = InnerOnly(t, read_sexpr(filled.read_text()), json.loads(pads.read_text()), step=0.05)
    net = "P19_OV_OK_SCHMITT"
    points = [(11.125, 12.5), (8.125, 11.25)]
    assert all(rt.existing_via(net, p) is not None for p in points)
    result = connect_components(
        rt,
        dict(
            net=net,
            components=[
                [dict(xy=p, layers=list(range(6)), kind="PCB_VIA", actual_existing_barrel=True)]
                for p in points
            ],
        ),
        width=0.2,
        budget=1000000,
    )
    print("inner backbone", result.get("connected"), result.get("reason"), result.get("visited"), flush=True)
    assert result.get("connected"), result
    # A real current-source GND main barrel, with the B-surface barrier removed.
    physical = Router(t)
    p = next(p for p in physical.by_ref["U36"] if p["pin"] == "4")
    targets = [
        dict(xy=g["xy"], kind="PCB_VIA", actual_existing_same_net=True)
        for g in physical.geometry
        if g["kind"] == "via" and g["net"] == "AGND" and math.dist(g["xy"], p["xy"]) < 12
    ]
    targets = sorted(targets, key=lambda g: math.dist(g["xy"], p["xy"]))[:32]
    ground, reason = connect(physical, p, targets, radius=12, step=0.025, budget=500000)
    print("GND4", bool(ground), reason, flush=True)
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"rmx:E28:inner-backbone-ground:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
                            )
                        )
                    ),
                ]
            )
    before_vias = sorted(sexpr(n) for n in children(read_sexpr(blob.decode()), "via"))
    assert before_vias == sorted(sexpr(n) for n in children(t, "via"))
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
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    (WORK / "generated/inner-backbone-ground.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                prior_native_filled_source_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(),
                prior_native_pad_geometry_sha256=hashlib.sha256(pads.read_bytes()).hexdigest(),
                input_inner_layers_and_all_via_geometry_literal_equal_to_prior_filled_source=True,
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                removed_three_ordinary_B_backbone_pieces=removed,
                actual_inner_route=result,
                ground_surface_route=ground,
                ground_failure=reason,
                no_new_drills_verified_literal=True,
                original_quiet_force_and_ground_Cu_preserved=True,
                actual_refilled_force_and_return_diagnostics_required=True,
                native_checks_pending=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
