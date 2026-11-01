"""Source-bound port and current requirements for the supported receiver ear."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.power_distribution.p02.distribution import LOADS

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    neck = json.loads((ROOT / "generated/native-neck.json").read_text())
    known = {"seed_local", "led_logic", *[f"led_group_{i}" for i in range(1, 5)]}
    dig = {k: v[2] for k, v in LOADS.items() if v[0] == "DIG"}
    other = {k: v for k, v in dig.items() if k not in known}
    nested = {k: LOADS[k][2] for k in ["converter_3v3", "controls_3v3", "monitor_3v3"]}
    sources = [
        REPO / "hardware/electronics/power_distribution/p02/distribution.py",
        ROOT / "generated/native-neck.json",
        ROOT / "generated/tool-axis.json",
        ROOT.parent / "proposals/processor-awg18-ear-supported/generated/current-native.json",
        ROOT.parent / "proposals/processor-awg18-ear-supported/generated/package-review.json",
    ]
    total = sum(dig.values())
    known_total = sum(dig[k] for k in known)
    report = dict(
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in sources},
        code_sha256=sha(Path(__file__)),
        retained_digital_allocations_a=dig,
        shared_J13_input_target_a=total,
        known_west_of_neck_a=known_total,
        unassigned_physical_force_return_interfaces_a=other,
        unassigned_total_a=sum(other.values()),
        positive_neck_current_expression="1.764 A + I_other_west; I_other_west in [0,0.636] A until actual fanout is defined",
        positive_neck_current_allocation_interval_a=[known_total, total],
        current_rating_may_be_reduced_to_known_branches=False,
        nested_3v3_export_allocations_a=nested,
        nested_3v3_not_additional_Seed_positive_current=True,
        local_Seed_return_expression="1.0 A minus actual outgoing 3V3/export current; .925 A only if retained .075 A export allocation is realized",
        ground_current_expression="Coupled signed local/remote returns plus possible interboard loops; no equal pin split or zero external-current assumption",
        actual_5V_DIG_pad_nodes=neck["actual_5V_DIG_pad_nodes"],
        old_J1_role="Unfitted service pads; no operating branch or second input allocated",
        no_physical_force_ports_for_other_allocations=True,
        input_joint_single_AWG18_pretinned_bundle_max_mm=1.4,
        two_wires_in_existing_input_bore_qualified=False,
        actionable_options=[
            "Define real outgoing positive and return interfaces for retained bypass/gain, monitor and reserve branches, with actual shared input current and source-to-load network.",
            "A real ear-side fanout could divert its assigned current before the neck, but only after native terminals, joints, lead bundle and return paths are implemented and checked.",
            "A west-side fanout retains the full 2.4 A neck allocation. Solve actual finite four-layer copper and signed return network after layout/ports are selected.",
            "Retain failed vertical-tool criterion until a selected alternate access or an actual bus installation/removal sequence is geometrically demonstrated.",
        ],
        neck_width_is_geometric_not_resistance_ampacity_or_noise_proof=True,
        full_PDN_solved=False,
        physical_qualified=False,
        fabrication_released=False,
        prior_J1_source_PDN_inherited=False,
    )
    (ROOT / "generated/requirements.json").write_text(json.dumps(report, indent=2) + "\n")
    print(total, known_total, sum(other.values()))


if __name__ == "__main__":
    run()
