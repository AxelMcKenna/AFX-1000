"""Independent native/source/topology review of the E19 direct-wire proposal."""

import argparse
import copy
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from ..generate import REPO, sha

SOURCE = REPO / "hardware/electronics/processor_carrier"


def footprints(tree):
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }


def check(workspace):
    pcb = workspace / "processor_carrier.kicad_pcb"
    source_pcb = SOURCE / pcb.name
    source, candidate = read_sexpr(source_pcb.read_text()), read_sexpr(pcb.read_text())
    left, right = footprints(source), footprints(candidate)
    assert left.keys() == right.keys()
    assert [ref for ref in left if left[ref] != right[ref]] == ["J1"]

    def nonfootprint(t):
        return [n for n in t if not (isinstance(n, list) and n and n[0] == "footprint")]

    assert nonfootprint(source) == nonfootprint(candidate), "Non-J1 board material/routing changed"
    f = right["J1"]
    assert f[1] == "RMX_Carrier:AWG18_Solder_2x1_P4mm_D2p2"
    assert first(f, "at") == first(left["J1"], "at") and first(f, "layer")[1] == "F.Cu"
    source_pins = {
        ref: {str(p[1]): str(first(p, "net")[-1]).lstrip("/") for p in children(fp, "pad")}
        for ref, fp in left.items()
        if not ref.startswith("H")
    }
    candidate_pins = {
        ref: {str(p[1]): str(first(p, "net")[-1]).lstrip("/") for p in children(fp, "pad")}
        for ref, fp in right.items()
        if not ref.startswith("H")
    }
    assert candidate_pins == source_pins
    pads = []
    for p in children(f, "pad"):
        pin = str(p[1])
        assert p[2:4] == ["thru_hole", "circle"]
        assert first(p, "layers")[1:] == ["*.Cu", "*.Mask"]
        assert float(first(p, "drill")[1]) == 2.2
        assert list(map(float, first(p, "size")[1:3])) == [3.4, 3.4]
        xy = transform(f, first(p, "at")[1:3])
        expected = [114, 105 if pin == "1" else 109]
        assert list(xy) == expected
        pads.append(
            dict(
                pin=pin,
                net=candidate_pins["J1"][pin],
                world_mm=[xy[0] - 70, xy[1] - 58, 8.1],
                finished_bore_nominal_mm=2.2,
            )
        )
    sch = workspace / "processor_carrier.kicad_sch"
    original_sch = read_sexpr((SOURCE / sch.name).read_text())
    new_sch = copy.deepcopy(read_sexpr(sch.read_text()))

    def symbol(t):
        return next(
            s
            for s in children(t, "symbol")
            if any(p[1:3] == ["Reference", "J1"] for p in children(s, "property"))
        )

    before, after = symbol(original_sch), symbol(new_sch)
    for key in ["Value", "Footprint"]:
        old = next(p for p in children(before, "property") if p[1] == key)
        new = next(p for p in children(after, "property") if p[1] == key)
        new[2] = old[2]
    assert new_sch == original_sch, "Schematic changed beyond J1 value/footprint"
    out = workspace / "generated"
    components, nets = netlist(out / "netlist.xml")
    assert nets == source_pins, "Fresh exported topology differs from original native PCB"
    assert len(components) == 76
    native_file = out / "native.json"
    native = json.loads(native_file.read_text())
    assert native["candidate_pcb_sha256"] == sha(pcb)
    for key in ["source_sha256", "artifact_sha256"]:
        assert all(sha(REPO / n) == h for n, h in native[key].items())
    drc = json.loads((out / "drc.json").read_text())
    erc = json.loads((out / "erc.json").read_text())
    assert all(not drc[k] for k in ["violations", "unconnected_items", "schematic_parity"])
    assert erc["sheets"] and all(not s["violations"] for s in erc["sheets"])
    hashes = {**native["source_sha256"], **native["artifact_sha256"]}
    for p in [
        Path(__file__),
        source_pcb,
        SOURCE / sch.name,
        native_file,
        REPO / "hardware/electronics/common/netlists.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    result = dict(
        scope=__doc__,
        source_sha256=hashes,
        candidate_pcb_sha256=sha(pcb),
        canonical_pcb_sha256=sha(source_pcb),
        only_changed_footprint="J1",
        all_other_native_board_nodes_identical=True,
        all_76_component_pin_maps_preserved=True,
        only_schematic_J1_value_footprint_changed=True,
        actual_pads=pads,
        raw_ERC_DRC_parity_opens_all_zero=True,
        current_path_resistance_qualified=False,
        physical_fit_verified=False,
        fabrication_released=False,
    )
    (out / "independent-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Independent E19 topology/native review passed", sha(pcb))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    check(parser.parse_args().workspace.resolve())
