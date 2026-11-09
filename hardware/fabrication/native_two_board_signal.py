"""Linux-only TBI01 native connectivity audit and schematic/PCB synchronization."""
import json
import shutil
import subprocess
import sys
from collections import defaultdict

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, OUT as SOURCE, PROJECT, prop, read_netlist, sha

OUT = STAGING / "two-board-signal-native-01"


def partition(pins):
    groups = defaultdict(set)
    for node, name in pins.items():
        groups[name].add(node)
    return {frozenset(v) for v in groups.values()}


def run():
    assert sys.platform == "linux", "Native CAD is isolated Linux only"
    import pcbnew
    assert not OUT.exists()
    source_hashes = {str(p.relative_to(REPO)): sha(p) for p in SOURCE.rglob("*") if p.is_file()}
    shutil.copytree(SOURCE, OUT)
    commands = []

    def command(label, args):
        p = subprocess.run(["kicad-cli", *args], capture_output=True, text=True, timeout=120)
        (OUT / (label + ".log")).write_text(p.stdout + p.stderr)
        commands.append(dict(command=["kicad-cli", *args], returncode=p.returncode))
        assert p.returncode == 0, (label, p.stdout, p.stderr)

    project = json.loads((OUT / (PROJECT + ".kicad_pro")).read_text())
    for group, keys in [(project.setdefault("erc", {}).setdefault("rule_severities", {}),
                         ["single_global_label", "four_way_junction", "simulation_model_issue", "footprint_filter"]),
                        (project["board"]["design_settings"].setdefault("rule_severities", {}),
                         ["missing_courtyard", "track_not_centered_on_via", "footprint_filters_mismatch", "footprint_type_mismatch"])]:
        for key in keys:
            group[key] = "error"
    (OUT / (PROJECT + ".kicad_pro")).write_text(json.dumps(project, indent=2) + "\n")
    schematic = OUT / (PROJECT + ".kicad_sch")
    command("netlist", ["sch", "export", "netlist", "--format", "kicadxml", "-o", str(OUT / "netlist.xml"), str(schematic)])
    actual, pins = read_netlist(OUT / "netlist.xml")
    expected = json.loads((SOURCE / "expected-circuit.json").read_text())
    wanted = {(ref, pin): name for ref, p in expected.items() for pin, name in p["pins"].items()}
    failures = []
    if set(actual) != set(expected):
        failures.append(dict(kind="part_set", missing=sorted(set(expected)-set(actual)), extra=sorted(set(actual)-set(expected))))
    for ref in expected.keys() & actual.keys():
        for field in ["value", "footprint"]:
            if (actual[ref].findtext(field) or "") != expected[ref][field]:
                failures.append(dict(kind=field, ref=ref, expected=expected[ref][field], actual=actual[ref].findtext(field)))
    missing, extra = partition(wanted)-partition(pins), partition(pins)-partition(wanted)
    if missing or extra:
        failures.append(dict(kind="net_partition", missing=[sorted(v) for v in missing], extra=[sorted(v) for v in extra]))
    mutation = dict(swapped_SAI_pin_detected=False, omitted_control_join_detected=False, analog_digital_5V_short_detected=False)
    if not failures:
        trial = dict(pins)
        trial[("D_J1005", "2")], trial[("D_J1005", "3")] = trial[("D_J1005", "3")], trial[("D_J1005", "2")]
        mutation["swapped_SAI_pin_detected"] = partition(trial) != partition(wanted)
        trial = dict(pins)
        for node in list(trial):
            if node[0].startswith("D_") and wanted[node] == "LINK_CODEC_RUN":
                trial[node] = "MUTATION_DISCONNECTED"
        mutation["omitted_control_join_detected"] = partition(trial) != partition(wanted)
        trial = dict(pins)
        an, dn = pins[("A_J702", "1")], pins[("D_J1001", "1")]
        assert an != dn
        trial = {node: an if net == dn else net for node, net in trial.items()}
        mutation["analog_digital_5V_short_detected"] = partition(trial) != partition(wanted)
    audit = dict(electrical_parts=len(actual), checked_pin_nodes=len(pins), failures=failures, mutation_controls=mutation,
                 only_scheduled_cross_source_joins=(not failures), fabricated=False)
    (OUT / "circuit-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    assert not failures and all(mutation.values()), "Native integration differs from explicit source-pin partition"
    # Bind the actual KiCad-exported nets and schematic instance paths to TB05 lands.
    pcb = OUT / (PROJECT + ".kicad_pcb")
    tree = read_sexpr(pcb.read_text())
    names = {name: i+1 for i, name in enumerate(sorted(set(pins.values())))}
    # Native net names retain the leading slash in the board database.
    import xml.etree.ElementTree as ET
    native_names = {n.attrib["name"].lstrip("/"): n.attrib["name"] for n in ET.parse(OUT / "netlist.xml").findall("./nets/net")}
    tree[:] = [n for n in tree if not (isinstance(n, list) and n and n[0] == "net")]
    for name, code in names.items():
        tree.append([a("net"), code, native_names[name]])
    paths = json.loads((SOURCE / "symbol-paths.json").read_text())
    assigned, mechanical, pad_count = set(), [], 0
    for f in children(tree, "footprint"):
        ref = str(prop(f, "Reference")[2])
        if ref not in expected:
            assert all(str(p[2]) == "np_thru_hole" for p in children(f, "pad")), ref
            attr = first(f, "attr")
            if a("board_only") not in attr:
                attr.append(a("board_only"))
            mechanical.append(ref)
            continue
        assigned.add(ref)
        f.append([a("path"), paths[ref]])
        for pad in children(f, "pad"):
            pin = str(pad[1])
            if not pin:
                continue
            assert (ref, pin) in pins, (ref, pin)
            name = pins[(ref, pin)]
            n = first(pad, "net")
            if n is None:
                pad.append([a("net"), names[name], native_names[name]])
            else:
                n[:] = [a("net"), names[name], native_names[name]]
            pad_count += 1
    assert set(expected)-assigned == {"A_U201"}
    pcb.write_text(sexpr(tree) + "\n")
    command("erc", ["sch", "erc", "--severity-all", "--format", "json", "-o", str(OUT / "erc.json"), str(schematic)])
    command("drc", ["pcb", "drc", "--all-track-errors", "--schematic-parity", "--severity-all", "--format", "json", "-o", str(OUT / "drc.json"), str(pcb)])
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    board.GetConnectivity().RecalculateRatsnest()
    drc = json.loads((OUT / "drc.json").read_text())
    erc = json.loads((OUT / "erc.json").read_text())
    assert all(sha(REPO / p) == digest for p, digest in source_hashes.items())
    report = dict(source_sha256=source_hashes, commands=commands, circuit_audit=audit,
        assigned_electrical_footprints=len(assigned), assigned_pad_instances=pad_count,
        mechanical_board_only=mechanical, missing_codec_footprint="A_U201",
        opens=board.GetConnectivity().GetUnconnectedCount(False),
        drc_categories={key: len(value) for key, value in drc.items() if isinstance(value, list)},
        erc_categories={key: len(value) for key, value in erc.items() if isinstance(value, list)},
        routing_complete=False, fabrication_released=False)
    (OUT / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ["source_sha256", "commands", "mechanical_board_only"]}))


if __name__ == "__main__":
    run()
