"""Private source-tree revision, actual port pins and retained current allocations."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.power_distribution.p02.distribution import LOADS

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[5]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    context = json.load(open(ROOT / "generated/parent-fanout-requirements.json"))
    for rel, h in context["source_sha256"].items():
        assert sha(REPO / rel) == h, rel
    _, pins = netlist(ROOT / "generated/netlist.xml")
    for ref in ["J13", "J14", "J15"]:
        assert pins[ref] == {"1": "5V_DIG", "2": "AGND"}
    new = []
    for ref, target, gnd, current in [
        ("J14", "sequenced_bypass", "2", sum(LOADS[x][2] for x in ["bypass", "gain_input", "gain_output"])),
        ("J15", "rail_monitor", "3", LOADS["monitor_digital"][2]),
    ]:
        new.append(
            dict(
                positive_from=["processor_carrier", ref, "1"],
                positive_to=[target, "J1", "1"],
                positive_current_allocation_a=current,
                return_from=[target, "J1", gnd],
                return_to=["processor_carrier", ref, "2"],
                return_current="Requires full signed AGND/export/control/bipolar network; no independent equality or equal pin split is assumed",
                source_footprint="AWG18_Solder_2x1_P4mm_D2p2",
                source_single_wire_AWG=18,
                pretinned_bundle_max_requirement_mm=1.4,
                finished_source_bore_required_mm=[2.1, 2.3],
                destination_native_PCB_exists=False,
                route_length_mm=None,
                destination_mating_terminal_selected=False,
                joint_or_current_qualified=False,
            )
        )
    ledger = {
        "Seed_including_nested3v3": LOADS["seed_local"][2],
        "LED": sum(v[2] for k, v in LOADS.items() if k.startswith("led_")),
        "bypass_gain": new[0]["positive_current_allocation_a"],
        "monitor_digital": new[1]["positive_current_allocation_a"],
        "reserve_unassigned": LOADS["digital_reserve"][2],
    }
    assert abs(sum(ledger.values()) - 2.4) < 1e-12
    r = dict(
        scope=__doc__,
        code_sha256=sha(Path(__file__)),
        source_pcb_sha256=sha(ROOT / "processor_carrier.kicad_pcb"),
        native_netlist_sha256=sha(ROOT / "generated/netlist.xml"),
        retained_LOADS_source_sha256=sha(
            REPO / "hardware/electronics/power_distribution/p02/distribution.py"
        ),
        parent_destination_context_sha256=sha(ROOT / "generated/parent-fanout-requirements.json"),
        actual_new_pinmaps={k: pins[k] for k in ["J13", "J14", "J15"]},
        new_private_wires=new,
        input_positive_allocation_a=ledger,
        input_total_max_allocation_a=2.4,
        presently_assigned_positive_total_a=sum(ledger.values()) - ledger["reserve_unassigned"],
        reserve_assigned_load_or_connector=False,
        global_manifest_modified=False,
        proposed_source_tree="E28J4 positive/AGND -> E19J13 shared input; E19J14 -> bypass and E19J15 -> monitor. Replaces logical E28 direct DIG-BYPASS/MONITOR branches only if this new tree is adopted; never parallel duplicate both allocations.",
        old_J1_unfitted_service=True,
        source_joint_geometry_is_single_AWG18_per_bore=True,
        destination_native_boards_and_complete_harness_implemented=False,
        current_values_are_allocations_not_native_device_load_upper_bounds=True,
        source_to_load_PDN_solved=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (ROOT / "generated/fanout-ledger.json").write_text(json.dumps(r, indent=2) + "\n")
    print("Actual79part source tree/retained input ledger", ledger)


if __name__ == "__main__":
    run()
