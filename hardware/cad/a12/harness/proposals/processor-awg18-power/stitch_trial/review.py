"""Independent source/native preservation review; permits exactly three added zones."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "processor-awg18"


def run():
    def h(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    a = read_sexpr((SOURCE / "processor_carrier.kicad_pcb").read_text())
    b = read_sexpr((ROOT / "processor_carrier.kicad_pcb").read_text())
    before = {str(first(z, "uuid")[1]): z for z in children(a, "zone")}
    after = {str(first(z, "uuid")[1]): z for z in children(b, "zone")}
    new = after.keys() - before.keys()
    assert len(new) == 3
    assert [sexpr(o) for o in a if not isinstance(o, list) or not o or o[0] != "zone"] == [
        sexpr(o) for o in b if not isinstance(o, list) or not o or o[0] != "zone"
    ]
    assert all(sexpr(z) == sexpr(after[k]) for k, z in before.items())
    expected = {"F.Cu", "B.Cu", "In2.Cu"}
    for k in new:
        z = after[k]
        assert str(first(z, "net")[-1]).lstrip("/") == "5V_DIG"
        expected.remove(first(z, "layer")[1])
        assert [(float(q[1]), float(q[2])) for q in first(first(z, "polygon"), "pts")[1:]] == [
            (111.5, 102.5),
            (149.5, 102.5),
            (149.5, 124.5),
            (111.5, 124.5),
        ]
    assert not expected
    pa, na = netlist(SOURCE / "generated/netlist.xml")
    pb, nb = netlist(ROOT / "generated/netlist.xml")
    assert na == nb and set(pa) == set(pb)
    native = json.loads((ROOT / "generated/native.json").read_text())
    assert not any(native["counts"].values())
    assert native["candidate_pcb_sha256"] == h(ROOT / "processor_carrier.kicad_pcb")
    for group in ["source_sha256", "artifact_sha256"]:
        for rel, digest in native[group].items():
            assert h(Path(__file__).resolve().parents[6] / rel) == digest, (
                rel,
                "stale native source/artifact",
            )
    report = dict(
        source_pcb_sha256=h(SOURCE / "processor_carrier.kicad_pcb"),
        candidate_pcb_sha256=h(ROOT / "processor_carrier.kicad_pcb"),
        actual_filled_pcb_sha256=h(ROOT / "generated/filled.kicad_pcb"),
        all_component_pin_maps_unchanged=True,
        component_count=len(na),
        all_original_native_nodes_unchanged=True,
        only_three_positive_zones_added=True,
        in1_ground_authored_geometry_unchanged=True,
        native_counts=native["counts"],
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated/preservation-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report)
    return report


if __name__ == "__main__":
    run()
