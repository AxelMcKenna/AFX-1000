"""Add bounded local audio connections to AC04 using native pad polygons.

The codec land, global supplies/returns and the remaining board routing are
explicitly unfinished. Native operations run only in the isolated Linux image.
"""

import argparse
import json
import math
import shutil
import sys
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication"
SOURCE = ROOT / "staging/audio-main-placement-02"
OUT = ROOT / "staging/audio-main-local-routing-01"


def relative_hashes(paths):
    return {str(p.relative_to(REPO)): sha(p) for p in paths}


def verify_hashes(record):
    assert all(sha(REPO / p) == h for p, h in record.items())


def capture():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication.capture_board import polygons

    assert not OUT.exists(), "Preserve earlier candidates"
    pcb = SOURCE / "audio_core.kicad_pcb"
    drc = json.loads((SOURCE / "drc.json").read_text())
    assert drc["violations"] == [] and drc["ignored_checks"] == []
    assert drc["schematic_parity"] == [dict(
        description="Missing footprint U201 (ES9292QPRO)", items=[],
        severity="warning", type="missing_footprint")]
    before = relative_hashes([pcb, SOURCE / "drc.json", SOURCE / "placement-handoff.json"])
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    board.GetConnectivity().RecalculateRatsnest()
    assert board.GetConnectivity().GetUnconnectedCount(False) == 724
    assert len(list(board.GetFootprints())) == 334 and not list(board.GetTracks())
    layers = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")
    rows = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            row = dict(uuid=pad.m_Uuid.AsString(), kind="PAD", ref=fp.GetReference(),
                       pin=pad.GetNumber(), net=pad.GetNetname(),
                       position_mm=[pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6],
                       drill_mm=[pad.GetDrillSize().x / 1e6, pad.GetDrillSize().y / 1e6],
                       npth=int(pad.GetAttribute()) == int(pcbnew.PAD_ATTRIB_NPTH), layers={})
            for name in layers:
                layer = board.GetLayerID(name)
                if pad.IsOnLayer(layer):
                    poly = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(.001), pcbnew.ERROR_OUTSIDE)
                    poly.Simplify()
                    row["layers"][name] = polygons(poly)
            rows.append(row)
    zones = []
    for zone in board.Zones():
        assert zone.GetIsRuleArea(), "This source has only the explicit codec reserve"
        for name in layers:
            if zone.IsOnLayer(board.GetLayerID(name)):
                zones.append(dict(net=zone.GetNetname(), layer=name, keepout=True,
                                  prohibit_tracks=bool(zone.GetDoNotAllowTracks()),
                                  prohibit_vias=bool(zone.GetDoNotAllowVias()), polygons=polygons(zone.Outline())))
    outline = pcbnew.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False)
    verify_hashes(before)
    OUT.mkdir()
    applied = OUT / "applied-input-capture.py.txt"
    shutil.copyfile(Path(__file__), applied)
    before.update(relative_hashes([applied, ROOT / "capture_board.py"]))
    result = dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(),
                  native_uncapped_opens=724, objects=rows, zones=zones, outline=polygons(outline),
                  copper_layers=layers, obstacle_polygons_error="outside 0.001 mm",
                  retained_schematic_parity=drc["schematic_parity"], no_source_geometry_changes=True,
                  fabrication_released=False)
    (OUT / "native-inputs.json").write_text(json.dumps(result, separators=(",", ":")) + "\n")
    print("Captured", len(rows), "native pads and", len(zones), "codec reserve layer shapes")


def requests(plan, pads):
    """Resolve every declared placement endpoint to a real numbered pad."""
    result = []
    for cell in plan["local_cells"]:
        ref, owner = cell["ref"], cell["owner"]
        layer = cell["side"] + ".Cu"
        for terminal in cell["terminals"]:
            p = pads[(ref, terminal["part_pin"])]
            candidates = [q for (r, _), q in pads.items() if r == owner and q["net"] == p["net"]
                          and math.dist(q["position_mm"], terminal["owner_position_mm"]) < 1e-7]
            assert len(candidates) == 1 and p["net"] and p["net"] != "AGND"
            q = candidates[0]
            assert layer in p["layers"] and layer in q["layers"]
            result.append(dict(ref=ref, pin=p["pin"], owner=owner, owner_pin=q["pin"],
                               net=p["net"], layer=layer, kind=cell["kind"],
                               declared_endpoint_limit_mm=cell["limit_mm"],
                               route_length_limit_mm=1.6 * cell["limit_mm"]))
        # Digital/oscillator decouplers also get a local ground connection when
        # the owning package has an AGND terminal. Amplifier ground returns need
        # the later plane/star design and are not invented here.
        if cell["kind"] == "supply_bypass":
            p = pads[(ref, "2")]
            assert p["net"] == "AGND"
            grounds = [q for (r, _), q in pads.items() if r == owner and q["net"] == "AGND"]
            if grounds:
                q = min(grounds, key=lambda q: math.dist(p["position_mm"], q["position_mm"]))
                result.append(dict(ref=ref, pin="2", owner=owner, owner_pin=q["pin"], net="AGND",
                                   layer=layer, kind="local_ground_return", declared_endpoint_limit_mm=None,
                                   route_length_limit_mm=5.6))
    assert sum(r["kind"] != "local_ground_return" for r in result) == 131
    return result


def best_path(screen, pads, row):
    from hardware.fabrication.route_nf_surface import candidate_paths, shape

    p, q = pads[(row["ref"], row["pin"])], pads[(row["owner"], row["owner_pin"])]
    start, end = tuple(p["position_mm"]), tuple(q["position_mm"])
    net, layer, limit = row["net"], row["layer"], row["route_length_limit_mm"]

    def accepted(path):
        path = [xy for i, xy in enumerate(path) if not i or xy != path[i - 1]]
        length = sum(math.dist(x, y) for x, y in zip(path, path[1:]))
        if len(path) > 1 and length <= limit and screen.legal(net, layer, path):
            return length, path
        return None

    choices = [r for path in candidate_paths(start, end) if (r := accepted(path))]
    # Try finite escapes at actual native pad edges before a bounded grid search.
    if not choices:
        def escapes(pad):
            x, y = pad["position_mm"]
            left, top, right, bottom = shape(pad["layers"][layer]).bounds
            return [(left - .32, y), (right + .32, y), (x, top - .32), (x, bottom + .32)]

        for u in escapes(p):
            if not screen.legal(net, layer, [start, u]):
                continue
            for v in escapes(q):
                if not screen.legal(net, layer, [v, end]):
                    continue
                for middle in candidate_paths(u, v):
                    result = accepted([start, *middle, end])
                    if result:
                        choices.append(result)
    if choices:
        return min(choices, key=lambda r: r[0])
    path = screen.grid_path(net, layer, start, end, budget=2500)
    return accepted(path) if path else None


def build():
    from shapely.geometry import LineString

    from hardware.fabrication.audit_audio_main_placement import check
    from hardware.fabrication.route_nf_surface import Screen

    assert check() == json.loads((SOURCE / "placement-handoff.json").read_text())
    capture_path = OUT / "native-inputs.json"
    captured = json.loads(capture_path.read_text())
    verify_hashes(captured["source_sha256"])
    assert not (OUT / "audio_core.kicad_pcb").exists()
    source_pcb = SOURCE / "audio_core.kicad_pcb"
    board = read_sexpr(source_pcb.read_text())
    original = sexpr(board)
    count = len(board)
    pads = {(p["ref"], p["pin"]): p for p in captured["objects"] if p["pin"]}
    nets = {str(n[2]): int(n[1]) for n in children(board, "net")}
    rows = requests(json.loads((SOURCE / "plan.json").read_text()), pads)
    # Compensation/feedback precede local supplies. Shared-net branches remain
    # on their owner's face; there are no vias or changes to component poses.
    rows.sort(key=lambda r: (r["kind"] in ("supply_bypass", "local_ground_return"),
                             r["route_length_limit_mm"], r["owner"], r["ref"], r["pin"]))
    screen = Screen(captured)
    routed, deferred = [], []
    emitted = set()
    for row in rows:
        selected = best_path(screen, pads, row)
        if selected is None:
            deferred.append(dict(**row, reason="No path within the unchanged clearance and length budgets"))
            print("Deferred", row["ref"], row["pin"], row["owner"], flush=True)
            continue
        length, path = selected
        identifiers = []
        for start, end in zip(path, path[1:]):
            ident = str(uuid.uuid5(uuid.NAMESPACE_URL,
                f"AFX:AC04:local:{sha(source_pcb)}:{row['net']}:{row['layer']}:{start}:{end}"))
            assert ident not in identifiers
            identifiers.append(ident)
            if ident not in emitted:
                board.append([a("segment"), [a("start"), *start], [a("end"), *end], [a("width"), .2],
                              [a("layer"), row["layer"]], [a("net"), nets[row["net"]]], [a("uuid"), ident]])
                emitted.add(ident)
        screen.added.append((row["net"], row["layer"], LineString(path)))
        routed.append(dict(**row, actual_length_mm=length, path_mm=path, segment_uuids=identifiers))
        print("Routed", row["ref"], row["pin"], "to", row["owner"], row["owner_pin"],
              round(length, 3), "mm", flush=True)
    assert sexpr(board[:count]) == original and routed
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in (
                "plan.json", "fp-lib-table", "sym-lib-table"):
            shutil.copyfile(p, OUT / p.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "audio_core.kicad_pcb"
    dest.write_text(sexpr(board) + "\n")
    inputs = [Path(__file__), ROOT / "route_nf_surface.py", capture_path, source_pcb,
              SOURCE / "placement-handoff.json", OUT / "audio_core.kicad_dru"]
    record = dict(source_sha256=relative_hashes(inputs), candidate_PCB_sha256=sha(dest),
                  requests=rows, routes=routed, deferred=deferred, width_mm=.2,
                  general_clearance_mm=.2, host_screen_extra_margin_mm=.01,
                  all_prior_authored_geometry_exact=True, no_vias_or_inner_layer_routes=True,
                  route_budgets_are_project_construction_limits_not_performance_qualification=True,
                  ground_return_distribution_codec_physical_stars_and_global_routing_unfinished=True,
                  native_checks_pending=True, fabrication_released=False)
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    shutil.copyfile(Path(__file__), OUT / "applied-routing.py.txt")
    print("Added", len(routed), "local connections; deferred", len(deferred), "; segments", len(board) - count)


def review():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    from hardware.fabrication import audio_main_placement

    before = relative_hashes([Path(__file__), OUT / "construction.json", OUT / "audio_core.kicad_dru"])
    construction = json.loads((OUT / "construction.json").read_text())
    verify_hashes(construction["source_sha256"])
    assert sha(OUT / "audio_core.kicad_pcb") == construction["candidate_PCB_sha256"]
    audio_main_placement.OUT = OUT
    audio_main_placement.review()
    board = pcbnew.LoadBoard(str(OUT / "audio_core.kicad_pcb"))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    pads = {(f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    witnesses = []
    for row in construction["routes"]:
        p, q = pads[(row["ref"], row["pin"])], pads[(row["owner"], row["owner_pin"])]
        assert p.GetNetname() == q.GetNetname() == row["net"]
        assert q.m_Uuid.AsString() in {item.m_Uuid.AsString() for item in conn.GetConnectedItems(p)}
        witnesses.append(dict(ref=row["ref"], pin=row["pin"], owner=row["owner"],
                              owner_pin=row["owner_pin"], native_connected=True))
    verify_hashes(before)
    paths = [OUT / p for p in ("audio_core.kicad_pcb", "placement-native-review.json", "construction.json")]
    before.update(relative_hashes(paths))
    report = dict(source_sha256=before, native_version=pcbnew.GetBuildVersion(), connections=witnesses,
                  uncapped_open_connections=conn.GetUnconnectedCount(False),
                  original_open_connections=724, no_vias_or_inner_layer_tracks=True,
                  complete_routing_and_qualification=False, fabrication_released=False)
    (OUT / "local-connectivity-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Native connected", len(witnesses), "local pairs; remaining opens", report["uncapped_open_connections"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "build", "review"))
    args = parser.parse_args()
    {"capture": capture, "build": build, "review": review}[args.action]()
