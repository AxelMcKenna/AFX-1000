"""Independently check the rear inlet pin contract and actual copper paths."""

import argparse
import json
import os
import subprocess
from pathlib import Path

from ...adc_driver.pcb.paths import graph, objects, reachable
from ...common.netlists import netlist
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr
from .generate import OUT, PROJECT, REPO, ROOT


def connected(tree, net, start, end, minimum_width):
    items = [o for o in objects(tree, net) if o["kind"] != "line" or 2 * o["r"] + 1e-9 >= minimum_width]
    source = [i for i, o in enumerate(items) if o.get("pad") == (start[0], str(start[1]))]
    target = [i for i, o in enumerate(items) if o.get("pad") == (end[0], str(end[1]))]
    assert len(source) == len(target) == 1, "Unexpected physical terminal multiplicity"
    assert target[0] in reachable(graph(items), source[0]), (
        "Actual copper disconnected or too narrow",
        net,
        start,
        end,
    )
    return dict(connected=True, minimum_segment_width_mm=minimum_width)


def check(cli):
    env = dict(
        os.environ,
        KICAD_CONFIG_HOME="/private/tmp/afx-inlet-kicad",
        KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        FONTCONFIG_FILE=str(REPO / "build-hardware/kicad-fonts.conf"),
    )
    commands = [
        [
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            str(OUT / "netlist.xml"),
            str(ROOT / (PROJECT + ".kicad_sch")),
        ],
        [
            "sch",
            "erc",
            "--format",
            "json",
            "--severity-all",
            "-o",
            str(OUT / "erc.json"),
            str(ROOT / (PROJECT + ".kicad_sch")),
        ],
        [
            "pcb",
            "drc",
            "--format",
            "json",
            "--severity-all",
            "--schematic-parity",
            "-o",
            str(OUT / "drc.json"),
            str(ROOT / (PROJECT + ".kicad_pcb")),
        ],
    ]
    for command in commands:
        result = subprocess.run([str(cli), *command], env=env, capture_output=True, text=True, check=True)
        (OUT / (command[0] + "-" + command[1] + ".log")).write_text(result.stdout + result.stderr)
    erc = json.loads((OUT / "erc.json").read_text())
    drc = json.loads((OUT / "drc.json").read_text())
    assert not any(s["violations"] for s in erc["sheets"]), "Native ERC findings"
    for key in ["violations", "unconnected_items", "schematic_parity"]:
        assert not drc[key], ("Native PCB findings", key, drc[key])
    parts, pins = netlist(OUT / "netlist.xml")
    assert set(parts) == {"J1", "J2", "J3", "F1", "S1"}, "Wrong inlet circuit variant"
    expected = {
        "J1": {"1": "DC_JACK", "2": "AGND"},
        "F1": {"1": "DC_JACK", "2": "DC_IN"},
        "J2": {"1": "DC_IN", "2": "AGND"},
        "J3": {"1": "SWITCH_SUPPLY", "2": "POWER_RUN", "3": "AGND"},
        "S1": {"1": "SWITCH_SUPPLY", "2": "POWER_RUN", "3": "AGND"},
    }
    for ref, ends in expected.items():
        for pin, net in ends.items():
            assert pins[ref][pin] == net, ("Inlet pin contract changed", ref, pin)
    assert pins["J1"]["3"].startswith("unconnected-"), "Jack switched terminal must stay unused"
    assert parts["F1"].findtext("value") == "0451006.MRL 6A 125V"
    assert parts["J2"].findtext("value") == "B2PS-VH(LF)(SN)"
    tree = read_sexpr((ROOT / (PROJECT + ".kicad_pcb")).read_text())
    paths = {}
    for net, start, end, width in [
        ("DC_JACK", ("J1", 1, 0), ("F1", 1, 0), 1.2),
        ("DC_IN", ("F1", 2, 0), ("J2", 1, 0), 1.2),
        ("AGND", ("J1", 2, 0), ("J2", 2, 0), 3.0),
        ("SWITCH_SUPPLY", ("S1", 1, 0), ("J3", 1, 0), 0.3),
        ("POWER_RUN", ("S1", 2, 0), ("J3", 2, 0), 0.3),
        ("AGND", ("S1", 3, 0), ("J3", 3, 0), 0.3),
    ]:
        paths[f"{start[0]}.{start[1]}->{end[0]}.{end[1]}"] = connected(tree, net, start, end, width)
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    # Conditional copper-only dissipation screen, separate from contact/fuse loss.
    # Terminal necks are included individually at their actual track widths.
    rho = 1.7241e-8 * (1 + 0.00393 * (85 - 20))
    copper = {}
    for net in ["DC_JACK", "DC_IN", "AGND"]:
        segments = [
            s
            for s in children(tree, "segment")
            if names[str(first(s, "net")[1])] == net and float(first(s, "width")[1]) >= 1.2
        ]
        resistance = 0
        for segment in segments:
            p, q = [tuple(map(float, first(segment, k)[1:3])) for k in ["start", "end"]]
            length = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 / 1000
            area = float(first(segment, "width")[1]) / 1000 * 0.00007
            resistance += rho * length / area
        copper[net] = resistance
    sources = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and "generated" not in p.parts and p.suffix not in {".pyc", ".kicad_prl"}
    ]
    sources += list((ROOT.parents[1] / "common").glob("*.py"))
    sources += [
        ROOT.parent / "components.json",
        ROOT.parent / "RMX_Input.pretty/PJ102AH_RearEdge_E23.kicad_mod",
        ROOT.parent / "RMX_Input.pretty/JS102011SAQN_RearEdge_E23.kicad_mod",
        ROOT.parent / "place.py",
        ROOT.parents[1] / "rail_disconnect/routing/check.py",
        ROOT.parents[1] / "adc_driver/pcb/paths.py",
        ROOT.parents[1] / "output_stage/check_placement.py",
        REPO / "tests/tooling/test_rear_inlet_revision2.py",
    ]
    report = dict(
        revision="E23I2",
        native_erc_violations=0,
        native_drc_violations=0,
        native_open_connections=0,
        schematic_parity_issues=0,
        independent_copper_connections=paths,
        conditional_copper_only_resistance_ohm=copper,
        conditional_copper_only_loss_at_4a_w=16 * sum(copper.values()),
        screen_excludes="Pads/terminal spreading, barrel/solder, jack/plug, fuse, connector/contact, cable resistance and current sharing; not a full path bound or thermal proof",
        candidate_stackup_accepted=False,
        physical_fit_verified=False,
        physical_electrical_verified=False,
        fault_coordination_qualified=False,
        fabrication_released=False,
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sorted(set(sources))},
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "E23I2: native ERC/DRC/parity/opens0; six independent copper paths checked; physical and fault qualification pending"
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", required=True, type=Path)
    check(p.parse_args().kicad_cli.resolve())
