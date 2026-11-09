"""Current-pin power integration proposal; no electrical joins or release implied."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, read_netlist, sha

OUT = STAGING / "two-board-power-interface-audit-01"
CAPTURE = STAGING / "two-board-placement-05/capture.json"
NF = REPO / "hardware/qualification/boards/startup_negative_circuit/absolute_aux_gate/integration-contract.json"
FPC = REPO / "hardware/qualification/boards/fan_health/composite_nf_branch/README.md"


def build():
    assert not OUT.exists()
    OUT.mkdir()
    cap = json.loads(CAPTURE.read_text())
    roles = dict(P="power_supply", I="input_protection", E="rail_disconnect", M="rail_monitor",
                 N="negative_startup_protection", F="fan_health_protection")
    paths = [Path(__file__), CAPTURE, NF, FPC]
    pins = {}
    for prefix, role in roles.items():
        pcb = REPO / cap["sources"][role]["path"]
        assert sha(pcb) == cap["sources"][role]["sha256"]
        nl = pcb.parent / "netlist.xml"
        paths += [pcb, nl]
        _, pins[prefix] = read_netlist(nl)
    rows = []

    def add(label, left, ln, right, rn, basis):
        for endpoint, net in [(left, ln), (right, rn)]:
            role, ref, pin = endpoint
            assert pins[role][(ref, pin)] == net, (endpoint, net, pins[role].get((ref, pin)))
        rows.append(dict(function=label, endpoints=[left, right], actual_source_nets=[ln, rn],
                         basis=basis, implemented_in_combined_schematic=False,
                         electrical_and_physical_receiving_qualified=False))

    add("inlet DC", ("I","J2","1"),"DC_IN",("P","J101","1"),"DC_IN","Current inlet and P03 native pin contracts")
    add("inlet DC return", ("I","J2","2"),"AGND",("P","J101","2"),"AGND","Separate current-path review required")
    for pin, net in [("1","SWITCH_SUPPLY"),("2","POWER_RUN"),("3","AGND")]:
        add("physical power switch",("I","J3",pin),net,("P","J104",pin),net,"Current inlet and P03 switch ports")
    for pin, net in [("1","P19_SRC"),("4","P12_SRC")]:
        add("positive source to disconnect",("P","J2",pin),net,("E","J1",pin),net,"Current native source/disconnect pin contracts; current capacity pending")
    add("raw analog 5V force",("P","J24","1"),"V5_REG_SRC",("E","J10","1"),"V5_REG_SRC","Operating force terminals; no test header substituted")
    add("raw digital 5V force",("P","J23","1"),"5V_DIG_SRC",("E","J11","1"),"5V_DIG_SRC","Operating force terminals; no test header substituted")
    add("supply/disconnect force return",("P","J20","1"),"AGND",("E","J7","1"),"AGND","Return topology/current/impedance unresolved")
    for pin, nfref, rail in [("3","J2","N19"),("5","J4","N12")]:
        add(rail+" source into NF",("P","J2",pin),rail+"_SRC",("N",nfref,"1"),rail+"_P03_SRC",str(NF.relative_to(REPO)))
        add(rail+" NF output into E28",("N",nfref,"2"),rail+"_E28_SRC",("E","J1",pin),rail+"_SRC",str(NF.relative_to(REPO)))
    add("fan/NF operating raw5",("P","J23","1"),"5V_DIG_SRC",("F","J201","1"),"FAN5V_IN",str(FPC.relative_to(REPO)))
    add("fan/NF operating return",("P","J21","1"),"AGND",("F","J201","2"),"GND",str(FPC.relative_to(REPO)))
    add("current-limited NF raw5",("F","J401","1"),"NF_RAW5",("N","J1","3"),"DIG5_FORCE",str(FPC.relative_to(REPO)))
    add("NF raw5/control return",("F","J401","2"),"GND",("N","J1","2"),"AGND",str(FPC.relative_to(REPO)))
    add("RUN through fan interlock: input",("P","J106","3"),"POWER_RUN_E28_LEAF",("F","J4","1"),"P03_POWER_RUN","Current AX03 leaf and FPC interlock; receiver/loading/timing review pending")
    add("RUN through fan interlock: output",("F","J4","2"),"E28_POWER_RUN",("E","J5","3"),"POWER_RUN","Current FPC interlock and E28 receiver; no bypass")
    add("auxiliary supply",("P","J106","1"),"V2V5_AUX",("E","J5","1"),"V2V5_AUX","Current P03/E28 auxiliary contract; NF branch still unresolved")
    add("source-ready",("P","J106","4"),"P03_ALL_SOURCES_READY",("E","J9","2"),"P03_SOURCES_READY","Current native P03/E28 ready contracts")
    add("NF output-valid",("N","J1","30"),"NF_OUTPUT_VALID",("E","J12","1"),"NF_OUTPUT_VALID_RAW",str(NF.relative_to(REPO)))
    for pin, net in [("1","P19"),("2","AGND"),("3","N19"),("4","P12"),("5","N12"),("6","V5_REG")]:
        add("protected analog monitor",("E","J3",pin),net,("M","J2",pin),net,"Current monitor inputs must observe protected outputs")
    add("protected digital monitor",("E","J4","1"),"5V_DIG",("M","J1","1"),"5V_DIG","Current monitor input must observe protected output")
    # Union only the proposed external interfaces; internal circuit elements are
    # never treated as shorts, including switches, protection and the NF stages.
    parent = {}
    def root(k):
        parent.setdefault(k,k)
        if parent[k] != k:
            parent[k] = root(parent[k])
        return parent[k]
    for row in rows:
        keys = [(e[0], n) for e, n in zip(row["endpoints"],row["actual_source_nets"])]
        parent[root(keys[1])] = root(keys[0])
    forbidden = [(("P","N19_SRC"),("E","N19_SRC")),
                 (("P","N12_SRC"),("E","N12_SRC")),
                 (("P","5V_DIG_SRC"),("N","DIG5_FORCE")),
                 (("F","P03_POWER_RUN"),("E","POWER_RUN")),
                 (("N","MODULE_INPUT_GND"),("N","AGND")),
                 (("E","5V_DIG_SRC"),("E","5V_DIG")),
                 (("E","V5_REG_SRC"),("E","V5_REG"))]
    assert all(root(a) != root(b) for a,b in forbidden)
    nf = json.loads(NF.read_text())
    assert pins["E"][("U12","11")] == "ALL_RAILS_ALLOW"
    assert pins["E"][("U29","7")] == "E28_MASTER_ENABLE"
    assert not nf["separate_module_input"]["board_tie_to_AGND"]
    holds = [
        "NF GLOBAL_MASTER needs a qualified buffer from E28 U12.11 ALL_RAILS_ALLOW; E28 J6.2/U29.7 E28_MASTER_ENABLE is not interchangeable.",
        "Complete NF clamp, OV-sense, fault-request, auxiliary and protected-output feedback wiring needs an integrated circuit and loading/fault review.",
        "NF J6 guarded module-input feed and separate MODULE_INPUT_GND force return remain unresolved; no board tie to NF AGND is authorized by the source contract.",
        "Do not adopt the older direct P03-to-E28 negative-rail links; they bypass NF. The old E28 J2 digital header is absent from the current source.",
        "NF operating control power must use FPC current-limited NF_RAW5; the older direct raw5 proposal bypasses U401 protection.",
        "Fan-health interlock must remain in the RUN path; old direct P03-to-E28 RUN wiring bypasses it.",
        "Monitor V3V3_IO, NBIAS_L/R and PRE_ANALOG_OK cross-board connections require the final signal/power interface.",
        "All power/ground current paths, Kelvin placement, voltage drop, source/fault/UV recovery, decoupling and thermal constraints need renewed review on the consolidated PCB.",
    ]
    result = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
                  checked_proposed_pin_pairs=len(rows), proposed_interfaces=rows,
                  forbidden_direct_net_joins=[[list(a),list(b)] for a,b in forbidden],
                  forbidden_joins_absent_from_proposal=True, unresolved_design_holds=holds,
                  combined_power_schematic_complete=False, wiring_qualified=False, fabrication_released=False)
    (OUT / "interface-review.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(checked_proposed_pin_pairs=len(rows), forbidden_bypasses_rejected=len(forbidden), unresolved_design_holds=len(holds))))


if __name__ == "__main__":
    build()
