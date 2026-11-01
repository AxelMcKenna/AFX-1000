"""Independent actual pin/fanout/Boolean and conditional receiving audit for 19 nodes."""

import copy
import hashlib
import json
from pathlib import Path

from . import control
from .schmitt_cone_candidate import CHANNELS, GROUPS, ROOT

SOURCE = ROOT / "generated/schmitt-all-oc-old-leaf-work"


def contract(parts):
    by = {c["ref"]: c for c in parts}
    raws = {n for g in GROUPS for n in g if n}
    assert len(raws) == 19
    projected = copy.deepcopy(parts)
    projected = [
        c
        for c in projected
        if c["ref"] not in {f"U{i}" for i in range(36, 43)} | {f"C{i}" for i in range(79, 86)}
    ]
    for c in projected:
        for p in c["pins"]:
            if p["net"] and p["net"].endswith("_SCHMITT"):
                assert p["net"][:-8] in raws
                p["net"] = p["net"][:-8]
    control.contract(projected)
    rows = []
    for i, g in enumerate(GROUPS):
        c = by[f"U{36 + i}"]
        p = {int(v["number"]): v for v in c["pins"]}
        assert c["part"] == "SN74LVC3G17DCUR" and p[4]["net"] == "AGND" and p[8]["net"] == "V2V5_AUX"
        for raw, (a, y) in zip(g, CHANNELS):
            assert p[a]["kind"] == "input" and p[y]["kind"] == "output"
            assert p[a]["net"] == (raw or "AGND") and p[y]["net"] == (raw + "_SCHMITT" if raw else None)
            if not raw:
                continue
            source = [
                (v["ref"], q["number"])
                for v in parts
                for q in v["pins"]
                if q["net"] == raw and q["kind"] == "open_collector"
            ]
            assert len(source) == 1
            raw_inputs = [
                (v["ref"], q["number"])
                for v in parts
                for q in v["pins"]
                if q["net"] == raw and q["kind"] == "input"
            ]
            assert raw_inputs == [(c["ref"], str(a))], (raw, raw_inputs)
            loads = [
                (v, q)
                for v in parts
                for q in v["pins"]
                if q["net"] == raw + "_SCHMITT" and q["kind"] == "input"
            ]
            assert len(loads) == (2 if raw == "DIG_PG3" else 1)
            assert all(v["part"].startswith(("SN74LVC08A", "SN74AUP2G08")) for v, q in loads)
            allocation = sum(20 if v["part"].startswith("SN74LVC08A") else 0.5 for v, q in loads) + 2
            assert allocation <= 100
            rows.append(
                dict(
                    raw=raw,
                    buffer=c["ref"],
                    input_pin=a,
                    output_pin=y,
                    source=source,
                    receivers=[(v["ref"], q["number"]) for v, q in loads],
                    load_allocation_uA=allocation,
                )
            )
    assert len(rows) == 19
    return rows


def main():
    parts = json.loads((SOURCE / "components.json").read_text())
    rows = contract(parts)
    before = json.loads((ROOT / "generated/coherent-ground-repair-work/components.json").read_text())
    cases = []
    for bits in range(64):
        inputs = control.safe_inputs(before)
        inputs.update(
            POWER_RUN=(bits >> 0) & 1,
            P03_SOURCES_READY=(bits >> 1) & 1,
            NF_OUTPUT_VALID_RAW=(bits >> 2) & 1,
            DIG_PG3=(bits >> 3) & 1,
            ANA_PG2=(bits >> 4) & 1,
            E28_TIMEOUT_RAW=(bits >> 5) & 1,
        )
        a = control.StaticLogic(before).settle(**inputs)
        b = control.StaticLogic(parts).settle(**inputs)
        names = [
            "E28_MASTER_ENABLE",
            "E28_ANA_ENABLE",
            "E28_DIG_FOLLOW1",
            "E28_DIG_FOLLOW2",
            "E28_DIG_FOLLOW3",
            "E28_ANA_FOLLOW",
            "E28_ANA_FOLLOW2",
            "E28_FAULT",
            "E28_OUTPUT_READY",
        ]
        assert {n: a[n] for n in names} == {n: b[n] for n in names}, bits
        cases.append(dict(bits=bits, outputs={n: b[n] for n in names}))
    report = dict(
        source_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                SOURCE / "components.json",
                ROOT / "generated/coherent-ground-repair-work/components.json",
                Path(__file__),
                ROOT / "generated/reset-buffer-proposal/sources/sn74lvc3g17.pdf",
            ]
        },
        rows=rows,
        steady_boolean_cases=cases,
        continuous_output_rows=dict(
            VCC_min=1.65,
            VCC_max=5.5,
            max_load_uA=100,
            VOH_drop_max_V=0.1,
            VOL_max_V=0.1,
            temperature_max_C=125,
        ),
        conditional_raw_receiving=dict(
            AUX_min_V=2.5,
            AUX_max_V=2.7,
            Rpullup_ohm=10000,
            Rpullup_total_max=10200,
            buffer_II_uA=5,
            additional_board_leak_uA=2,
            source_off_leak_allocation_uA=2,
            high_min_V=2.5 - 10200 * 9e-6,
            VTplus_enclosure_V=1.87,
            VTminus_enclosure_V=0.58,
            low_source_sink_allocation_A=2.7 / 9800 + 7e-6,
            source_specific_low_V_and_off_leak_accepted=False,
            intermediate_VCC_and_VI_discrete_row_transfer_accepted=False,
        ),
        additional_7_package_AUX_reservation_A=0.014,
        additional_reservation_includes_output_and_dynamic_allocation=True,
        guaranteed_extra_ICC_at_2p5V=False,
        received_output_edge_required=dict(
            LVC08A_max_ns_per_V=8,
            AUP2G08_max_ns_per_V=200,
            buffer_output_rise_fall_max_specified=False,
            assembled_node_C_and_rise_fall_capture_accepted=False,
            propagation_delay_is_not_rise_time=True,
        ),
        partial_AUX_failOFF_accepted=False,
        PDN_coupled_ground_accepted=False,
        mechanical_full_native_fit_accepted=False,
        physical_qualified=False,
    )
    (SOURCE / "generated/receiving-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "19 actual Schmitt receiving contracts / 64 unchanged steady-state cases pass; dynamic, source-specific and physical holds remain"
    )


if __name__ == "__main__":
    main()
