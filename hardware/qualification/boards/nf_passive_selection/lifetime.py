"""Additional ordinary/feed resistor error scenarios, not life guarantees."""

import argparse
import hashlib
import json
from pathlib import Path

from hardware.qualification.boards.nf_passive_selection import selection

ROOT = Path(__file__).resolve().parent


def tnpw(ohm, hours):
    life = {1000: (0.0005, 0.01), 8000: (0.001, 0.02), 225000: (0.003, 0.05)}[hours]
    terms = dict(
        initial=0.001,
        TCR_65K=25e-6 * 65,
        endurance=life[0] + life[1] / ohm,
        solder_heat=0.0002 + 0.01 / ohm,
        damp_heat=0.001 + 0.01 / ohm,
    )
    total = sum(terms.values())
    return dict(
        terms=terms,
        total_fraction=total,
        hours=hours,
        complete0p5_planning_met=total <= 0.005,
        complete3_planning_met=total <= 0.03,
        separate_test_limit_sum_NOT_joint_installed_guarantee=True,
    )


def analysis():
    cases = {
        ref: {str(h): tnpw(ohm, h) for h in [1000, 8000, 225000]}
        for ref, ohm in {"R92": 11300, "R93": 49.9, "R94": 10000, "R97": 240}.items()
    }
    feed_terms = dict(
        initial=0.01,
        TCR_65K=100e-6 * 65,
        endurance_1000h=0.01 + 0.05 / 402,
        solder_heat=0.0025 + 0.05 / 402,
        damp_heat=0.01 + 0.05 / 402,
    )
    alternative_terms = dict(
        initial=0.001,
        TCR_65K=25e-6 * 65,
        endurance_1000h=0.001 + 0.01 / 402,
        solder_heat=0.0005 + 0.01 / 402,
        damp_heat=0.001 + 0.01 / 402,
    )
    return dict(
        revision="NP01-additional-resistor-life-scenarios",
        film_enclosure_C=[0, 85],
        reference_temperature_C=20,
        TNPW_general_mode_125C_film_max=True,
        ordinary_TNPW=cases,
        R93_concrete_alternative=dict(
            MPN="TNPU060349R9AZEN00",
            family="TNPU0603",
            ohm=49.9,
            initial_fraction=0.0005,
            TCR_ppm_per_K=5,
            catalog_supported_order_code=True,
            body_max_mm=[1.7, 0.95, 0.55],
            project_seat_mm=0.1,
            projection_requirement_mm=0.65,
            land="TNPU0603_IPC28950",
            drop_in=False,
            adopted=False,
            planning_8000h=selection.scenario(49.9, 0.0005, 5, 8000),
            alternative_keep0805_and_relax_trim_error_requires_UV_ratio_rerun=True,
        ),
        CRCW402_1000h=dict(
            terms=feed_terms,
            total_fraction=sum(feed_terms.values()),
            complete3pct_planning_met=sum(feed_terms.values()) <= 0.03,
            source="vishay-CRCW-20035.pdf pp8,10",
        ),
        PRG402_1000h_option=dict(
            MPN="PRG5025P-4020-B-T4",
            terms=alternative_terms,
            total_fraction=sum(alternative_terms.values()),
            complete3pct_planning_met=sum(alternative_terms.values()) <= 0.03,
            source="susumu-current-catalog.pdf printed28",
            actual_power_board_and_land_hold=True,
        ),
        scenarios_omit_any_unselected_test_or_installed_effect_NOT_complete_worst_case=True,
        test_limits_retain_original_test_conditions=True,
        no_new_service_life_requirement_approved=True,
        electrical_qualified=False,
        physical_qualified=False,
        production_adopted=False,
    )


def build(output):
    if output.exists():
        raise RuntimeError("Refusing to overwrite saved life scenario")
    d = analysis()
    sources = [
        Path(__file__),
        Path(selection.__file__),
        ROOT / "sources/primary/vishay-TNPW-28758.pdf",
        ROOT / "sources/primary/vishay-TNPU-28779.pdf",
        ROOT / "sources/primary/vishay-CRCW-20035.pdf",
        ROOT / "sources/primary/susumu-current-catalog.pdf",
    ]
    d["source_sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    output.write_text(json.dumps(d, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                R93_complete0p5_at8000h=d["ordinary_TNPW"]["R93"]["8000"]["complete0p5_planning_met"],
                R93_alternative_adopted=False,
                electrical_qualified=False,
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
