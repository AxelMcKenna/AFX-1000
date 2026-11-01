"""Actual sealed261/265 identity changes and historical passive reconciliation."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def delta(a, b):
    by_a = {p["ref"]: p for p in a}
    by_b = {p["ref"]: p for p in b}
    changed = {}
    for ref in sorted(by_a.keys() & by_b.keys()):
        change = {
            key: [by_a[ref].get(key), by_b[ref].get(key)]
            for key in ["part", "footprint", "pins"]
            if by_a[ref].get(key) != by_b[ref].get(key)
        }
        if change:
            changed[ref] = change
    return dict(
        added={r: by_b[r] for r in sorted(by_b.keys() - by_a.keys())},
        removed=sorted(by_a.keys() - by_b.keys()),
        changed=changed,
    )


def build():
    target = ROOT / "identity-review.json"
    if target.exists():
        raise RuntimeError("Fresh identity review required")
    a = json.loads((ROOT / "inputs/NF261/components.json").read_text())
    b = json.loads((ROOT / "inputs/NF265/components.json").read_text())
    selected = json.loads((ROOT / "inputs/references/NP01-selections.json").read_text())
    old = [dict(ref=p["ref"], part=p["old_part"], footprint=p["old_footprint"]) for p in selected["rows"]]
    new = [p for p in b if p["ref"].startswith(("R", "C"))]
    partial_delta = delta(old, new)
    # Historical NP table did not carry full native pin records in this list.
    for change in partial_delta["changed"].values():
        change.pop("pins", None)
    partial_delta["changed"] = {k: v for k, v in partial_delta["changed"].items() if v}
    d = dict(
        revision="NC265-exact-identity-review",
        NF261_to_NF265=delta(a, b),
        historical_NP01_to_current265_passive_identity_delta=partial_delta,
        current265_passive_count=len(new),
        current265_component_count=len(b),
        current265_connectors=json.loads((ROOT / "inputs/NF265/integration-contract.json").read_text())[
            "connectors"
        ],
        new_exact_body_notes=dict(
            C99=dict(
                MPN="C1206C104J3GACTU",
                bodymax_T_mm=1.8,
                project_seat_mm=0.1,
                projection_receiving_mm=1.9,
                old47nF_not_inherited=True,
            ),
            C100=dict(
                MPN="C0603C104K5RACTU",
                bodymax_T_mm=0.95,
                project_seat_mm=0.1,
                projection_receiving_mm=1.05,
                primary_exact_tables="KEMET2026PDF5/9-CJ",
            ),
        ),
        R92_R94_HW_EN00=dict(
            initial_fraction=0.0002,
            TCR_ppm_per_K=2,
            range_ohm=[500, 20000],
            complete0p35_receiving_NOT_unconditional_lifetime=True,
        ),
        R93_complete0p7_is_separate_trim_receiving_not_supplier_guarantee=True,
        all_remaining_original_COMPLETE0p1_primitive_resistors_still_need_electrical_error_allocation_resolution=True,
        real_connector_parts=dict(
            J1=["B30B-PHDSS", "PHDR-30VS", "SPHD-002T-P0.5"],
            J3_J5=["B2B-PH-K-S", "PHR-2", "SPH-002T-P0.5S"],
            J6=["B2B-XH-A(LF)(SN)", "XHP-2", "SXH-001T-P0.6"],
            force_wire="Alpha6715 BK005 proposal, four separately marked N19/N12 P03/E28 leads",
        ),
        connector_guarantees_NOT_closed=[
            "Individual product drawing/mating tolerances and received maximum envelopes",
            "1.76mm max board beyond PH1.6 applicable maximum and PHD/XH1.6 reference",
            "Post-solder tail trim PLUS fillet<=1.5mm; nominal3.0/3.4 tails cannot be assumed to comply across1.44..1.76 board range",
            "Exact crimp/strip/insulation support, wire temperature/ampacity and pull/retention/vibration/life",
            "Low-level signal/dry-circuit behavior and shared RAW5/AUX ground coupling",
            "Module input inrush/hot current, branch fault protection and contact life",
            "Complete force wire length/hot resistance/four joint allocation and remote strain/terminations",
        ],
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
        source_sha256={
            str(p): sha(p)
            for p in [
                Path(__file__),
                ROOT / "inputs/NF261/components.json",
                ROOT / "inputs/NF265/components.json",
                ROOT / "inputs/references/NP01-selections.json",
                ROOT / "inputs/NF265/integration-contract.json",
            ]
        },
    )
    target.write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                current_components=len(b),
                passives=len(new),
                added=list(d["NF261_to_NF265"]["added"]),
                changed=len(d["NF261_to_NF265"]["changed"]),
            )
        )
    )


if __name__ == "__main__":
    build()
