"""Native E10 PCB contract/geometry checks; physical/audio qualification remains open."""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...common.netlists import netlist, number
from ...common.placement import footprint_root
from ...common.reports import sha
from ...common.sexpr import children, first, read_sexpr
from ...output_stage.check_placement import courtyard
from ...rail_disconnect.routing.check import copper_path
from ..verify import CONTRACT, EXPECTED
from .generate import MOUNTS, POSES, SIZE

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
OUT = ROOT / "generated"


def feedback_contract(tree):
    result = {}
    for net, a, b in [
        ("GAIN_FB_L", ("U1", 2, 0), ("R5", 1, 0)),
        ("GAIN_FB_L", ("U1", 2, 0), ("R6", 1, 0)),
        ("BUF_OUT_L", ("U1", 1, 0), ("R5", 2, 0)),
        ("GAIN_FB_R", ("U1", 6, 0), ("R12", 1, 0)),
        ("GAIN_FB_R", ("U1", 6, 0), ("R13", 1, 0)),
        ("BUF_OUT_R", ("U1", 7, 0), ("R12", 2, 0)),
    ]:
        length = copper_path(tree, net, a, b, 0.25)
        assert length <= 12, ("Feedback construction rule exceeded", net, a, b, length)
        result[f"{net}_{b[0]}"] = length
    return result


def inspect(tree, parts, pins):
    assert pins == CONTRACT, "Parent circuit pin contract changed"
    for ref, value in EXPECTED.items():
        assert abs(number(parts[ref].findtext("value")) / value - 1) < 1e-9, ref
    assert parts["U1"].findtext("value") == "OPA1656ID"
    assert parts["K1"].findtext("value") == "G6K-2F-Y DC5"
    expected = {c["ref"]: c for c in json.loads((PARENT / "components.json").read_text())}
    assert float(first(first(tree, "general"), "thickness")[1]) == 1.6
    corners = {
        tuple(map(float, first(line, tag)[1:3]))
        for line in children(tree, "gr_line")
        for tag in ("start", "end")
    }
    assert corners == {(100, 100), (100 + SIZE[0], 100), (100 + SIZE[0], 100 + SIZE[1]), (100, 100 + SIZE[1])}
    footprints = {}
    mounts = {}
    bounds = {}
    for f in children(tree, "footprint"):
        ref = next(p[2] for p in children(f, "property") if p[1] == "Reference")
        assert ref not in footprints and ref not in mounts, ("Duplicate footprint", ref)
        if ref.startswith("H"):
            pads = children(f, "pad")
            assert len(pads) == 1 and pads[0][2] == "np_thru_hole"
            assert float(first(pads[0], "drill")[1]) == 2.4
            mounts[ref] = tuple(round(float(v) - 100, 6) for v in first(f, "at")[1:3])
            continue
        assert ref in expected, ("Unexpected part", ref)
        assert f[1] == expected[ref]["footprint"], ("Footprint changed", ref)
        assert next(p[2] for p in children(f, "property") if p[1] == "Value") == parts[ref].findtext("value")
        actual = {str(p[1]): str(first(p, "net")[-1]).lstrip("/") for p in children(f, "pad")}
        assert actual == pins[ref], ("PCB pin mismatch", ref)
        pose = first(f, "at")
        x, y, angle, side = POSES[ref]
        assert [float(v) for v in pose[1:4]] == [100 + x, 100 + y, angle], ("Unexpected pose", ref)
        assert first(f, "layer")[1] == side + ".Cu"
        box = courtyard(f, side + ".CrtYd")
        assert box[0] >= 100 and box[1] >= 100 and box[2] <= 100 + SIZE[0] and box[3] <= 100 + SIZE[1], (
            "Body outside PCB",
            ref,
            box,
        )
        bounds[ref] = dict(side=side, courtyard_mm=box)
        footprints[ref] = f
    assert set(footprints) == set(expected), "Missing component"
    assert mounts == {f"H{i}": tuple(p) for i, p in enumerate(MOUNTS, 1)}, "Mounting contract changed"
    zones = children(tree, "zone")
    assert len(zones) == 4 and all(children(z, "keepout") for z in zones), "Missing fastener keepout"
    for zone in zones:
        keepout = first(zone, "keepout")
        assert all(first(keepout, key)[1] == "not_allowed" for key in ("tracks", "vias", "copperpour"))
    return bounds


def check(cli):
    OUT.mkdir(exist_ok=True)
    report_path = OUT / "verification.json"
    report_path.unlink(missing_ok=True)
    pcb = ROOT / "input_range.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    with tempfile.TemporaryDirectory(prefix="rmx-e10-pcb-check-") as folder:
        temp = Path(folder)
        for n in ["input_range.kicad_sch", "RMX_E10.kicad_sym", "sym-lib-table"]:
            shutil.copy2(PARENT / n, temp / n)
        for n in ["input_range.kicad_pcb", "input_range.kicad_pro", "fp-lib-table"]:
            shutil.copy2(ROOT / n, temp / n)
        shutil.copytree(ROOT / "RMX_Power.pretty", temp / "RMX_Power.pretty")
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )

        def run(*args):
            r = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, text=True)
            assert r.returncode == 0, (args, r.stdout, r.stderr)
            return r.stdout.strip()

        version = run("--version")
        run(
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            OUT / "netlist.xml",
            temp / "input_range.kicad_sch",
        )
        parts, pins = netlist(OUT / "netlist.xml")
        bodies = inspect(tree, parts, pins)
        paths = feedback_contract(tree) if children(tree, "segment") else {}
        run(
            "pcb",
            "drc",
            "--all-track-errors",
            "--schematic-parity",
            "--severity-all",
            "--format",
            "json",
            "-o",
            OUT / "drc.json",
            temp / "input_range.kicad_pcb",
        )
        native = json.loads((OUT / "drc.json").read_text())
        assert native["violations"] == [], (
            "Native DRC violations",
            [(v["type"], v.get("description")) for v in native["violations"][:20]],
        )
        assert native["schematic_parity"] == [], native["schematic_parity"]
        for name, layers in [
            ("top", "F.Cu,F.Silkscreen,Edge.Cuts"),
            ("bottom", "B.Cu,B.Silkscreen,Edge.Cuts"),
        ]:
            run(
                "pcb",
                "export",
                "svg",
                "--layers",
                layers,
                "--page-size-mode",
                "2",
                "--mode-single",
                "-o",
                OUT / (name + ".svg"),
                temp / "input_range.kicad_pcb",
            )
    count = len(native["unconnected_items"])
    sources = [
        p
        for p in ROOT.iterdir()
        if p.is_file() and p.suffix in (".py", ".md", ".json", ".kicad_pcb", ".kicad_pro")
    ]
    sources += [
        ROOT / "fp-lib-table",
        *sorted((ROOT / "RMX_Power.pretty").glob("*.kicad_mod")),
        PARENT / "input_range.kicad_sch",
        PARENT / "input_range.kicad_pro",
        PARENT / "RMX_E10.kicad_sym",
        PARENT / "sym-lib-table",
        PARENT / "components.json",
        PARENT / "verify.py",
        OUT / "inputs.json",
        OUT / "drc.json",
        OUT / "netlist.xml",
    ]
    repo = ROOT.parents[3]
    for n in [
        "common/placement.py",
        "common/sexpr.py",
        "common/netlists.py",
        "output_stage/check_placement.py",
        "power_supply/place.py",
        "rail_disconnect/routing/router.py",
        "rail_disconnect/routing/check.py",
        "common/reports.py",
    ]:
        sources.append(ROOT.parents[1] / n)
    for p in [repo / "tests/tooling/test_input_range_pcb.py"]:
        if p.exists():
            sources.append(p)
    report = dict(
        revision="E10-PCB-candidate",
        checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kicad_version=version,
        circuit_components=28,
        mounting_holes=4,
        board_size_mm=[*SIZE, 1.6],
        copper_layers=6,
        native_drc_violations=0,
        schematic_parity_issues=0,
        native_open_connections=count,
        routed_segments=len(children(tree, "segment")),
        through_vias=len(children(tree, "via")),
        independent_local_paths=paths,
        component_bounds=bodies,
        parent_circuit_preserved=True,
        pcb_routed=count == 0,
        native_connectivity_closed=count == 0,
        continuous_ground_plane_implemented=False,
        audio_performance_verified=False,
        physical_fit_verified=False,
        integrated_in_a11=False,
        production_parts_or_stackup_qualified=False,
        build_ready=False,
        source_sha256={str(p.relative_to(repo)): sha(p) for p in sorted(set(sources))},
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"E10 PCB candidate:28parts,{report['routed_segments']}segments,{report['through_vias']}vias;0nativeDRC/parity,{count}opens. No A11 fit or physical qualification."
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli", type=Path, required=True)
    args = p.parse_args()
    check(args.kicad_cli)


if __name__ == "__main__":
    main()
