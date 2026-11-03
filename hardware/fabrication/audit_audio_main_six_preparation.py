"""Independently replay the four-to-six-layer audio preparation and native lands.

This checks retained design geometry and the two native fills. It does not
approve a manufacturer's physical stack, added-route performance or fabrication.
"""

import argparse
import copy
import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import a, children, first, read_sexpr
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_audio_main_supplies import without_fill
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-controls-08"
OUT = ROOT / "staging/audio-main-six-control-01"
LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
RETIRED = {
    "599b0ae6-95dc-50a6-a335-b074c9211b30", "60600f0c-7d4e-50f7-9b97-4857f341a340",
    "35949e89-f6d6-53ff-a0d0-69708dd03479", "0aeece30-5475-5eaf-b4a8-6645ea676060",
    "1e17c3c2-6813-56e0-821b-10e35b4395e6", "894e9e9a-912b-5ed3-8be0-aa26c53d9a07",
    "ef532391-1051-58fe-bb4c-bacc32aad73a", "439b9d3a-821c-5600-b400-5736ca8985fa",
    "babb28b5-6841-5b39-8f03-60ede5a24549",
}
GROUND_UUID = "44753f7d-be74-5116-bbe6-cb93386bd923"


def verify_preparation(source, prepared, record):
    expected = without_fill(source)
    names = {str(n[1]): str(n[2]) for n in children(expected, "net")}
    removed = [n for n in children(expected, "segment") if str(first(n, "uuid")[1]) in RETIRED]
    assert len(removed) == 9 and record["retired_copper_uuids"] == sorted(RETIRED)
    assert removed == record["retired_nodes"]
    assert all(names[str(first(n, "net")[1])] == "/CODEC/DRIVER_SETTLE_READY"
               and first(n, "layer")[1] == "F.Cu" and float(first(n, "width")[1]) == .2 for n in removed)
    expected = [n for n in expected if n not in removed]
    table = first(expected, "layers")
    assert [n[1] for n in table[1:] if n[1].endswith(".Cu")] == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    bottom = next(i for i, n in enumerate(table) if isinstance(n, list) and n[1] == "B.Cu")
    table[bottom:bottom] = [[a(3), "In3.Cu", a("signal")], [a(4), "In4.Cu", a("power")]]
    zones = children(expected, "zone")
    keepouts = [(i, z) for i, z in enumerate(zones) if children(z, "keepout")]
    assert len(keepouts) == 19
    extended = []
    for i, zone in keepouts:
        layers = first(zone, "layers")
        before = layers[1:]
        assert all(n in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu") for n in before)
        layers.extend(["In3.Cu", "In4.Cu"])
        extended.append(dict(zone_index=i, old_layers=before, new_layers=layers[1:]))
    assert record["extended_rule_area_layers"] == extended
    grounds = [z for z in zones if not children(z, "keepout")]
    assert len(grounds) == 1 and first(grounds[0], "layer")[1] == "In1.Cu"
    assert names[str(first(grounds[0], "net")[1])] == "AGND"
    extra = copy.deepcopy(grounds[0])
    first(extra, "layer")[1] = "In4.Cu"
    first(extra, "uuid")[1] = GROUND_UUID
    expected.append(extra)
    assert without_fill(prepared) == expected, "Preparation changed undeclared geometry, layers, copper or authored keepouts"
    assert record["added_ground_zone_uuid"] == GROUND_UUID
    assert record["additional_copper_layers"] == ["In3.Cu", "In4.Cu"]
    assert float(first(first(expected, "general"), "thickness")[1]) == record["nominal_board_thickness_mm"] == 1.6
    assert not record["physical_stack_material_cost_and_process_accepted"] and not record["fabrication_released"]


def verify_native_pads(original, current):
    def key(p):
        return p["ref"], p["pin"], tuple(p["position_mm"])

    old = {key(p): p for p in original["objects"]}
    new = {key(p): p for p in current["objects"]}
    assert len(old) == len(new) == len(original["objects"]) == len(current["objects"]) == 930
    assert old.keys() == new.keys()
    assert current["copper_layers"] == LAYERS
    inner_lands = 0
    for k, p in old.items():
        q = new[k]
        assert all(p[f] == q[f] for f in ("kind", "net", "drill_mm", "npth")), "Native land identity or drill changed"
        expected = copy.deepcopy(p["layers"])
        if "In1.Cu" in expected:
            assert p["drill_mm"] != [0, 0]
            expected["In3.Cu"] = expected["In4.Cu"] = expected["In1.Cu"]
            inner_lands += 1
        assert q["layers"] == expected, "Existing copper lands changed or new inner annuli differ"
    return inner_lands


def verify_fill(path, authored, filled_name, export_name, report):
    filled = path / filled_name
    exported = path / export_name
    assert sha(filled) == report["filled_PCB_sha256"] and sha(exported) == report["native_export_sha256"]
    board = read_sexpr(filled.read_text())
    assert without_fill(board) == without_fill(authored), "Native fill changed authored geometry"
    native = read_sexpr(exported.read_text())
    zones = [z for z in children(board, "zone") if not children(z, "keepout")]
    actual = {str(first(z, "uuid")[1]): children(z, "filled_polygon") for z in children(native, "zone") if not children(z, "keepout")}
    assert len(zones) == len(actual) == 2
    assert {first(z, "layer")[1] for z in zones} == {"In1.Cu", "In4.Cu"}
    areas = {}
    for z in zones:
        fills = children(z, "filled_polygon")
        assert fills and fills == actual[str(first(z, "uuid")[1])]
        polygons = [Polygon([tuple(map(float, p[1:3])) for p in children(first(f, "pts"), "xy")]).buffer(0) for f in fills]
        area = unary_union(polygons).area
        assert area > 7800 and first(z, "net_name")[1] == "AGND"
        areas[first(z, "layer")[1]] = round(area, 6)
    return areas


def check():
    names = ["preparation-record.json", "prepared-refill.json", "prepared-native-inputs.json",
             "distribution-construction.json", "native-refill.json", "current-native-pads.json"]
    reports = {name: json.loads((OUT / name).read_text()) for name in names}
    for r in reports.values():
        verify_hashes(r["source_sha256"])
        assert not r["fabrication_released"]
    source = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    prepared_path = OUT / "prepared-input.kicad_pcb"
    prepared = read_sexpr(prepared_path.read_text())
    record = reports["preparation-record.json"]
    assert sha(prepared_path) == record["authored_PCB_sha256"]
    verify_preparation(source, prepared, record)
    prepared_fill = reports["prepared-refill.json"]
    assert prepared_fill["native_copper_layer_count"] == 6
    capture = reports["prepared-native-inputs.json"]
    assert capture["layer_count"] == 6 and capture["copper_layers"] == LAYERS
    assert capture["native_uncapped_opens"] == 204
    before = verify_fill(OUT, prepared, "prepared-refilled.kicad_pcb", "prepared-native-export.kicad_pcb", prepared_fill)
    authored = read_sexpr((OUT / "distribution-input.kicad_pcb").read_text())
    after = verify_fill(OUT, authored, "audio_core.kicad_pcb", "native-refill-export.kicad_pcb", reports["native-refill.json"])
    old_pads = json.loads((SOURCE / "current-native-pads.json").read_text())
    verify_hashes(old_pads["source_sha256"])
    lands = verify_native_pads(old_pads, reports["current-native-pads.json"])
    for p in SOURCE.iterdir():
        if p.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or p.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            assert sha(p) == sha(OUT / p.name)
    for p in (SOURCE / "libraries").rglob("*"):
        if p.is_file():
            assert sha(p) == sha(OUT / p.relative_to(SOURCE))
    return dict(source_sha256=relative_hashes([Path(__file__), SOURCE / "audio_core.kicad_pcb", SOURCE / "current-native-pads.json"]+[OUT / n for n in names]),
                scope="layer preparation, retained geometry, native pads and native fill binding",
                copper_layers=LAYERS, authored_keepouts_extended_without_polygon_changes=19,
                only_retired_copper_segments=9, all_unretired_copper_footprints_and_outline_exact=True,
                native_pads_checked=930, through_hole_lands_extended_to_new_layers=lands,
                prepared_ground_area_mm2=before, routed_ground_area_mm2=after,
                physical_stack_material_cost_and_process_accepted=False,
                added_control_route_policy_independently_audited=False,
                electrical_performance_qualified=False, PCB_routed=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check()
    p = OUT / "preparation-retention-review.json"
    if args.check:
        assert result == json.loads(p.read_text())
    else:
        with p.open("x") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    print("Six-layer preparation replayed; 19 keepouts / 930 native pads / both filled ground planes checked")
