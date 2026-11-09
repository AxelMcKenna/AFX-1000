"""Native power-board validation with canonical footprint instance paths."""
import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha


def partition(pins):
    groups = defaultdict(set)
    for node, net in pins.items():
        groups[net].add(node)
    return {frozenset(nodes) for nodes in groups.values()}


def run():
    assert sys.platform == "linux"
    import pcbnew
    ap = argparse.ArgumentParser()
    ap.add_argument("--source",default="two-board-power-integration-01")
    ap.add_argument("--output",default="two-board-power-native-01")
    args = ap.parse_args()
    assert all(all(c.isalnum() or c in "-_" for c in n) for n in [args.source,args.output])
    source, out = STAGING/args.source, STAGING/args.output
    assert not out.exists()
    paths = [Path(__file__),REPO/"hardware/fabrication/integrate_two_board_signal.py",*[p for p in source.rglob("*") if p.is_file()]]
    hashes = {str(p.relative_to(REPO)):sha(p) for p in paths}
    shutil.copytree(source,out)
    project = "power_protection"
    settings_path = out/(project+".kicad_pro")
    settings = json.loads(settings_path.read_text())
    erc_rules = settings.setdefault("erc",{}).setdefault("rule_severities",{})
    drc_rules = settings["board"]["design_settings"].setdefault("rule_severities",{})
    for rule in ["single_global_label","four_way_junction","simulation_model_issue","footprint_filter"]:
        erc_rules[rule] = "error"
    for rule in ["missing_courtyard","track_not_centered_on_via","footprint_filters_mismatch","footprint_type_mismatch"]:
        drc_rules[rule] = "error"
    settings_path.write_text(json.dumps(settings,indent=2)+"\n")
    commands = []

    def command(label,args):
        p = subprocess.run(["kicad-cli",*args],capture_output=True,text=True,timeout=120)
        (out/(label+".log")).write_text(p.stdout+p.stderr)
        commands.append(dict(command=["kicad-cli",*args],returncode=p.returncode))
        assert p.returncode == 0,(label,p.stdout,p.stderr)

    sch = out/(project+".kicad_sch")
    command("netlist",["sch","export","netlist","--format","kicadxml","-o",str(out/"netlist.xml"),str(sch)])
    actual,pins = read_netlist(out/"netlist.xml")
    expected = json.loads((source/"expected-circuit.json").read_text())
    wanted = {(r,pin):net for r,p in expected.items() for pin,net in p["pins"].items()}
    differences = []
    if actual.keys() != expected.keys():
        differences.append(dict(kind="part_set",missing=sorted(expected.keys()-actual.keys()),extra=sorted(actual.keys()-expected.keys())))
    for ref in expected.keys() & actual.keys():
        for field in ["value","footprint"]:
            if (actual[ref].findtext(field) or "") != expected[ref][field]:
                differences.append(dict(kind=field,ref=ref,expected=expected[ref][field],actual=actual[ref].findtext(field)))
    missing,extra = partition(wanted)-partition(pins),partition(pins)-partition(wanted)
    if missing or extra:
        differences.append(dict(kind="pin_partition",missing=[sorted(g) for g in missing],extra=[sorted(g) for g in extra]))
    mutation = {}
    if not differences:
        for name,left,right in [
            ("negative_stage_bypass",("P_J2","3"),("E_J1","3")),
            ("NF_raw5_limiter_bypass",("P_J23","1"),("N_J1","3")),
            ("fan_RUN_bypass",("F_J4","1"),("E_J5","3")),
            ("isolated_module_return_short",("N_J6","2"),("N_J1","2")),
            ("protected_raw5_short",("E_J11","1"),("E_J4","1")),
            ("wrong_GLOBAL_MASTER_source",("N_J1","6"),("E_U29","7")),
        ]:
            leftnet,rightnet = pins[left],pins[right]
            assert leftnet != rightnet,name
            trial = {node:leftnet if net == rightnet else net for node,net in pins.items()}
            mutation[name] = partition(trial) != partition(wanted)
        trial = dict(pins)
        trial[("N_J2","1")],trial[("N_J2","2")] = trial[("N_J2","2")],trial[("N_J2","1")]
        mutation["negative_force_pin_swap"] = partition(trial) != partition(wanted)
    audit = dict(electrical_parts=len(actual),checked_pin_entries=len(pins),differences=differences,
                 mutation_controls=mutation,only_declared_interface_joins=not differences,
                 complete_power_circuit=False,fabrication_released=False)
    (out/"circuit-audit.json").write_text(json.dumps(audit,indent=2)+"\n")
    assert not differences and all(mutation.values())
    pcb = out/(project+".kicad_pcb")
    tree = read_sexpr(pcb.read_text())
    nets = {n.attrib["name"].lstrip("/"):n.attrib["name"] for n in ET.parse(out/"netlist.xml").findall("./nets/net")}
    ids = {name:i+1 for i,name in enumerate(sorted(nets))}
    tree[:] = [n for n in tree if not(isinstance(n,list) and n and n[0] == "net")]
    for name,code in ids.items():
        tree.insert(8,[a("net"),code,nets[name]])
    instances = json.loads((source/"symbol-paths.json").read_text())
    mapped,mechanical,pad_count = set(),[],0
    for f in children(tree,"footprint"):
        ref = str(prop(f,"Reference")[2])
        if ref not in expected:
            assert all(str(p[2]) == "np_thru_hole" for p in children(f,"pad")),ref
            if not children(f,"attr"):
                f.append([a("attr")])
            attr = first(f,"attr")
            if a("board_only") not in attr:
                attr.append(a("board_only"))
            mechanical.append(ref)
            continue
        mapped.add(ref)
        existing_paths = children(f, "path")
        # Repeated validation must not append another copy of the same path.
        # A different existing path is a circuit-mapping error, not metadata to discard.
        assert all(str(p[1]) == instances[ref] for p in existing_paths), ref
        f[:] = [n for n in f if not (isinstance(n, list) and n and n[0] == "path")]
        f.append([a("path"), instances[ref]])
        assert len(children(f, "path")) == 1
        for pad in children(f,"pad"):
            pin = str(pad[1])
            if not pin:
                continue
            assert (ref,pin) in pins,(ref,pin)
            name = pins[(ref,pin)]
            oldnet = next(iter(children(pad,"net")),None)
            newnet = [a("net"),ids[name],nets[name]]
            if oldnet is None:
                pad.append(newnet)
            else:
                oldnet[:] = newnet
            pad_count += 1
    assert mapped == set(expected)
    pcb.write_text(sexpr(tree)+"\n")
    command("erc",["sch","erc","--severity-all","--format","json","-o",str(out/"erc.json"),str(sch)])
    command("drc",["pcb","drc","--all-track-errors","--schematic-parity","--severity-all","--format","json","-o",str(out/"drc.json"),str(pcb)])
    board = pcbnew.LoadBoard(str(pcb))
    board.BuildConnectivity()
    board.GetConnectivity().RecalculateRatsnest()
    drc,erc = [json.loads((out/name).read_text()) for name in ["drc.json","erc.json"]]
    erc_findings = [v for s in erc["sheets"] for v in s.get("violations",[])]
    assert not erc["ignored_checks"] and not drc["ignored_checks"]
    assert all(sha(REPO/name) == digest for name,digest in hashes.items())
    result = dict(source_sha256=hashes,commands=commands,circuit_audit=audit,
        placed_electrical_parts=len(mapped),mapped_pad_instances=pad_count,mechanical_board_only=mechanical,
        opens=board.GetConnectivity().GetUnconnectedCount(False),geometry_findings=len(drc["violations"]),
        schematic_parity_findings=len(drc["schematic_parity"]),erc_findings=len(erc_findings),
        artifact_sha256={p.name:sha(p) for p in [pcb,sch,settings_path,out/"netlist.xml",out/"erc.json",out/"drc.json"]},
        canonical_footprint_symbol_paths=True,all_native_rule_checks_enabled=True,complete_power_circuit=False,routing_complete=False,fabrication_released=False)
    (out/"review.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ["placed_electrical_parts","mapped_pad_instances","opens","geometry_findings","schematic_parity_findings","erc_findings"]}))


if __name__ == "__main__":
    run()
