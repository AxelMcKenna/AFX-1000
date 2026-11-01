"""Reproducible first-master startup stress screen, never thermal/SOA approval."""

import hashlib
import json
import re
from pathlib import Path

from .manufacturer import ROOT
from .positive import components

SOURCE = "https://www.ti.com/lit/ds/symlink/tps25948.pdf"


def screen(parts=None, load_current_a=None):
    parts = components() if parts is None else parts
    rows = []
    for domain, ref, prefix, maximum_cap_f, default_load in (
        ("digital", "U15", "E28_DIG_0", 0.0071, 2.4),
        ("analog", "U13", "E28_ANA_0", 0.0022, 0.251),
    ):
        chip = next(c for c in parts if c["ref"] == ref)
        pins = {p["number"]: p["net"] for p in chip["pins"]}
        assert pins["4"] == "AGND" and pins["10"] is None
        dvdtr = next(
            c for c in parts if {p["net"] for p in c["pins"]} == {prefix + "_DVDT", prefix + "_DVDT_CAP"}
        )
        cap = next(
            c
            for c in parts
            if c["ref"].startswith("C") and {p["net"] for p in c["pins"]} == {prefix + "_DVDT_CAP", "AGND"}
        )
        assert dvdtr["part"] == "100 1%" and "C0G 5%" in cap["part"]
        nominal = float(re.match(r"([\d.]+)nF", cap["part"])[1]) * 1e-9
        cmin = nominal * 0.95 * (1 - 30e-6 * 100)
        cmax = nominal * 1.05 * (1 + 30e-6 * 100)
        slew_max = 9e-6 / cmin
        slew_min = 2.6e-6 / cmax
        vin = 5.1
        load = default_load if load_current_a is None else load_current_a
        # Match the P03 source-chain screen conservatively. These are additional
        # reservations, not a completed inventory or proof that P02's existing
        # load reserves exclude the same consumers.
        local = 0.024 if domain == "digital" else 0.008
        current = maximum_cap_f * slew_max + load + local
        ramp = vin / slew_max
        ecap = 0.5 * maximum_cap_f * vin**2
        eload = 0.5 * vin * (load + local) * ramp
        rows.append(
            dict(
                domain=domain,
                master_ref=ref,
                native_timing_cap_ref=cap["ref"],
                native_timing_cap=cap["part"],
                maximum_network_capacitance_requirement_f=maximum_cap_f,
                actual_network_inventory_accepted=False,
                timing_cap_min_f=cmin,
                timing_cap_max_f=cmax,
                c0g_temperature_box_ppm_per_c=30,
                temperature_span_from25c_max_c=100,
                guaranteed_idvdt_a=[2.6e-6, 9e-6],
                output_slew_v_s=[slew_min, slew_max],
                source_voltage_screen_v=vin,
                constant_external_load_bound_a=load,
                additional_local_load_allocation_a=local,
                local_load_inventory_closed=False,
                overlap_with_existing_p02_reserves_reconciled=False,
                first_master_current_max_a=current,
                fast_ramp_time_s=ramp,
                initial_pass_power_w=vin * current,
                capacitive_pass_energy_j=ecap,
                constant_load_pass_energy_j=eload,
                total_pass_energy_j=ecap + eload,
                no_division_by_parallel_channel_count=True,
                input_maximum_falling_slew_requirement_v_us=10,
                input_maximum_rising_slew_requirement_v_us=100,
                input_waveforms_measured=False,
                thermal_soa_qualified=False,
                thermal_source=SOURCE + "#page=42",
                thermal_limitations=[
                    "Fig6-26/8-6 supplies a typical time-to-shutdown curve, not guaranteed pulseSOA or transientZtheta",
                    "TSD154C is typical only; no minimum margin at worst startingjunctiontemperature is established",
                    "Triangular passpower requires convolution/validatedthermalmodel; average or peakconstantpower alone is insufficient",
                    "Every follower waits for predecessorSPLYGD; master alone bears the full connected capacitance/load",
                    "Actual downstreamreset/converter-enable behavior and maximumcapacitance inventory are unaccepted",
                ],
            )
        )
    return rows


def main():
    rows = screen()
    manifest = dict(
        rows=rows,
        build_ready=False,
        physical_qualified=False,
        source_sha256={
            str(Path(__file__).relative_to(ROOT.parents[3])): hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest()
        },
    )
    (ROOT / "generated/startup-screen.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for row in rows:
        print(
            row["domain"],
            row["first_master_current_max_a"],
            row["initial_pass_power_w"],
            row["total_pass_energy_j"],
        )


if __name__ == "__main__":
    main()
