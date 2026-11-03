"""Retain an exact common-via bridge while planning the remaining control joins."""

import copy
import json
import math
import shutil
from pathlib import Path

from hardware.fabrication.audio_main_global_controls import HELPERS, plan
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "staging/audio-main-controls-07"
TARGETS = {"/BYPASS/TIMER_INPUT_OK", "/CODEC/CODEC_PGOOD", "CHIP_EN"}


def run():
    import hardware.fabrication.nf_multilayer_raster_directed as search
    import hardware.fabrication.nf_pin_escape_routes as raster

    capture = OUT / "native-inputs.json"
    dest = OUT / "seeded-control-routing-proposal.json"
    assert not dest.exists()
    applied = OUT / "applied-seeded-control-probe.py.txt"
    assert not applied.exists()
    shutil.copyfile(Path(__file__), applied)
    inputs = [Path(__file__), applied, capture, ROOT / "audio_main_global_controls.py", ROOT / "audio_main_via_weighted_router.py"]+[ROOT / p for p in HELPERS]
    inputs.append(ROOT / "audio_main_chip_enable_bridge.py")
    before = relative_hashes(inputs)
    captured = json.loads(capture.read_text())
    verify_hashes(captured["source_sha256"])
    assert captured["native_uncapped_opens"] == 205
    objects = {o["uuid"]: o for o in captured["objects"]}
    selected = copy.deepcopy(captured)
    selected["groups"] = {k: ids for k, ids in sorted(captured["groups"].items(), key=lambda row: (-len(row[1]), row[0]))
                          if objects[ids[0]]["net"] in TARGETS}
    # This changes planning resolution only. Actual copper/clearance, drill,
    # reference, via-count and length constraints remain exact and unchanged.
    raster.STEP = search.STEP = .2
    raster.RASTER_MARGIN = math.sqrt(2)*raster.STEP/2+.002
    candidates = []
    from hardware.fabrication import audio_main_via_weighted_router as weighted
    from hardware.fabrication.audio_main_global_controls import LAYERS, via_mask
    weighted.LAYERS, weighted.via_mask = LAYERS, via_mask
    weighted.STEP, weighted.WIDTH = .2, .2
    original = weighted.route_multi
    def observe(screen, net, starts, ends, deadline, **kwargs):
        result = original(screen, net, starts, ends, deadline, **kwargs)
        if result is not None:
            from shapely.geometry import LineString
            fresh = [p for p in result["vias"] if not any(other == net and math.dist(p, q) < 1e-7 for other, q in screen.vias+screen.new_vias)]
            length = sum(LineString(points).length for _, points in result["runs"])
            terminal_points = [result["runs"][0][1][0], result["runs"][-1][1][-1]]
            limit = min(180, 2.5*math.dist(*terminal_points)+10)
            candidates.append(dict(net=net, result=result, fresh_vias_mm=fresh, planar_length_mm=length,
                                   maximum_planar_length_mm=limit, actual_fresh_via_count=len(fresh),
                                   within_via_limit=len(fresh)<=4, within_length_limit=length<=limit,
                                   individual_new_vias_legal=all(screen.via_legal(net,p) for p in fresh)))
        return result
    search.route_multi = observe
    from hardware.fabrication.audio_main_chip_enable_bridge import propose
    bridge = propose(captured)
    routes, attempts = plan(selected, seconds=100, per_route=30, seed_routes=[bridge])
    verify_hashes(before)
    result = dict(source_sha256=before, targets=sorted(TARGETS), grid_step_mm=.2,
                  route_search_seconds=30, total_search_seconds=100, maximum_visits_per_join=500000,
                  start_groups_ordered_by_size_descending=True, via_search_penalty_mm=20.0, routes=routes, attempts=attempts, candidates=candidates,
                  proposal_only=True, native_checks_pending=True, fabrication_released=False)
    dest.write_text(json.dumps(result, indent=2)+"\n")
    print("Planned", len(routes), "joins from", len(candidates), "paths; no board emitted")


if __name__ == "__main__":
    run()
