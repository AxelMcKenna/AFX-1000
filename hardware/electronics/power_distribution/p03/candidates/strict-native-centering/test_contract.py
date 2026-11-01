"""Cross-artifact regression gates for the unaccepted private P03 candidate."""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from reproduce import check
from verify import identities

ROOT = Path(__file__).resolve().parent


def native_closed(drc):
    return (
        "ignored_checks" in drc
        and not drc["ignored_checks"]
        and not drc["violations"]
        and not drc["unconnected_items"]
        and not drc["schematic_parity"]
    )


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = json.loads((ROOT / "generated/current-native.json").read_text())
        cls.drc = json.loads((ROOT / "generated/drc.json").read_text())

    def test_raw_strict_empty_ignored_and_negative_controls(self):
        self.assertTrue(native_closed(self.drc))
        missing = copy.deepcopy(self.drc)
        del missing["ignored_checks"]
        self.assertFalse(native_closed(missing))
        ignored = copy.deepcopy(self.drc)
        ignored["ignored_checks"] = [dict(key="track_not_centered_on_via")]
        self.assertFalse(native_closed(ignored))
        issue = copy.deepcopy(self.drc)
        issue["violations"] = [dict(type="track_not_centered_on_via")]
        self.assertFalse(native_closed(issue))
        p = json.loads((ROOT / "power_p03.kicad_pro").read_text())["board"]["design_settings"][
            "rule_severities"
        ]
        self.assertTrue(
            all(
                p[k] == "error"
                for k in [
                    "missing_courtyard",
                    "track_not_centered_on_via",
                    "tuning_profile_track_geometries",
                    "footprint_filters_mismatch",
                    "footprint_type_mismatch",
                ]
            )
        )

    def test_fresh_native_board_and_uncapped_source(self):
        self.assertEqual(
            hashlib.sha256((ROOT / "power_p03.kicad_pcb").read_bytes()).hexdigest(), self.native["pcb_sha256"]
        )
        u = json.loads((ROOT / "generated/uncapped.json").read_text())
        self.assertEqual(u["uncapped_unconnected_count"], 0)
        self.assertEqual(u["raw_reported_unconnected_count"], 0)
        self.assertIn("RecalculateRatsnest", u["method"])
        self.assertTrue(all(x["returncode"] == 0 for x in self.native["native_commands"]))
        self.assertFalse(self.native["native_pin_value_mismatches"])

    def test_entire_physical_FP_via_stack_outline_preserved(self):
        i = identities()
        self.assertEqual(i["actual_FP_count"], 266)
        self.assertEqual(i["actual_via_count"], 1254)
        self.assertTrue(i["all_original_complete_FPs_exact"])
        self.assertTrue(i["all_original_complete_vias_exact"])
        self.assertTrue(i["board_setup_layer_stack_and_outline_exact"])

    def test_exact_source_delta_reproduces_actual_geometry(self):
        check()
        d = json.loads((ROOT / "generated/source-delta.json").read_text())
        self.assertEqual((len(d["removed"]), len(d["changed"]), len(d["added"])), (32, 139, 2))
        self.assertEqual(
            d["source_parent_pcb_sha256"], "db83a26f98e3638d7b1a723be5d54f71c4e3aaa5418021e5b9003afea810283d"
        )

    def test_circuit_values_part_selection_and_threshold_defect_unchanged(self):
        for n in [
            "components.json",
            "component-selections.json",
            "power_p03.kicad_sch",
            "power_p03.kicad_dru",
        ]:
            self.assertEqual((ROOT / n).read_bytes(), (ROOT / "sources/db83" / n).read_bytes(), n)
        self.assertTrue(self.native["known_POWER_RUN_loaded_threshold_defect_UNREPAIRED"])
        self.assertTrue(self.native["AX02_not_integrated"])
        self.assertFalse(self.native["release_ready"])

    def test_six_actual_front_authored_paths_no_vertical_fallback(self):
        p = json.loads((ROOT / "generated/six-front-paths-new.json").read_text())
        self.assertEqual(p["pcb_sha256"], self.native["pcb_sha256"])
        self.assertTrue(p["all_six_actual_front_paths_present"])
        self.assertEqual(len(p["six_paths"]), 6)
        self.assertTrue(
            all(
                x["exact_authored_front_track_path_present"]
                and not x["zones_or_vertical_or_via_pad_bridges_used"]
                for x in p["six_paths"]
            )
        )
        c = next(x for x in p["six_paths"] if x["cap"] == "C106" and x["pin"] == "2")
        self.assertEqual(c["minimum_authored_width_mm"], 0.5)
        self.assertGreater(
            c["actual_new_authored_centreline_length_mm"], c["old_receipt_centreline_length_mm"]
        )
        self.assertTrue((ROOT / "generated/aux-literal-current-failure.json").exists())

    def test_all16_original_direct_buck_links_still_present(self):
        p = json.loads((ROOT / "generated/buck-pairs-current.json").read_text())
        self.assertEqual(len(p["connections"]), 16)
        self.assertTrue(p["eight_native_direct_pairs_present"] and p["eight_native_hf_pairs_present"])
        self.assertTrue(all(x["matching_native_segment_uuids"] for x in p["connections"]))

    def test_force_necks_and_material_models_remain_explicit_receiving(self):
        d = json.loads((ROOT / "generated/centering2-delta.json").read_text())["explicit_P19_two_short_necks"]
        self.assertEqual(d["new_width_mm"], 0.6)
        self.assertEqual(len(d["length_mm"]), 2)
        self.assertFalse(d["material_geometry_temperature_and_coupled_network_bound_accepted"])
        self.assertTrue(d["not_added_to_authoritative_source_load_a"])
        c = json.loads((ROOT / "construction.json").read_text())
        self.assertEqual(c["via_wall_minimum_required_um"], 50)
        self.assertEqual(c["outer_finished_copper_minimum_required_um"], 85)
        self.assertEqual(c["inner_finished_copper_minimum_required_um"], 70)
        self.assertFalse(c["fabricator_dfm_approved"])
        self.assertFalse(c["actual_microsection_verified"])
        self.assertFalse(c["construction_acceptance_inherited"])
        self.assertTrue(c["native_filling_capping_metadata_reconciliation_pending"])


if __name__ == "__main__":
    unittest.main()
