"""Independent native-source and raw-report audit of the sealed real R1 repair."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
BASE = REPO / "hardware/cad/a12/harness/proposals"
OLD = BASE / "processor-awg18-ear-fanout-j29-central"
NEW = BASE / "processor-awg18-ear-fanout-j29-central-r1"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def footprints(tree):
    return {
        next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
        for f in children(tree, "footprint")
    }


def maps(p):
    tree = ET.parse(p)
    result = {}
    for net in tree.findall("./nets/net"):
        for node in net.findall("node"):
            key = (node.attrib["ref"], node.attrib["pin"])
            assert key not in result
            result[key] = net.attrib["name"]
    return result


def main():
    handoff = read(NEW / "handoff.json")
    assert len(handoff["files_sha256"]) == 59
    for n, h in handoff["files_sha256"].items():
        assert sha(NEW / n) == h, n
    old = read_sexpr((OLD / "processor_carrier.kicad_pcb").read_text())
    new = read_sexpr((NEW / "processor_carrier.kicad_pcb").read_text())
    of, nf = footprints(old), footprints(new)
    assert len(of) == len(nf) == 88 and set(of) == set(nf)
    assert [n for n in sorted(of) if of[n] != nf[n]] == ["R1"]
    assert list(map(float, first(nf["R1"], "at")[1:])) == [180, 140, 90]
    pads = children(nf["R1"], "pad")
    assert len(pads) == 2 and all(p[2:4] == ["smd", "rect"] for p in pads)
    assert all(list(map(float, first(p, "size")[1:])) == [1.65, 3.68] for p in pads)
    centres = sorted(float(first(p, "at")[1]) for p in pads)
    assert math.isclose(centres[1] - centres[0] - 1.65, 4.06, abs_tol=1e-12)
    # Compare complete remaining board-level objects, including all configuration,
    # zones, outline and locked routing. Only own force segments/vias may differ.
    def remainder(tree):
        return [x for x in tree[1:] if x[0] not in ["footprint", "segment", "via"]]

    assert remainder(old) == remainder(new)
    delta = {}
    for kind in ["segment", "via"]:
        a = Counter(json.dumps(x) for x in children(old, kind))
        b = Counter(json.dumps(x) for x in children(new, kind))
        removed = [json.loads(x) for x in (a - b).elements()]
        added = [json.loads(x) for x in (b - a).elements()]
        assert all(
            first(x, "net")[1] in ["/5V_DIG", "/SEED_VIN", "5V_DIG", "SEED_VIN"] for x in removed + added
        )
        delta[kind] = dict(removed=len(removed), added=len(added))
    assert delta == {"segment": {"removed": 4, "added": 8}, "via": {"removed": 0, "added": 5}}
    oldpins = maps(OLD / "generated/netlist.xml")
    newpins = maps(NEW / "generated/netlist.xml")
    assert oldpins == newpins
    assert len({x[0] for x in newpins}) == 79
    drc = read(NEW / "generated/drc.json")
    erc = read(NEW / "generated/erc.json")
    assert not drc["violations"] and not drc["unconnected_items"] and not drc["schematic_parity"]
    assert not [v for s in erc["sheets"] for v in s["violations"]]
    assert drc["ignored_checks"] == read(OLD / "generated/drc.json")["ignored_checks"]
    assert erc["ignored_checks"] == read(OLD / "generated/erc.json")["ignored_checks"]
    assert sha(NEW / "processor_carrier.kicad_pcb") == handoff["candidate_pcb_sha256"]
    assert sha(NEW / "generated/filled.kicad_pcb") == handoff["filled_pcb_sha256"]
    assert not handoff["physical_qualified"] and not handoff["fabrication_released"]
    result = dict(
        scope=__doc__,
        handoff_sha256=sha(NEW / "handoff.json"),
        packet_hashes_checked=59,
        unchanged_complete_footprints=87,
        unchanged_schematic_component_pinmaps=79,
        unchanged_net_node_pairs=len(newpins),
        board_top_level_except_own_routes_and_R1_exact=True,
        own_force_route_delta=delta,
        manufacturer_land_size_mm=[1.65, 3.68],
        manufacturer_inner_gap_mm=4.06,
        raw_ERC_DRC_opens_parity_counts_zero=True,
        configured_ignored_ERC_keys_unchanged=[x["key"] for x in erc["ignored_checks"]],
        configured_ignored_DRC_keys_unchanged=[x["key"] for x in drc["ignored_checks"]],
        new_native_commands_run=False,
        existing_configured_checks_only=True,
        independent_saved_source_review_passed=True,
        fresh_PDN_or_whole_unit_MCAD_reviewed_here=False,
        physical_qualified=False,
        fabrication_released=False,
        audit_script_sha256=sha(Path(__file__)),
    )
    (ROOT / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
