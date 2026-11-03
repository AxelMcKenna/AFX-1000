"""Renew the GAIN_REQ branch clear of comparator inputs; retain the placed board."""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-monitor-01"
OUT = ROOT / "staging/audio-main-six-monitor-03"
GAIN = "/BYPASS/GAIN_REQ"
MONITORS = {"/ADC/BIAS_SHIFT_L", "/ADC/BIAS_SHIFT_R", "/ADC/THRESH_UPPER", "/ADC/THRESH_LOWER"}
RETIRED = {
    "166bdbe7-3c5b-50bc-b178-c0263b4e185f", "35d5c09a-5e9a-5046-966b-f705bd446225",
    "447e6f58-bc59-5a39-9b8e-27427eb25be4", "79c6445e-97d2-57a5-a83e-457e94442bdf",
    "850dad2b-227e-5384-a26b-7398d7647ccb", "9f5253d3-88d0-51e0-89d0-421fee009ab1",
    "a59e96a9-96e1-5d14-92fb-412accc0d1d5", "b65764be-9782-58c7-b722-925f57fd308e",
    "e51a82c8-c126-5b42-a715-08d02f46911c", "e5ab9cb0-c52a-5b71-aeae-faa2fb59de02",
    "e5e80630-a8b3-5197-8fb1-737bab566ada", "f52f1a68-70ee-5d14-92d7-b7cbc2b6ae78",
    "f5656402-7a86-50fe-936f-7a4f68eba552", "fa5434b3-a5cf-59d3-b121-cc5553c096e0",
    "fcb88307-8615-5292-a01c-99d9cd9a1a1a",
}
GAIN_RUNS = [("F.Cu", [[33.0875, 49], [33.9, 48.4]]),
             ("In3.Cu", [[33.9, 48.4], [35.060414, 54.100709], [24.799009, 55.697832], [3, 45.62]])]
BIAS_RUN = [("B.Cu", [[28.5, 46.8], [28, 47.486419], [28.141835, 49.131546], [28.825, 50]])]


def snapshot(label):
    p = OUT / ("applied-"+label+".py.txt")
    assert not p.exists()
    shutil.copyfile(Path(__file__), p)
    return p


def prepare():
    assert not OUT.exists()
    source = SOURCE / "audio_core.kicad_pcb"
    record = json.loads((SOURCE / "native-refill.json").read_text())
    verify_hashes(record["source_sha256"])
    assert sha(source) == record["filled_PCB_sha256"]
    board = read_sexpr(source.read_text())
    names = {str(n[1]): str(n[2]) for n in children(board, "net")}
    removed = [n for n in children(board, "segment") if str(first(n, "uuid")[1]) in RETIRED]
    assert len(removed) == 15 and all(names[str(first(n, "net")[1])] == GAIN and first(n, "layer")[1] == "F.Cu"
                                     and float(first(n, "width")[1]) == .2 for n in removed)
    prepared = [n for n in board if n not in removed]
    OUT.mkdir()
    applied = snapshot("gain-branch-preparation")
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "prepared-input.kicad_pcb"
    dest.write_text(sexpr(prepared)+"\n")
    report = dict(source_sha256=relative_hashes([applied, source, SOURCE / "native-refill.json", SOURCE / "named-route-review.json"]),
                  authored_PCB_sha256=sha(dest), retired_copper_uuids=sorted(RETIRED), retired_nodes=removed,
                  reason="Renew the branch that violates the enlarged comparator-input noise-spacing policy",
                  all_unretired_geometry_exact=True, expected_native_opens=174, fabrication_released=False)
    (OUT / "preparation-record.json").write_text(json.dumps(report, indent=2)+"\n")
    print("Retired the 15-segment GAIN_REQ branch; all other copper, poses, lands and authored zones exact")


def build():
    from shapely.geometry import LineString

    from hardware.fabrication.audio_main_quiet_screen import QuietTraceScreen
    from hardware.fabrication.audit_audio_main_named_routes import NOISY

    applied = snapshot("gain-repair-and-bias-bridge")
    captured = json.loads((OUT / "prepared-native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    assert captured["native_uncapped_opens"] == 174 and captured["layer_count"] == 6
    objects = {o["uuid"]: o for o in captured["objects"]}
    pads = {(o["ref"], o["pin"]): o for o in objects.values() if o["kind"] == "PAD" and o["pin"]}
    membership = {uid: k for k, ids in captured["groups"].items() for uid in ids}
    left, right = pads["R607", "1"], pads["J602", "4"]
    screen = QuietTraceScreen(captured, MONITORS)
    via = [33.9, 48.4]
    assert screen.via_legal(GAIN, via)
    assert all(screen.legal(GAIN, face, ps) for face, ps in GAIN_RUNS)
    length = sum(LineString(ps).length for _, ps in GAIN_RUNS)
    limit = min(180, 2.5*math.dist(left["position_mm"], right["position_mm"])+10)
    assert length <= limit
    gain = dict(net=GAIN, source_groups=[[membership[left["uuid"]]], [membership[right["uuid"]]]], runs=GAIN_RUNS,
                endpoints=[["R607", "1"], ["J602", "4"]], terminal_points_mm=[left["position_mm"], right["position_mm"]],
                new_vias_mm=[via], planar_length_mm=length, maximum_planar_length_mm=limit,
                purpose="quiet_gpio_repair", repaired_existing_join=True)
    assert gain["source_groups"][0] != gain["source_groups"][1]
    quiet = QuietTraceScreen(captured, NOISY)
    quiet.added.extend((GAIN, face, LineString(ps)) for face, ps in GAIN_RUNS)
    quiet.new_vias.append((GAIN, via))
    p = objects["e193935e-1685-5e3b-8613-dff81b72a3fb"]
    q = pads["R136", "2"]
    assert p["net"] == q["net"] == "/ADC/BIAS_SHIFT_R" and p["kind"] == "PCB_VIA"
    assert p["position_mm"] == [28.5, 46.8] and q["position_mm"] == [28.825, 50]
    assert quiet.legal(q["net"], "B.Cu", BIAS_RUN[0][1])
    length = LineString(BIAS_RUN[0][1]).length
    limit = min(8, 1.6*math.dist(p["position_mm"], q["position_mm"])+.5)
    assert length <= limit
    bridge = dict(net=q["net"], source_groups=[[membership[p["uuid"]]], [membership[q["uuid"]]]], runs=BIAS_RUN,
                  native_contacts=[dict(uuid=p["uuid"], face="B.Cu", point_mm=p["position_mm"]),
                                   dict(uuid=q["uuid"], face="B.Cu", point_mm=q["position_mm"])],
                  terminal_points_mm=[p["position_mm"], q["position_mm"]], new_vias_mm=[],
                  planar_length_mm=length, maximum_planar_length_mm=limit,
                  purpose="short_comparator_surface_bridge", repaired_existing_join=False)
    assert bridge["source_groups"][0] != bridge["source_groups"][1]
    board = read_sexpr((OUT / "prepared-refilled.kicad_pcb").read_text())
    original, count, additions = sexpr(board), len(board), []
    for row in (gain, bridge):
        for face, ps in row["runs"]:
            add_geometry(board, additions, row["net"], face, ps, .2, row["purpose"])
        for xy in row["new_vias_mm"]:
            add_via(board, additions, row["net"], xy, row["purpose"])
    assert sexpr(board[:count]) == original
    dest = OUT / "distribution-input.kicad_pcb"
    assert not dest.exists()
    dest.write_text(sexpr(board)+"\n")
    report = dict(source_sha256=relative_hashes([applied, OUT / "prepared-native-inputs.json", OUT / "prepared-refilled.kicad_pcb",
        OUT / "preparation-record.json", ROOT / "audio_main_quiet_screen.py", ROOT / "audio_main_bypass_repack.py",
        ROOT / "audit_audio_main_named_routes.py"]), authored_PCB_sha256=sha(dest), routes=[gain, bridge],
        added_segments=[r for r in additions if r["kind"] == "segment"], added_vias=[r for r in additions if r["kind"] == "via"],
        trace_width_mm=.2, clearance_mm=.2, planning_margin_mm=.01, noisy_net_centreline_to_copper_mm=.71,
        repaired_existing_control_joins=1, new_comparator_joins=1, expected_native_opens=172,
        native_checks_pending=True, electrical_noise_and_installed_fault_performance_qualified=False, fabrication_released=False)
    (OUT / "distribution-construction.json").write_text(json.dumps(report, indent=2)+"\n")
    print("GAIN_REQ repair", round(gain["planar_length_mm"], 3), "mm / one via; BIAS_SHIFT_R bridge", round(length, 3), "mm / no new vias")


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    applied = snapshot(action+"-entry")
    if action == "fill-prepared":
        from hardware.fabrication import audio_main_six_layer_trial as helper
        helper.OUT = OUT
        helper.fill_prepared()
        result = OUT / "prepared-refill.json"
    elif action == "capture":
        from hardware.fabrication.capture_audio_layer_trial import capture
        capture(OUT, OUT / "prepared-refilled.kicad_pcb", OUT / "prepared-refill.json", "prepared-native-inputs.json", applied)
        result = OUT / "prepared-native-inputs.json"
    elif action == "fill":
        from hardware.fabrication import audio_main_power_routes as helper
        helper.OUT = OUT
        helper.fill()
        result = OUT / "native-refill.json"
    elif action == "review":
        from hardware.fabrication.audio_main_native_review import review
        review(OUT, SOURCE / "terminal-connectivity-review.json", OUT / "prepared-native-inputs.json", OUT / "distribution-construction.json", applied)
        result = OUT / "terminal-connectivity-review.json"
    elif action == "retain":
        from hardware.fabrication.review_audio_layer_retention import review
        review(SOURCE, OUT, 95, applied)
        result = OUT / "additional-terminal-review.json"
    else:
        from hardware.fabrication.capture_audio_layer_trial import capture
        capture(OUT, OUT / "audio_core.kicad_pcb", OUT / "terminal-connectivity-review.json", "final-native-inputs.json", applied)
        result = OUT / "final-native-inputs.json"
    (OUT / (action+"-entry.json")).write_text(json.dumps(dict(source_sha256=relative_hashes([applied, result]), fabrication_released=False), indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "fill-prepared", "capture", "build", "fill", "review", "retain", "capture-final"))
    action = parser.parse_args().action
    {"prepare": prepare, "build": build}.get(action, lambda: native(action))()
