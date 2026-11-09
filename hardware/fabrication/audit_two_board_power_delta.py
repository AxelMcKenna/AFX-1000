"""Independent comparison: TBP composition changes connectivity, never placement."""
import copy
import json
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, CAD, prop, read_netlist, sha

OUT = STAGING / "two-board-power-native-02"


def geometry(node, mechanical=False):
    if not isinstance(node,list):
        return node
    if node and node[0] in ["net","path"]:
        return None
    result = []
    for child in node:
        if mechanical and node and node[0] == "attr" and child == "board_only":
            continue
        value = geometry(child,mechanical)
        if value is not None:
            result.append(value)
    return result


def check():
    before_path,after_path = CAD/"power_protection.kicad_pcb",OUT/"power_protection.kicad_pcb"
    before,after = [read_sexpr(p.read_text()) for p in [before_path,after_path]]
    expected = json.loads((OUT/"expected-circuit.json").read_text())
    old,new = [{str(prop(f,"Reference")[2]):f for f in children(t,"footprint")} for t in [before,after]]
    assert old.keys() == new.keys() and len(new) == 1092
    parts,pins = read_netlist(OUT/"netlist.xml")
    assert set(parts) == set(expected)
    pad_count = 0
    for ref in old:
        assert geometry(old[ref],ref not in expected) == geometry(new[ref],ref not in expected),ref
        for pad in children(new[ref],"pad"):
            if ref not in expected or not str(pad[1]):
                continue
            net = first(pad,"net")
            assert str(net[2]).lstrip("/") == pins[(ref,str(pad[1]))],(ref,pad[1])
            pad_count += 1
    def root_geometry(t):
        return [n for n in t if not(isinstance(n,list) and n and n[0] in ["footprint","net"])]
    assert root_geometry(before) == root_geometry(after)
    assert not any(children(after,tag) for tag in ["segment","via","zone"])
    mutation = {}
    ref = "N_U19"
    for kind in ["shifted_part","changed_land_size","changed_component_value"]:
        trial = copy.deepcopy(new[ref])
        if kind == "shifted_part":
            first(trial,"at")[1] = float(first(trial,"at")[1])+1
        elif kind == "changed_land_size":
            first(children(trial,"pad")[0],"size")[1] = 9
        else:
            prop(trial,"Value")[2] = "UNDECLARED_SUBSTITUTION"
        mutation[kind] = geometry(trial) != geometry(old[ref])
    assert all(mutation.values())
    erc = json.loads((OUT/"erc.json").read_text())
    warnings = [v for s in erc["sheets"] for v in s.get("violations",[])]
    assert len(warnings) == 2
    assert all(v["type"] == "ground_pin_not_ground" and v["severity"] == "warning" for v in warnings)
    isolated = [dict(ref=r,pin="4",actual_reference_net=pins[(r,"4")],host_reference_net=pins[(r,"5")]) for r in ["N_U19","N_U24"]]
    assert all(r["actual_reference_net"] != r["host_reference_net"] for r in isolated)
    paths = [Path(__file__),before_path,after_path,OUT/"netlist.xml",OUT/"review.json",OUT/"erc.json",OUT/"drc.json",
             OUT/"expected-circuit.json",OUT/"circuit-audit.json",STAGING/"two-board-power-integration-02/construction.json"]
    result = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        unchanged_complete_footprint_geometry=1092,unchanged_electrical_components=1077,
        mapped_physical_pad_instances=pad_count,unchanged_outline_mounts_and_setup=True,
        only_declared_net_path_and_mechanical_board_only_edits=True,
        geometry_mutation_controls=mutation,isolated_reference_warnings=isolated,
        isolated_reference_ground_nets_distinct=True,erc_warnings_waived=False,
        complete_power_circuit=False,electrical_placement_qualified=False,fabrication_released=False)
    with (OUT/"placement-delta.json").open("x") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    print(json.dumps({k:result[k] for k in ["unchanged_complete_footprint_geometry","mapped_physical_pad_instances","geometry_mutation_controls","isolated_reference_warnings"]}))


if __name__ == "__main__":
    check()
