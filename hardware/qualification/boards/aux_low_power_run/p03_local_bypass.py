"""Give U201 a direct front-side bypass and move only the new return branch."""

import hashlib
import json
import uuid
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.power_distribution.p03.route import coded, named

WORK = Path(__file__).resolve().parents[4] / "hardware/electronics/power_distribution/p03/candidates/ax03-run-transmitter"


def run():
    source = WORK / "generated/routes-strict-01/power_p03.kicad_pcb"
    output = WORK / "generated/local-bypass"
    assert not output.exists()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    tree = read_sexpr(source.read_text())
    parent = read_sexpr((WORK.parent / "strict-native-centering/power_p03.kicad_pcb").read_text())
    original = {str(first(n, "uuid")[1]) for kind in ("segment", "via") for n in children(parent, kind)}
    remove = {"b9692431-172e-5ad9-a67a-5ff7579b37e1", "bd41b3de-dee0-5bcc-bd37-ba97f85386c8"}
    assert not remove & original
    displaced = [n for n in children(tree, "segment") if str(first(n, "uuid")[1]) in remove]
    assert len(displaced) == 2 and all(first(n, "net")[1] == "/AGND" for n in displaced)
    for n in displaced:
        tree.remove(n)
    tree = coded(tree)
    codes = {str(n[2]).lstrip("/"): int(n[1]) for n in children(tree, "net")}
    for net, start, end, width in (
        ("V2V5_AUX", (101.75, 121.275), (103.4, 121), .25),
        ("AGND", (101.75, 119.725), (100.95, 118.9), .25),
    ):
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:P03:AX03:bypass:{before}:{net}"))
        tree.append(read_sexpr(f'(segment (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) (width {width}) (layer "F.Cu") (net {codes[net]}) (uuid "{uid}"))'))
    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:P03:AX03:bypass:{before}:GNDvia"))
    tree.append(read_sexpr(f'(via (at 100.95 118.9) (size .6) (drill .25) (layers "F.Cu" "B.Cu") (net {codes["AGND"]}) (uuid "{uid}"))'))
    output.mkdir()
    pcb = output/source.name
    pcb.write_text(sexpr(named(tree))+"\n")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    (output/"bypass.json").write_text(json.dumps(dict(source_pcb_sha256=before,
        output_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        displaced_only_new_return_segments=[sexpr(n) for n in displaced],
        original_strict_source_copper_unchanged=True, supervisor_cap_supply_link_layer="F.Cu",
        new_ground_via_mm=[100.95, 118.9, .6, .25], native_refill_and_checks_pending=True,
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")


if __name__ == "__main__":
    run()
