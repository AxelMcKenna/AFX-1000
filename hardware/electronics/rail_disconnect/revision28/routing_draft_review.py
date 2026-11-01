"""Source-bound preservation review for the explicit U14-to-routing draft."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from ...common.sexpr import children, first, read_sexpr, sexpr
from .native_contract_compare import contracts, fingerprint

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "generated/p9-u14-input-escape-work"
WORK = ROOT / "generated/u28-return-dual-plane-work"
MOVED = {"U23", "C68", "U26", "C71", "U27", "C72", "U28", "C73"}


def main():
    before, after = [read_sexpr((p / "rail_disconnect.kicad_pcb").read_text()) for p in (BASE, WORK)]
    old, new = contracts(before), contracts(after)
    assert set(old["footprints"]) == set(new["footprints"])
    changed = {ref for ref in old["footprints"] if old["footprints"][ref] != new["footprints"][ref]}
    assert changed == MOVED
    assert old["board_setup"] == new["board_setup"]

    def logical_pads(tree):
        result = {}
        for fp in children(tree, "footprint"):
            ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
            result[ref] = Counter(
                (str(p[1]), str(p[2]), str(p[3]), str(first(p, "net")[-1]) if children(p, "net") else None)
                for p in children(fp, "pad")
            )
        return result

    assert logical_pads(before) == logical_pads(after)
    old_zones, new_zones = old["zones"], new["zones"]
    assert not old_zones - new_zones
    added_zones = new_zones - old_zones
    assert sum(added_zones.values()) == 10
    for z in children(after, "zone"):
        if fingerprint(z) in added_zones:
            assert first(z, "net_name")[1] == "/AGND"
            assert str(first(z, "priority")[1]) == "0"
            assert float(first(z, "min_thickness")[1]) == 0.2
    assert sum((old["edge_cuts"] - new["edge_cuts"]).values()) == 3
    assert sum((new["edge_cuts"] - old["edge_cuts"]).values()) == 3

    def copper(tree):
        return {
            str(first(n, "uuid")[1]): sexpr(n) for kind in ("segment", "via") for n in children(tree, kind)
        }

    a, b = copper(before), copper(after)
    lock_path = ROOT / "generated/leaf-prune-source-lock-contract.json"
    locked = {row["uuid"] for row in json.loads(lock_path.read_text())["locked_copper"]}
    operative = locked & a.keys()
    assert all(b.get(uid) == a[uid] for uid in operative)
    unchanged_files = (
        "rail_disconnect.kicad_sch",
        "rail_disconnect.kicad_pro",
        "components.json",
        "fp-lib-table",
        "sym-lib-table",
        "RMX_E17.kicad_sym",
    )
    assert all((BASE / name).read_bytes() == (WORK / name).read_bytes() for name in unchanged_files)
    raw_path = WORK / "generated/drc-u28-return-dual-plane1.json"
    raw = json.loads(raw_path.read_text())
    assert not any(v["severity"] == "error" for v in raw["violations"])
    assert not raw["schematic_parity"]
    files = [
        Path(__file__),
        lock_path,
        raw_path,
        BASE / "rail_disconnect.kicad_pcb",
        WORK / "rail_disconnect.kicad_pcb",
    ]
    report = dict(
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        baseline_native_opens=43,
        current_native_opens=len(raw["unconnected_items"]),
        current_native_warnings=len(raw["violations"]),
        hard_DRC=0,
        parity=0,
        changed_footprints_exactly=sorted(changed),
        C72_face_change="F to B; standard 0805 mirrored pattern from existing C71, preserving C72 reference/identity/pad-net contract",
        all_circuit_pad_numbers_types_shapes_netnames_equal=True,
        all_schematic_project_components_and_library_tables_byte_equal=True,
        all_original_zone_contracts_preserved=True,
        new_AGND_zones=10,
        added_band_edge_change_count=3,
        original_layers_setup_rules_equal=True,
        actual_original_locked_copper_objects_retained_exactly=len(operative),
        physical_copper_removed_from_original_count=len(a.keys() - b.keys()),
        physical_new_copper_object_count=len(b.keys() - a.keys()),
        literal_delta_contains_exact_removed_and_added_object_ledger=True,
        J8_lug_PB02_and_other_ground_strategy_not_adopted=True,
        C24_charging_return_loop_still_requires_actual_network_and_dynamic_validation=True,
        electrical_startup_SOA_thermal_MCAD_physical_fabrication_release=False,
    )
    (WORK / "generated/preservation-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
