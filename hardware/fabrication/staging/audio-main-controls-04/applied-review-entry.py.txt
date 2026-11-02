"""Complete accessible codec control branches without changing placed circuitry."""

import argparse
import copy
import json
import shutil
import sys
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.audio_main_global_controls import HELPERS, LAYERS, plan
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-settle-repack-01"
OUT = ROOT / "staging/audio-main-controls-04"
TARGETS = {"/CODEC/CODEC_RUN", "/CODEC/TIMER_OK"}


def snapshot(label):
    dest = OUT / ("applied-"+label+".py.txt")
    assert not dest.exists()
    shutil.copyfile(Path(__file__), dest)
    return dest


def build():
    applied = snapshot("control-build")
    assert not (OUT / "distribution-input.kicad_pcb").exists()
    capture = OUT / "native-inputs.json"
    captured = json.loads(capture.read_text())
    verify_hashes(captured["source_sha256"])
    assert captured["native_uncapped_opens"] == 213
    objects = {o["uuid"]: o for o in captured["objects"]}
    selected = copy.deepcopy(captured)
    selected["groups"] = {k: ids for k, ids in captured["groups"].items() if objects[ids[0]]["net"] in TARGETS}
    routes, attempts = plan(selected, seconds=40, per_route=15)
    assert len(routes) == 2 and {r["net"] for r in routes} == TARGETS, "Both codec branches must complete"
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    nets = {str(n[2]): n[1] for n in children(board, "net")}
    tracks, vias = [], []
    for row in routes:
        for layer, points in row["runs"]:
            for start, end in zip(points, points[1:]):
                ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:controls04:{row['net']}:{layer}:{start}:{end}"))
                tracks.append(dict(uuid=ident, net=row["net"], layer=layer, start_mm=start, end_mm=end, width_mm=.2))
                board.append([a("segment"), [a("start"), *start], [a("end"), *end], [a("width"), .2],
                              [a("layer"), layer], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
        for xy in row["new_vias_mm"]:
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL, f"AFX:controls04:via:{row['net']}:{xy}"))
            vias.append(dict(uuid=ident, net=row["net"], xy_mm=xy, diameter_mm=.6, drill_mm=.3))
            board.append([a("via"), [a("at"), *xy], [a("size"), .6], [a("drill"), .3],
                          [a("layers"), "F.Cu", "B.Cu"], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "distribution-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    inputs = [applied, Path(__file__), SOURCE / "audio_core.kicad_pcb", SOURCE / "routing-handoff.json", capture,
              ROOT / "audio_main_global_controls.py"]+[ROOT / p for p in HELPERS]
    record = dict(source_sha256=relative_hashes(inputs), authored_PCB_sha256=sha(dest), routes=routes, attempts=attempts,
                  added_segments=tracks, added_vias=vias, allowed_control_nets=sorted(TARGETS), signal_layers=LAYERS,
                  trace_width_mm=.2, clearance_mm=.2, planning_margin_mm=.01, search_seconds=40,
                  per_route_search_seconds=15, maximum_search_visits=500000, via_diameter_mm=.6, drill_mm=.3,
                  maximum_new_vias_per_join=4, sensitive_analog_regions_protected_on_all_routed_layers=True,
                  all_parent_objects_exact_before_native_refill=True, native_checks_pending=True,
                  control_timing_signal_integrity_EMI_and_installed_fault_qualified=False, fabrication_released=False)
    (OUT / "distribution-construction.json").write_text(json.dumps(record, indent=2)+"\n")
    assert sha(applied) == sha(Path(__file__))
    print("Built", len(routes), "codec joins /", len(tracks), "tracks /", len(vias), "vias")


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    applied = snapshot(action+"-entry")
    if action == "fill":
        from hardware.fabrication import audio_main_power_routes as helper

        helper.OUT = OUT
        helper.fill()
        result = OUT / "native-refill.json"
    else:
        from hardware.fabrication.audio_main_native_review import review

        review(OUT, SOURCE / "terminal-connectivity-review.json", OUT / "native-inputs.json",
               OUT / "distribution-construction.json", applied)
        result = OUT / "terminal-connectivity-review.json"
    report = dict(source_sha256=relative_hashes([applied, result]), selected_output=str(OUT.relative_to(ROOT)), fabrication_released=False)
    (OUT / (action+"-entry.json")).write_text(json.dumps(report, indent=2)+"\n")
    assert sha(applied) == sha(Path(__file__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "fill", "review"))
    args = parser.parse_args()
    {"build": build, "fill": lambda: native("fill"), "review": lambda: native("review")}[args.action]()
