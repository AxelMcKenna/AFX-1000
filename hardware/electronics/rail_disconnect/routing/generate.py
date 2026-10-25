"""Route a separate E25 candidate without changing the placed/mechanical source."""

import argparse
import json
import shutil
from pathlib import Path

from ...common.reports import sha
from ...common.sexpr import children, read_sexpr, sexpr
from .router import Router

ROOT = Path(__file__).resolve().parent
PLACEMENT = ROOT.parent / "placement"
OUT = ROOT / "generated"


def generate(complete=False, reviewed=False):
    OUT.mkdir(exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    baseline = PLACEMENT / "rail_disconnect.kicad_pcb"
    record = json.loads((PLACEMENT / "generated/verification.json").read_text())
    for name, expected in record["source_sha256"].items():
        assert sha(PLACEMENT / name) == expected, ("Stale placement baseline", name)
    board = read_sexpr(baseline.read_text())
    assert not any(children(board, key) for key in ("segment", "via", "zone"))
    router = Router(board)
    # Each VSON has three separate source lands; include every physical land.
    for index in range(1, 15):
        pads = router.by_ref[f"Q{index}"]
        points = sorted((p["xy"] for p in pads if p["pin"] == "1"), key=lambda p: p[1])
        net = next(p["net"] for p in pads if p["pin"] == "1")
        router.path(net, 0, points, 0.7)
    # Back-to-back source buses are short, broad local conductors, not remote
    # thin control traces. Their actual DC/thermal/current balance is unqualified.
    for left, right in ((1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14)):
        l = router.by_ref[f"Q{left}"]
        r = router.by_ref[f"Q{right}"]
        source_l = [p for p in l if p["pin"] == "1"]
        source_r = [p for p in r if p["pin"] == "1"]
        x0, x1 = source_l[0]["xy"][0], source_r[0]["xy"][0]
        y = (min(p["xy"][1] for p in source_l) + max(p["xy"][1] for p in source_r)) / 2
        router.path(source_l[0]["net"], 0, [(x0, y), (x1, y)], 1.2)
    # Preserve both physical digital MOSFET paths, including their common bus.
    router.path("5V_DIG_COMMON", 0, [(131.5, 7), (131.5, 13)], 1.2)
    router.path("5V_DIG_SRC", 0, [(126.67, 7), (126.67, 13)], 2.0)
    router.path("5V_DIG", 0, [(136.33, 7), (136.33, 13)], 2.0)
    stage = OUT / "local-source-bars"
    stage.mkdir(exist_ok=True)
    (stage / "rail_disconnect.kicad_pcb").write_text(sexpr(board) + "\n")
    (stage / "routing-inputs.json").write_text(
        json.dumps(
            dict(
                revision="E25-local-source-bars",
                routes=list(router.routes),
                baseline_placement_pcb_sha256=sha(baseline),
                pcb_routed=False,
                dc_loss_current_balance_or_thermal_qualified=False,
                build_ready=False,
            ),
            indent=2,
        )
        + "\n"
    )
    if complete:
        router.route_all()
    if reviewed:
        recipe = json.loads((ROOT / "reviewed-copper.json").read_text())
        assert recipe["baseline_placement_pcb_sha256"] == sha(baseline)
        board = read_sexpr(baseline.read_text())
        board.extend(read_sexpr(item) for item in recipe["copper_s_expressions"])
        router = Router(board)
        router.load_existing_copper()
    for name in ("rail_disconnect.kicad_pro", "fp-lib-table"):
        shutil.copy2(PLACEMENT / name, ROOT / name)
    shutil.copytree(PLACEMENT / "RMX_Disconnect.pretty", ROOT / "RMX_Disconnect.pretty", dirs_exist_ok=True)
    (ROOT / "rail_disconnect.kicad_pcb").write_text(sexpr(board) + "\n")
    report = dict(
        revision="E25-routing",
        baseline_placement_pcb_sha256=sha(baseline),
        baseline_placement_verification_sha256=sha(PLACEMENT / "generated/verification.json"),
        placed_geometry_preserved=True,
        requested_complete_routing=complete,
        reviewed_copper_replayed=reviewed,
        reviewed_copper_recipe_sha256=sha(ROOT / "reviewed-copper.json") if reviewed else None,
        routed_segments=len(children(board, "segment")),
        through_vias=len(children(board, "via")),
        routes=router.routes,
        unrouted_tasks=router.failed,
        pcb_routed=False,
        copper_loss_or_current_balance_qualified=False,
        physical_protection_verified=False,
        build_ready=False,
    )
    (OUT / "routing-inputs.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E25 candidate: {report['routed_segments']} segments, {report['through_vias']} vias; native DRC required"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--complete", action="store_true", help="Attempt conservative six-layer maze routing")
    mode.add_argument(
        "--reviewed", action="store_true", help="Replay the independently checked123-open copper candidate"
    )
    args = parser.parse_args()
    generate(args.complete, args.reviewed)


if __name__ == "__main__":
    main()
