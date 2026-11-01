"""Verify a complete isolated repair against actual native bytes, not a pass label."""

import hashlib
import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr
from .construction import direct_ep_inventory
from .spec import REPO


def validate(root, report=None):
    root = Path(root).resolve()
    report = report or json.loads((root / "generated/current-native.json").read_text())

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    pcb = root / "power_p03.kicad_pcb"
    assert digest(pcb) == report["pcb_sha256"], "Repair native PCB is stale"
    for group in ("source_sha256", "artifact_sha256"):
        assert report[group], "Missing native source/artifact binding"
        for relative, expected in report[group].items():
            path = (REPO / relative).resolve()
            assert path.is_relative_to(REPO.resolve()), "Evidence escapes repository"
            assert digest(path) == expected, f"Stale repair evidence: {relative}"
    required_sources = {
        root / name
        for name in ("power_p03.kicad_pcb", "power_p03.kicad_sch", "power_p03.kicad_pro", "construction.json")
    }
    required_artifacts = {
        root / "generated" / ("complete-scratch-" + name)
        for name in ("erc.json", "drc.json", "netlist.xml", "verification.json")
    }
    assert required_sources <= {(REPO / p).resolve() for p in report["source_sha256"]}
    assert required_artifacts <= {(REPO / p).resolve() for p in report["artifact_sha256"]}
    proof = json.loads((root / "generated/complete-scratch-verification.json").read_text())
    assert proof["pcb_sha256"] == report["pcb_sha256"], "Native proof belongs to another PCB"
    raw = json.loads((root / "generated/complete-scratch-drc.json").read_text())
    erc = json.loads((root / "generated/complete-scratch-erc.json").read_text())
    counts = dict(
        ERC=sum(len(s["violations"]) for s in erc["sheets"]),
        DRC=len(raw["violations"]),
        parity=len(raw.get("schematic_parity", [])),
        opens=len(raw["unconnected_items"]),
    )
    assert counts == report["native_counts"] == dict(ERC=0, DRC=0, parity=0, opens=0)
    assert {k: proof[k] for k in counts} == counts
    assert report["native_electrically_closed"] is True
    for key in (
        "thermal_guardbanded_qualified",
        "coupled_ground_and_endpoint_accepted",
        "fabricator_dfm_approved",
        "physical_qualified",
        "release_ready",
    ):
        assert report[key] is False, "Native closure cannot qualify physical performance"
    tree = read_sexpr(pcb.read_text())
    assert direct_ep_inventory(tree)["implements_required_count_and_geometry"]
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    actual = []
    for via in children(tree, "via"):
        x, y = [float(v) - 100 for v in first(via, "at")[1:3]]
        if 25.5 <= x <= 27 and 19.25 <= y <= 20.75:
            assert names.get(str(first(via, "net")[1]), str(first(via, "net")[-1])).lstrip("/") == "AGND"
            assert abs(float(first(via, "size")[1]) - 0.70) < 1e-8
            assert abs(float(first(via, "drill")[1]) - 0.25) < 1e-8
            actual.append((round(x, 6), round(y, 6)))
    assert set(actual) == {(x, y) for x in (25.75, 26.25, 26.75) for y in (19.5, 20, 20.5)}
    assert len(actual) == 9
    return counts
