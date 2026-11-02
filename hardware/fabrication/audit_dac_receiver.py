"""Source-bound circuit and local-feedback checks for the first E08 layout."""

import argparse
import json
from pathlib import Path

from hardware.electronics.adc_driver.pcb.paths import normalized
from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.dac_receiver.verify import CONTRACT, EXPECTED, number
from hardware.electronics.rail_disconnect.routing.check import copper_path
from hardware.fabrication.audit_candidate import authored, native_evidence_errors, sha

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication"
SOURCE = REPO / "hardware/electronics/dac_receiver"
PLACEMENT = ROOT / "staging/dac-receiver-placement-native-02"
ROUTED = ROOT / "staging/dac-receiver-closed-native-01"


def check():
    receipt = json.loads((ROUTED / "review.json").read_text())
    assert not native_evidence_errors(ROUTED / "dac_receiver.kicad_pro", receipt)
    assert receipt["status"]["native_closed"] and receipt["uncapped_open_connections"] == 0
    original, original_pins = netlist(SOURCE / "generated/netlist.xml")
    current, current_pins = netlist(ROUTED / "netlist.xml")
    assert original_pins == current_pins == CONTRACT
    assert set(original) == set(current) and len(current) == 60
    for ref in current:
        for key in ("value", "footprint"):
            assert original[ref].findtext(key) == current[ref].findtext(key), (ref, key)
        if ref in EXPECTED:
            assert abs(number(current[ref].findtext("value")) / EXPECTED[ref] - 1) < 1e-10
    before, after = [read_sexpr((p / "dac_receiver.kicad_pcb").read_text()) for p in (PLACEMENT, ROUTED)]
    # Native refills change zone caches and session imports add copper. All
    # placed component, outline and authored-plane geometry remains identical.
    for tag in ("footprint", "gr_line", "zone"):
        assert [authored(n) for n in children(before, tag)] == [authored(n) for n in children(after, tag)], tag
    assert not children(before, "segment") and not children(before, "via")
    assert len(children(after, "footprint")) == 64
    assert {first(s, "layer")[1] for s in children(after, "segment")} <= {"F.Cu", "B.Cu"}
    tree = normalized(after)
    paths = []

    def path(net, start, end, kind):
        length = copper_path(tree, net, (*start, 0), (*end, 0), .2)
        paths.append(dict(kind=kind, net=net, start=list(start), end=list(end),
                          whole_segment_chain_length_mm=length, layer="F.Cu"))

    for ci, ch in enumerate(("L", "R")):
        for op, ip, r, c, suffix in ((1, 2, 1 + 12 * ci, 1 + 5 * ci, "P"),
                                    (7, 6, 2 + 12 * ci, 2 + 5 * ci, "N")):
            for ref in ("R" + str(r), "C" + str(c)):
                path("IV_" + suffix + "_" + ch, ("U" + str(ci + 1), op), (ref, 2), "I/V output feedback")
                path("DAC_" + ch + suffix, ("U" + str(ci + 1), ip), (ref, 1), "I/V summing input")
        op, ip = (1, 2) if ci == 0 else (7, 6)
        for u, r, c, output, input_net in (
            ("U3", 7 + 12 * ci, 3 + 5 * ci, "CM_DRV_" + ch, "CM_SUM_" + ch),
            ("U4", 10 + 12 * ci, 4 + 5 * ci, "RX_OUT_" + ch, "RX_NEG_" + ch),
        ):
            for ref in ("R" + str(r), "C" + str(c)):
                path(output, (u, op), (ref, 2), "Common-mode/receiver output feedback")
                path(input_net, (u, ip), (ref, 1), "Common-mode/receiver input feedback")
        path("BUF_OUT_" + ch, ("U5", op), ("U5", ip), "Buffer unity feedback")
    assert len(paths) == 34
    drill = json.loads((ROUTED / "smd-drill-review.json").read_text())
    assert all(sha(Path(p)) == digest for p, digest in drill["source_sha256"].items())
    assert drill["no_drilled_hole_overlap_with_SMD_copper"]
    source_paths = [Path(__file__), SOURCE / "generated/netlist.xml", SOURCE / "dependencies.json",
                    PLACEMENT / "dac_receiver.kicad_pcb", ROUTED / "dac_receiver.kicad_pcb",
                    ROUTED / "netlist.xml", ROUTED / "review.json", ROUTED / "smd-drill-review.json",
                    REPO / "hardware/electronics/dac_receiver/verify.py",
                    REPO / "hardware/electronics/rail_disconnect/routing/check.py",
                    REPO / "hardware/electronics/adc_driver/pcb/paths.py"]
    return dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in source_paths},
        electrical_parts=60, mechanical_mounts=4, original_circuit_values_pin_nets_and_footprints_exact=True,
        placed_geometry_and_authored_planes_exact=True, native_counts=receipt["status"]["counts"],
        all_native_checks_enabled=True, segments=len(children(after, "segment")),
        conventional_through_vias=len(children(after, "via")), signal_layers=["F.Cu", "B.Cu"],
        AGND_plane_layers=["In1.Cu", "In2.Cu"], front_copper_feedback_chains=paths,
        feedback_length_definition="Sum of whole segments in a connected front-centreline chain; includes segment overhangs, not extracted parasitics",
        maximum_feedback_chain_mm=max(p["whole_segment_chain_length_mm"] for p in paths),
        minimum_drill_edge_to_SMD_copper_mm=drill["minimum_drill_edge_to_SMD_copper_mm"],
        gain_and_raw_DAC_scale_resolved=False, final_codec_colocation_complete=False,
        analog_stability_noise_distortion_and_thermal_qualified=False,
        enclosure_fit_qualified=False, manufacturing_process_accepted=False,
        physical_board_partition_complete=False, fabrication_released=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare saved evidence without writing")
    args = parser.parse_args()
    report = check()
    output = ROUTED / "layout-handoff.json"
    if args.check:
        assert json.loads(output.read_text()) == report, "Missing or stale layout handoff"
    else:
        with output.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print("E08: unchanged60-part circuit, zero native findings/opens, 34 front feedback chains;")
    print(report["segments"], "segments,", report["conventional_through_vias"], "vias; integration/ESS data still required")
