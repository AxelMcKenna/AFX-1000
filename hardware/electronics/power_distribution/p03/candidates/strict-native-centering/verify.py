"""Actual private strict-native P03 checkpoint; no physical acceptance."""

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]
sys.path.insert(0, str(REPO))
from hardware.electronics.common.netlists import netlist  # noqa: E402 - standalone repository bootstrap
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr  # noqa: E402


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def identities():
    old = read_sexpr((ROOT / "sources/db83/power_p03.kicad_pcb").read_text())
    new = read_sexpr((ROOT / "power_p03.kicad_pcb").read_text())

    def objects(t, k):
        return {str(first(n, "uuid")[1]): sexpr(n) for n in children(t, k)}

    f0, f1 = objects(old, "footprint"), objects(new, "footprint")
    v0, v1 = objects(old, "via"), objects(new, "via")
    fp = [k for k in set(f0) | set(f1) if f0.get(k) != f1.get(k)]
    via = [k for k in set(v0) | set(v1) if v0.get(k) != v1.get(k)]
    assert not fp and not via
    assert sexpr(first(old, "setup")) == sexpr(first(new, "setup"))
    assert sexpr(first(old, "layers")) == sexpr(first(new, "layers"))
    edges0 = [
        sexpr(n)
        for n in old
        if isinstance(n, list) and n and children(n, "layer") and first(n, "layer")[1] == "Edge.Cuts"
    ]
    edges1 = [
        sexpr(n)
        for n in new
        if isinstance(n, list) and n and children(n, "layer") and first(n, "layer")[1] == "Edge.Cuts"
    ]
    assert edges0 == edges1
    filled = Counter(
        str(first(v, "filling")[1]) if children(v, "filling") else "native_metadata_unspecified"
        for v in children(new, "via")
    )
    capped = Counter(
        str(first(v, "capping")[1]) if children(v, "capping") else "native_metadata_unspecified"
        for v in children(new, "via")
    )
    return dict(
        actual_FP_count=len(f1),
        all_original_complete_FPs_exact=True,
        actual_via_count=len(v1),
        all_original_complete_vias_exact=True,
        board_setup_layer_stack_and_outline_exact=True,
        via_filling_metadata=dict(filled),
        via_capping_metadata=dict(capped),
        metadata_is_NOT_fabricator_process_acceptance=True,
        physical_qualified=False,
    )


def native():
    assert not (ROOT / "handoff.json").exists()
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/rmx-kicad-config",
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    cli = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    board = ROOT / "power_p03.kicad_pcb"
    before = sha(board)
    commands = []
    for name, args, target in [
        (
            "drc",
            [
                "pcb",
                "drc",
                "--all-track-errors",
                "--schematic-parity",
                "--severity-all",
                "--refill-zones",
                "--format",
                "json",
                "--output",
                str(ROOT / "generated/drc.json"),
            ],
            board,
        ),
        (
            "erc",
            [
                "sch",
                "erc",
                "--format",
                "json",
                "--severity-all",
                "--output",
                str(ROOT / "generated/erc.json"),
            ],
            ROOT / "power_p03.kicad_sch",
        ),
        (
            "netlist",
            [
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadxml",
                "--output",
                str(ROOT / "generated/netlist.xml"),
            ],
            ROOT / "power_p03.kicad_sch",
        ),
    ]:
        cmd = [cli, *args, str(target)]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        (ROOT / "generated" / f"{name}.log").write_text(p.stdout + p.stderr)
        commands.append(dict(command=cmd, returncode=p.returncode))
        assert p.returncode == 0, name
    assert sha(board) == before
    py = "/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9"
    cmd = [
        py,
        str(ROOT / "sources/native_uncapped.py"),
        str(ROOT / "sources/db83/power_p03.kicad_pcb"),
        str(board),
        str(ROOT / "generated/drc.json"),
        str(ROOT / "generated/uncapped.json"),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    (ROOT / "generated/uncapped.log").write_text(p.stdout + p.stderr)
    commands.append(dict(command=cmd, returncode=p.returncode))
    assert p.returncode == 0
    d = json.loads((ROOT / "generated/drc.json").read_text())
    e = json.loads((ROOT / "generated/erc.json").read_text())
    u = json.loads((ROOT / "generated/uncapped.json").read_text())
    assert "ignored_checks" in d and not d["ignored_checks"]
    assert not d["violations"] and not d["unconnected_items"] and not d["schematic_parity"]
    assert not [v for s in e["sheets"] for v in s["violations"]]
    assert u["uncapped_unconnected_count"] == 0
    actual, pins = netlist(ROOT / "generated/netlist.xml")
    parts = json.loads((ROOT / "components.json").read_text())
    m = []
    for c in parts:
        if actual[c["ref"]].findtext("value") != c["part"]:
            m.append([c["ref"], "value"])
        for pin in c["pins"]:
            value = pins[c["ref"]][pin["number"]]
            if pin["net"] is None:
                if not value.startswith("unconnected-"):
                    m.append([c["ref"], pin["number"], value])
            elif value != pin["net"]:
                m.append([c["ref"], pin["number"], value, pin["net"]])
    assert not m
    identity = identities()
    (ROOT / "generated/identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    result = dict(
        scope="NEW privateP03 strictnativecentering, all5previouslyignored checks explicitlyERROR",
        pcb_sha256=sha(board),
        schematic_sha256=sha(ROOT / "power_p03.kicad_sch"),
        native_counts=dict(ERC=0, DRC=0, warnings=0, parity=0, opens=0, uncapped_opens=0),
        ignored_checks=[],
        actual_native_components=len(actual),
        native_pin_value_mismatches=m,
        native_commands=commands,
        all_original_FPs_vias_and_outline_preserved=True,
        known_POWER_RUN_loaded_threshold_defect_UNREPAIRED=True,
        AX02_not_integrated=True,
        old_literal_AUX_checker_not_claimed_pass=True,
        new_six_local_front_paths="six-front-paths-new.json",
        old_ground_thermal_endpoint_results_not_inherited=True,
        physical_qualified=False,
        fabricator_approved=False,
        release_ready=False,
    )
    (ROOT / "generated/current-native.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    native()
