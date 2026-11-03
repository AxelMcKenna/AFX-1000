"""Route explicit low-current bias-window inputs on the six-layer audio trial.

Only the four comparator input nets below are eligible. No differential audio,
negative-bias supply, relay current, component pose or existing copper changes.
Native Linux review is mandatory and installed noise/fault testing remains open.
"""

import argparse
import itertools
import json
import math
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-local-01"
OUT = ROOT / "staging/audio-main-six-monitor-01"
NETS = {"/ADC/BIAS_SHIFT_L", "/ADC/BIAS_SHIFT_R", "/ADC/THRESH_UPPER", "/ADC/THRESH_LOWER"}


def snapshot(label):
    p = OUT / ("applied-" + label + ".py.txt")
    assert not p.exists()
    shutil.copyfile(Path(__file__), p)
    return p


def capture():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    from hardware.fabrication.capture_audio_layer_trial import capture as native_capture

    assert not OUT.exists()
    report = json.loads((SOURCE / "surface-delta-review.json").read_text())
    verify_hashes(report["source_sha256"])
    assert report["uncapped_open_connections"] == 180 and not report["fabrication_released"]
    OUT.mkdir()
    applied = snapshot("input-capture")
    native_capture(OUT, SOURCE / "audio_core.kicad_pcb", SOURCE / "surface-delta-review.json", "native-inputs.json", applied)


def build():
    from shapely.geometry import LineString
    from shapely.strtree import STRtree

    from hardware.fabrication.audio_main_continuous_path import route
    from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
    from hardware.fabrication.audio_main_joint_fanouts import choices
    from hardware.fabrication.audio_main_layer_screen import LayeredSignalScreen
    from hardware.fabrication.route_nf_surface import candidate_paths

    assert not (OUT / "distribution-input.kicad_pcb").exists()
    applied = snapshot("monitor-routing")
    captured = json.loads((OUT / "native-inputs.json").read_text())
    verify_hashes(captured["source_sha256"])
    assert captured["native_uncapped_opens"] == 180 and captured["layer_count"] == 6
    objects = {o["uuid"]: o for o in captured["objects"]}
    groups = {frozenset([k]): [objects[uid] for uid in ids if objects[uid]["kind"] == "PAD" and objects[uid]["pin"]]
              for k, ids in captured["groups"].items() if objects[ids[0]]["net"] in NETS}
    assert all(groups.values())
    screen = LayeredSignalScreen(captured)
    noisy = set(CONTROL_NETS) | {"/CODEC/ADC_DATA", "/CODEC/BCLK", "/CODEC/WS", "/CODEC/SCL", "/CODEC/SDA",
                               "GAIN_LOW", "/BYPASS/BYPASS_LOW", "/BYPASS/INPUT_LOW"}
    for face in screen.layers:
        screen.geometry[face] = [(net, g, max(d, .71) if net in noisy else d) for net, g, d in screen.geometry[face]]
        screen.trees[face] = STRtree([g for _, g, _ in screen.geometry[face]])
    routes, deferred = [], []
    failed = set()
    while True:
        tasks = []
        for left, right in itertools.combinations(groups, 2):
            if groups[left][0]["net"] != groups[right][0]["net"] or (left, right) in failed:
                continue
            p, q = min(itertools.product(groups[left], groups[right]),
                       key=lambda pair: math.dist(pair[0]["position_mm"], pair[1]["position_mm"]))
            tasks.append((math.dist(p["position_mm"], q["position_mm"]), tuple(sorted(left)), tuple(sorted(right)), left, right))
        if not tasks:
            break
        _, _, _, left, right = min(tasks)
        net = groups[left][0]["net"]
        pads = sorted(itertools.product(groups[left], groups[right]),
                      key=lambda pair: math.dist(pair[0]["position_mm"], pair[1]["position_mm"]))
        selected = None
        for p, q in pads[:8]:
            start, end = p["position_mm"], q["position_mm"]
            limit = min(40, 2*math.dist(start, end)+6)
            # First keep any legal short connection on a shared surface.
            for face in ("F.Cu", "B.Cu"):
                if not p["layers"].get(face) or not q["layers"].get(face):
                    continue
                for raw in candidate_paths(start, end):
                    points = [xy for i, xy in enumerate(raw) if not i or xy != raw[i-1]]
                    length = LineString(points).length
                    if length <= limit and screen.legal(net, face, points):
                        row = dict(runs=[(face, points)], new_vias_mm=[], planar_length_mm=length)
                        if selected is None or length < selected[0]:
                            selected = length, row, p, q, limit
            if selected:
                break
            left_ports = choices(screen, p, next(iter(left)), limit=24)
            right_ports = choices(screen, q, next(iter(right)), limit=24)
            options = sorted(itertools.product(left_ports, right_ports),
                             key=lambda pair: pair[0]["cost"]+pair[1]["cost"]+math.dist(pair[0]["point"], pair[1]["point"]))
            for entry, exit_port in options[:96]:
                vias = [entry["point"], exit_port["point"]]
                if math.dist(*vias) <= .86 or any(math.dist(xy, old) <= .86 for xy in vias for _, old in screen.new_vias):
                    continue
                bounds = [min(start[0], end[0])-5, min(start[1], end[1])-5,
                          max(start[0], end[0])+5, max(start[1], end[1])+5]
                middle = route(screen, net, "In3.Cu", vias[0], vias[1], bounds, seconds=3)
                if not middle:
                    continue
                runs = entry["runs"]+[("In3.Cu", middle["points_mm"])]+[(face, list(reversed(ps))) for face, ps in reversed(exit_port["runs"])]
                length = sum(LineString(ps).length for _, ps in runs)
                if length > limit:
                    continue
                row = dict(runs=runs, new_vias_mm=vias, planar_length_mm=length,
                           continuous_path_receipt=middle)
                selected = length, row, p, q, limit
                break
            if selected:
                break
        if selected is None:
            failed.add((left, right))
            deferred.append(dict(net=net, source_groups=[sorted(left), sorted(right)], reason="No short path under the unchanged copper, ground-reference and two-via limits"))
            continue
        length, row, p, q, limit = selected
        row.update(net=net, source_groups=[sorted(left), sorted(right)], endpoints=[[p["ref"], p["pin"]], [q["ref"], q["pin"]]],
                   terminal_points_mm=[p["position_mm"], q["position_mm"]], maximum_planar_length_mm=limit,
                   maximum_new_vias=2, purpose="bias_window_comparator_input")
        for face, ps in row["runs"]:
            assert screen.legal(net, face, ps)
        # Screen each new drill against the final runs as well as existing
        # native copper. The same-net escape must end exactly at its via.
        for i, xy in enumerate(row["new_vias_mm"]):
            assert screen.via_legal(net, xy)
            assert all(math.dist(xy, other) > .86 for other in row["new_vias_mm"][:i])
        routes.append(row)
        screen.added.extend((net, face, LineString(ps)) for face, ps in row["runs"])
        screen.new_vias.extend((net, xy) for xy in row["new_vias_mm"])
        groups[left | right] = groups.pop(left)+groups.pop(right)
        print(net, row["endpoints"], round(length, 3), "mm /", len(row["new_vias_mm"]), "vias", flush=True)
    assert routes
    source_pcb = SOURCE / "audio_core.kicad_pcb"
    board = read_sexpr(source_pcb.read_text())
    count, original = len(board), sexpr(board)
    added = []
    for row in routes:
        for face, points in row["runs"]:
            add_geometry(board, added, row["net"], face, points, .2, row["purpose"])
        for xy in row["new_vias_mm"]:
            add_via(board, added, row["net"], xy, row["purpose"])
    assert sexpr(board[:count]) == original
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "distribution-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    record = dict(source_sha256=relative_hashes([applied, OUT / "native-inputs.json", source_pcb, SOURCE / "native-netlist.xml",
                   ROOT / "audio_main_layer_screen.py", ROOT / "audio_main_continuous_path.py", ROOT / "audio_main_joint_fanouts.py",
                   ROOT / "audio_main_control_routes.py", ROOT / "audio_main_bypass_repack.py"]), authored_PCB_sha256=sha(dest),
                  allowed_nets=sorted(NETS), routes=routes, deferred_requests=deferred,
                  added_segments=[r for r in added if r["kind"] == "segment"], added_vias=[r for r in added if r["kind"] == "via"],
                  trace_width_mm=.2, clearance_mm=.2, planning_margin_mm=.01, noisy_net_centreline_to_copper_mm=.71,
                  noisy_nets=sorted(noisy), expected_native_opens=180-len(routes),
                  all_existing_geometry_exact=True, native_checks_pending=True,
                  input_noise_coupling_and_installed_fault_performance_qualified=False, fabrication_released=False)
    (OUT / "distribution-construction.json").write_text(json.dumps(record, indent=2)+"\n")
    print("Constructed", len(routes), "monitor joins; expected opens", record["expected_native_opens"], flush=True)


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    applied = snapshot(action+"-entry")
    if action == "fill":
        from hardware.fabrication import audio_main_power_routes as helper
        helper.OUT = OUT
        helper.fill()
    elif action == "review":
        from hardware.fabrication.audio_main_native_review import review
        review(OUT, SOURCE / "terminal-connectivity-review.json", OUT / "native-inputs.json", OUT / "distribution-construction.json", applied)
    else:
        from hardware.fabrication.review_audio_layer_retention import review
        review(SOURCE, OUT, 88, applied)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "build", "fill", "review", "retain"))
    action = parser.parse_args().action
    {"capture": capture, "build": build}.get(action, lambda: native(action))()
