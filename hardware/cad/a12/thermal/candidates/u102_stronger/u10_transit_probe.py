"""Source-bound U10 bottom-transit recovery diagnostic; four electrical opens remain."""

import json
from pathlib import Path

from hardware.cad.a12.thermal.candidates.u10.candidate import geometry_inventory
from hardware.cad.a12.thermal.candidates.u10.network import solve
from hardware.cad.a12.thermal.generate import REPO, sha
from hardware.electronics.common.sexpr import read_sexpr

ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / "sources/closed-U10/power_p03.kicad_pcb"
    pcb = ROOT / "u10_B_trial/power_p03.kicad_pcb"
    before = geometry_inventory(read_sexpr(source.read_text()))
    after = geometry_inventory(read_sexpr(pcb.read_text()))
    assert before["footprints"] == after["footprints"] and before["vias"] == after["vias"]
    for layer in ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]:
        assert [x for x in before["tracks"] if x[3] == layer] == [x for x in after["tracks"] if x[3] == layer]
    receipt = json.loads((ROOT / "u10_B_trial/receipt.json").read_text())
    assert receipt["hard_drc"] == receipt["parity"] == receipt["erc"] == 0 and receipt["opens"] == 4
    c = json.loads((ROOT / "u10_B_trial/construction.json").read_text())
    assert c["pcb_sha256"] == sha(pcb)
    d = c["dielectric_nominal_mm"]
    paths = [
        Path(__file__).resolve(),
        source,
        pcb,
        ROOT / "u10_B_trial/receipt.json",
        ROOT / "u10_B_trial/construction.json",
        ROOT / "u10_transit_trial.py",
        ROOT / "generated/U10-bottom-transit-inspection.json",
        REPO / "hardware/cad/a12/thermal/candidates/u10/network.py",
        REPO / "hardware/cad/a12/thermal/analyze.py",
        REPO / "hardware/electronics/common/sexpr.py",
        REPO / "hardware/electronics/output_stage/check_placement.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}
    rows = []
    for grid in [160, 320]:
        r = solve(
            [190.1, 127.7, 193.75, 131.4],
            grid=grid,
            pcb_path=pcb,
            via_wall_um=50,
            power=0.6292218937818581,
            tim_k=4,
            tim_gap_mm=1.5,
            contact_c_per_w=2,
            copper_k=350,
            dielectric_override_mm=[v * (1.76 - 0.45) / sum(d) for v in d],
        )
        rows.append(r)
    report = dict(
        source_sha256=hashes,
        pcb_sha256=sha(pcb),
        results=rows,
        qualified=False,
        source_electrical_opens=4,
        conditional65plus2c=rows[-1]["conditional_junction_at_60c_base_c"] + 7,
        proposal="Restore only40 displacedBtransits forSHDN5V_DIG_SRC,N19_SET,N19_SRC using paths outsidecontact/inotherlayers; retain every actual foreignhole and quietAGNDbarrel",
        factory_and_source_noise_qualified=False,
        all_original_vias_and_non_B_tracks_verified_unchanged=True,
        package_and_TIM_bounds_guaranteed=False,
        neighbouring_device_cross_heating_and_whole_base_upper_bound=None,
    )
    assert all(sha(REPO / p) == h for p, h in hashes.items())
    (ROOT / "generated/U10-B-transit-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "actualrecovery",
        rows[-1]["conditional_junction_at_60c_base_c"],
        "65+2",
        report["conditional65plus2c"],
        "Barea",
        rows[-1]["sink_area_under_matching_bottom_copper_mm2"],
    )


if __name__ == "__main__":
    main()
