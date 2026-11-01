"""Read-only validation of the bounded NC01 preselection snapshot."""

import json
import math
from pathlib import Path

from .local_fanout import certify
from .study import ROOT, library_contract, sha


def fanout_errors(f, analysis):
    errors = []
    wire = analysis["wire_candidates"]["Alpha3049"]
    chord = 14 * (1 - math.cos(math.pi / 256))
    threshold = (wire["OD_mm"][1] + 0.24 + 0.25 + 0.010 + 2 * chord) / (math.cos(math.pi / 64) ** 2)
    if (
        f["source_required_radius_mm"] != wire["minimum_centerline_bend_radius_mm"]
        or f["true_minimum_radius_mm"] != 14
        or f["wire_OD_max_mm"] != wire["OD_mm"][1]
        or f["N_arc_segments"] != 64
        or abs(f["chord_bound_mm"] - chord) > 1e-14
        or abs(f["required_centerline_separation_mm"] - threshold) > 1e-12
    ):
        errors.append("wrong-wire-curve-bounds")
    if [r["circuit"] for r in f["routes"]] != list(range(1, 31)):
        errors.append("wrong-circuit-coverage")
    for r in f["routes"]:
        n = r["circuit"]
        x, y, z = r["exit_xyz_mm"]
        L = r["straight_mm"]
        R = r["radius_mm"]
        if R != 14 or L != (10 if n % 2 else 0):
            errors.append("changed-bend-or-stagger")
        if [x, y, z] != [2 * ((n - 1) // 2), 0, 2 * ((n - 1) % 2)]:
            errors.append("wrong-physical-exit-pin")
        expected = [[x, y, z]]
        if L:
            expected.append([x, y - L, z])
        expected += [
            [x, y - L - R * math.sin(j * math.pi / 128), z + R * (1 - math.cos(j * math.pi / 128))]
            for j in range(1, 65)
        ]
        if len(expected) != len(r["native_points"]) or any(
            abs(a - b) > 1e-10 for p, q in zip(expected, r["native_points"]) for a, b in zip(p, q)
        ):
            errors.append("point-path-not-certified-curve")
    return errors


def run():
    errors = []
    counts = {}
    capture = json.loads((ROOT / "capture.json").read_text())
    for n, h in capture["copied_sha256"].items():
        if sha(ROOT / n) != h:
            errors.append("captured-input:" + n)
    for name in [
        "analysis.json",
        "local-PHD30-fanout.json",
        "force-pigtail-proposal.json",
        "native-footprints.json",
    ]:
        d = json.loads((ROOT / "generated" / name).read_text())
        for p, h in d["source_sha256"].items():
            if not Path(p).is_file() or sha(Path(p)) != h:
                errors.append(name + ":source:" + p)
    a = json.loads((ROOT / "generated/analysis.json").read_text())
    if len(a["NF05S_pincontract"]["J1"]) != 30 or a["captured_NF05S_parts"] != 249:
        errors.append("wrong-249-parent-scope")
    if a["force_contact_screens"]["PHD_PH_environment"]["within_allocation"]:
        errors.append("false-force-contact-pass")
    if a["connector_facts"]["PHD_two_circuit_candidate"]["catalog_available"]:
        errors.append("invented-PHD2")
    for p, h in a["primary_local_sha256"].items():
        if sha(Path(p)) != h:
            errors.append("primary-catalog:" + p)
    fp = ROOT / "sources/repository/KiCad/JST_PHD_B30B-PHDSS_2x15_P2.00mm_Vertical.kicad_mod"
    try:
        library_contract(fp)
    except AssertionError:
        errors.append("actual-PHD30-pad-contract")
    f = json.loads((ROOT / "generated/local-PHD30-fanout.json").read_text())
    errors += fanout_errors(f, a)
    pairs = 0
    for i, x in enumerate(f["routes"]):
        if x["radius_mm"] < f["source_required_radius_mm"]:
            errors.append("bend-radius")
        for y in f["routes"][i + 1 :]:
            result = certify(x, y, f["required_centerline_separation_mm"])
            pairs += 1
            if not result["certified"]:
                errors.append("continuous-pair")
            if result != f["certificates"].get(str(x["circuit"]) + "-" + str(y["circuit"])):
                errors.append("stored-certificate-does-not-replay")
    if pairs != 435 or len(f["certificates"]) != 435 or f["sampled_minimum_used"]:
        errors.append("missing-continuous-coverage")
    native = json.loads((ROOT / "generated/native-footprints.json").read_text())
    if len(native["footprints"]) != 2 or sum(len(v["pads"]) for v in native["footprints"].values()) != 32:
        errors.append("actual-native-parser-coverage")
    if not native["parser_only"] or native["PCB_native_DRC_performed"]:
        errors.append("false-PCB-DRC-inheritance")
    p = json.loads((ROOT / "generated/post-run-native-tool-provenance.json").read_text())
    if p["native_receipt_sha256"] != sha(ROOT / "generated/native-footprints.json"):
        errors.append("native-receipt-binding")
    # Installed binary freshness is diagnostic; the copied part geometry/pin
    # data remain explicit. It never substitutes for native parser evidence.
    counts["post_run_tool_files_still_matching"] = sum(
        Path(n).is_file() and sha(Path(n)) == h for n, h in p["tool_files_sha256"].items()
    )
    counts.update(
        continuous_pairs_replayed=pairs, native_footprints=2, native_pads=32, captured_parent_parts=249
    )
    return dict(
        errors=errors,
        counts=counts,
        evidence_consistent=not errors,
        current_261_successor_adopted=False,
        wholeunit_fit_performed=False,
        force_strain_proposal_complete=False,
        physical_qualified=False,
        electrical_qualified=False,
        fabrication_released=False,
    )


if __name__ == "__main__":
    d = run()
    print(json.dumps(d, indent=2))
    raise SystemExit(bool(d["errors"]))
