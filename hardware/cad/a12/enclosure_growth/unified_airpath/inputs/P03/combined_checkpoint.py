"""Verify actual combined-source composition and both local repair contracts."""

import hashlib
import json
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr
from . import aux_loop_check, buck_layout, composition, u102_checkpoint
from .spec import REPO


def validate(root):
    root = Path(root).resolve()
    counts = u102_checkpoint.validate(root)
    assert u102_checkpoint.validate_u10(root) == counts
    loops = aux_loop_check.validate(root)
    report = json.loads((root / "generated/composition.json").read_text())
    sources = []
    for name, digest in report["source_pcb_sha256"].items():
        source = (REPO / name).resolve()
        assert source.is_relative_to(REPO.resolve())
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, "Composition source is stale"
        sources.append(read_sexpr(source.read_text()))
    assert len(sources) == 3
    expected, proof = composition.merge(*sources)
    actual = read_sexpr((root / "power_p03.kicad_pcb").read_text())
    assert composition.inventory(expected) == composition.inventory(actual), "Authored merge changed"
    assert proof["exact_authored_object_edits"] == report["exact_authored_object_edits"]
    assert report["inherited_thermal_result_accepted"] is False
    pairs = buck_layout.pair_inventory(actual)
    assert pairs["eight_native_direct_pairs_present"] and pairs["eight_native_hf_pairs_present"]
    # The sealed AUX37fd source has TWO named adjacent field barrels. A third
    # historical site was removed by the actual local-cap repair; do not invent it.
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(actual, "net")}
    ground = {
        tuple(round(float(x) - 100, 6) for x in first(v, "at")[1:3])
        for v in children(actual, "via")
        if names.get(str(first(v, "net")[1]), str(first(v, "net")[-1])).lstrip("/") == "AGND"
    }
    assert {(25.35, 19.05), (25.85, 21.8)} <= ground
    assert (25.35, 21.8) not in ground
    domain_ground = {p for p in ground if 20 <= p[0] <= 32 and 15 <= p[1] <= 27}
    assert len(domain_ground) == 17
    return dict(
        native_counts=counts,
        source_and_authored_object_merge_verified=True,
        u102_direct_ep_count=9,
        u102_named_adjacent_field_barrel_count=2,
        u102_thermal_domain_local_mm=[20, 15, 32, 27],
        u102_actual_domain_agnd_through_via_count=len(domain_ground),
        direct_aux_loops=loops,
        native_buck_pairs=pairs,
        actual_thermal_and_return_reextraction_required=True,
        stability_startup_and_physical_qualified=False,
    )
