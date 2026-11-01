"""Independent native ear/pad/package and exact-parent preservation proof."""

import csv
import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18-power/stitch_trial"
REPO = ROOT.parents[5]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(fp):
    return next(p[2] for p in children(fp, "property") if p[1] == "Reference")


def run():
    board = ROOT / "processor_carrier.kicad_pcb"
    old = read_sexpr((SOURCE / "processor_carrier.kicad_pcb").read_text())
    new = read_sexpr(board.read_text())
    oldfps = {ref(f): sexpr(f) for f in children(old, "footprint")}
    newfps = {ref(f): sexpr(f) for f in children(new, "footprint")}
    assert set(newfps) - set(oldfps) == {"J13"}
    assert all(newfps[k] == v for k, v in oldfps.items())
    allowed = {"footprint", "zone", "gr_line"}
    assert [sexpr(q) for q in old if not isinstance(q, list) or not q or q[0] not in allowed] == [
        sexpr(q) for q in new if not isinstance(q, list) or not q or q[0] not in allowed
    ]
    for tag in ["zone", "gr_line"]:
        before = {str(first(q, "uuid")[1]): sexpr(q) for q in children(old, tag)}
        after = {str(first(q, "uuid")[1]): sexpr(q) for q in children(new, tag)}
        for k, v in before.items():
            original = next(q for q in children(old, tag) if str(first(q, "uuid")[1]) == k)
            if tag == "gr_line" and first(original, "layer")[1] == "Edge.Cuts":
                continue
            assert after[k] == v, (tag, k, "Original object changed")
    fp = next(f for f in children(new, "footprint") if ref(f) == "J13")
    assert first(fp, "layer")[1] == "F.Cu"
    assert list(map(float, first(fp, "at")[1:3])) == [258, 158]
    assert fp[1] == "RMX_Carrier:AWG18_Solder_2x1_P4mm_D2p2"
    pins = {}
    for p in children(fp, "pad"):
        pin = str(p[1])
        assert pin in ["1", "2"]
        assert p[2:4] == ["thru_hole", "circle"]
        assert list(map(float, first(p, "size")[1:])) == [3.4, 3.4]
        assert float(first(p, "drill")[1]) == 2.2
        net = str(first(p, "net")[-1]).lstrip("/")
        assert net == ("5V_DIG" if pin == "1" else "AGND")
        a = list(map(float, first(p, "at")[1:3]))
        pins[pin] = dict(
            net=net,
            native_xy_mm=[258 + a[0], 158 + a[1]],
            world_xy_mm=[188 + a[0], 100 + a[1]],
            nominal_land_mm=3.4,
            nominal_finished_bore_mm=2.2,
        )
    pp, np = netlist(SOURCE / "generated/netlist.xml")
    pn, nn = netlist(ROOT / "generated/netlist.xml")
    assert len(pn) == 77 and len(pp) == 76
    assert set(nn) - set(np) == {"J13"} and nn["J13"] == {"1": "5V_DIG", "2": "AGND"}
    assert all(nn[k] == v for k, v in np.items())
    oldparts = {p["ref"]: p for p in json.loads((SOURCE / "components.json").read_text())}
    newparts = {p["ref"]: p for p in json.loads((ROOT / "components.json").read_text())}
    assert all(newparts[k] == v for k, v in oldparts.items())
    assert set(newparts) - set(oldparts) == {"J13"}
    with (SOURCE / "bom.csv").open(newline="") as f:
        before = list(csv.DictReader(f))
    with (ROOT / "bom.csv").open(newline="") as f:
        after = list(csv.DictReader(f))
    assert after[:-1] == before and after[-1]["Reference"] == "J13"
    native = json.loads((ROOT / "generated/native.json").read_text())
    assert native["candidate_pcb_sha256"] == sha(board)
    assert all(type(v) is int and v == 0 for v in native["counts"].values())
    for group in ["source_sha256", "artifact_sha256"]:
        for name, digest in native[group].items():
            assert sha(REPO / name) == digest, ("Stale native evidence", name)
    outline = [(100, 100), (250, 100), (250, 153), (264, 153), (264, 165), (100, 165)]
    edges = {
        tuple(map(float, first(g, "start")[1:3])): tuple(map(float, first(g, "end")[1:3]))
        for g in children(new, "gr_line")
        if first(g, "layer")[1] == "Edge.Cuts"
    }
    assert edges == dict(zip(outline, outline[1:] + outline[:1]))
    report = dict(
        source_parent_sha256=sha(SOURCE / "processor_carrier.kicad_pcb"),
        candidate_pcb_sha256=sha(board),
        actual_filled_pcb_sha256=sha(ROOT / "generated/filled.kicad_pcb"),
        native_counts=native["counts"],
        original_76_pin_maps_parts_traces_poses_quietfilters_and_ground_zone_preserved=True,
        component_count=77,
        actual_J13_pads=pins,
        native_outline_mm=outline,
        world_outline_mm=[[x - 70, y - 58] for x, y in outline],
        world_ear_bbox_mm=[180, 95, 194, 107],
        pad_copper_to_lower_board_edge_mm=1.3,
        drill_to_lower_board_edge_mm=1.9,
        nominal_courtyard_to_lower_edge_mm=1.05,
        new_bare_pad_courtyard_world_bbox_mm=[186.05, 98.05, 189.95, 105.95],
        old_H4_head_world_bbox_from_root_mm=[173.2, 100.2, 178.8, 105.8],
        nominal_J13_courtyard_to_H4_head_X_gap_mm=7.25,
        source_input_force_and_return_pins="J13.1B/5V_DIG and J13.2B/AGND",
        shared_input_current_target_a=2.4,
        unassigned_other_branches_or_reserve_a=0.636,
        selected_stackup_accepted=False,
        current_distribution_ampacity_noise_and_thermal_qualified=False,
        root_native_ear_body_wire_collision_check_pending=True,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated/package-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()
