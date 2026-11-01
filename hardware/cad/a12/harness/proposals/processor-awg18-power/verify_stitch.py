"""Independent exact-object preservation and native proof for six power stitches."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def run():
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    w = ROOT / "stitch_trial"
    a = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    b = read_sexpr((w / "processor_carrier.kicad_pcb").read_text())
    before = {str(first(v, "uuid")[1]): sexpr(v) for v in children(a, "via")}
    after = {str(first(v, "uuid")[1]): sexpr(v) for v in children(b, "via")}
    added = set(after) - set(before)
    assert len(added) == 6
    assert all(after[k] == v for k, v in before.items())
    assert [sexpr(n) for n in a if not isinstance(n, list) or not n or n[0] != "via"] == [
        sexpr(n) for n in b if not isinstance(n, list) or not n or n[0] != "via"
    ]
    sites = set()
    for v in children(b, "via"):
        if str(first(v, "uuid")[1]) not in added:
            continue
        assert str(first(v, "net")[-1]).lstrip("/") == "5V_DIG"
        assert float(first(v, "size")[1]) == 0.6 and float(first(v, "drill")[1]) == 0.3
        sites.add(tuple(map(float, first(v, "at")[1:3])))
    assert sites == {(117, 111), (125, 113), (127, 115), (133, 115), (137, 119), (145, 117)}
    pa, na = netlist(ROOT / "generated/netlist.xml")
    pb, nb = netlist(w / "generated/netlist.xml")
    assert na == nb and set(pa) == set(pb)
    native = json.loads((w / "generated/native.json").read_text())
    assert native["candidate_pcb_sha256"] == sha(w / "processor_carrier.kicad_pcb")
    assert all(type(v) is int and v == 0 for v in native["counts"].values())
    report = dict(
        source_three_fill_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        candidate_pcb_sha256=sha(w / "processor_carrier.kicad_pcb"),
        actual_filled_pcb_sha256=sha(w / "generated/filled.kicad_pcb"),
        exact_new_5v_via_sites_native_mm=sorted(sites),
        all_original_objects_parts_filter_traces_and_pin_maps_unchanged=True,
        component_count=len(na),
        native_counts=native["counts"],
        new_ground_plane_voids_require_actual_reextraction=True,
        stackup_and_material_selected=False,
        ampacity_and_noise_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (w / "generated/preservation-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report)
    return report


if __name__ == "__main__":
    run()
