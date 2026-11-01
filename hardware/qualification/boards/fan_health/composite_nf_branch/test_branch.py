import copy
import json
import unittest
import xml.etree.ElementTree as ET

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import children, first, read_sexpr

from .analyze import ROOT, analyze, current_interval, sha
from .validate import footprints, topology, validate


class ProtectedNFBranch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = analyze()
        cls.tree = read_sexpr((ROOT / "fan_power_health.kicad_pcb").read_text())
        _, cls.pins = netlist(ROOT / "generated/netlist.xml")

    def test_actual_native_parent_and_stage(self):
        r = validate(self.tree)
        self.assertEqual(r["parts"], 91)
        self.assertTrue(r["parent84_complete_footprints_exact"])
        self.assertTrue(r["parent_all_copper_exact"])

    def test_primary_physical_map_and_manufacturer_lands(self):
        tree = ET.parse(ROOT / "generated/netlist.xml").getroot()
        lib = {(x.get("lib"), x.get("part")): x for x in tree.findall("libparts/libpart")}
        for c in tree.findall("components/comp"):
            if c.get("ref") not in ["U201", "U301", "U401"]:
                continue
            src = c.find("libsource")
            pins = {
                p.get("num"): p.get("name")
                for p in lib[(src.get("lib"), src.get("part"))].findall("pins/pin")
            }
            self.assertEqual(
                pins, {"1": "IN", "2": "GND", "3": "EN", "4": "FAULT_N", "5": "ILIM", "6": "OUT"}
            )
        fp = read_sexpr((ROOT / "FPC01.pretty/TI_DBV0006A.kicad_mod").read_text())
        centers = {
            "1": [-1.3, -0.95],
            "2": [-1.3, 0],
            "3": [-1.3, 0.95],
            "4": [1.3, 0.95],
            "5": [1.3, 0],
            "6": [1.3, -0.95],
        }
        for p in children(fp, "pad"):
            self.assertEqual(list(map(float, first(p, "size")[1:])), [1.1, 0.6])
            self.assertEqual(list(map(float, first(p, "at")[1:])), centers[p[1]])

    def test_parent_clock_copper_and_pose_mutations_rejected(self):
        b = copy.deepcopy(self.tree)
        t = next(x for x in children(b, "segment") if "XTAL" in str(first(x, "net")[1]))
        first(t, "end")[1] = "50"
        with self.assertRaises(AssertionError):
            validate(b)
        b = copy.deepcopy(self.tree)
        first(footprints(b)["U1"], "at")[1] = "48.6"
        with self.assertRaises(AssertionError):
            validate(b)

    def test_clip_cannot_be_deleted_or_accept_copper(self):
        b = copy.deepcopy(self.tree)
        z = next(
            z
            for z in children(b, "zone")
            if children(z, "name") and str(first(z, "name")[1]).startswith("MOUNT_CLIP_")
        )
        first(first(z, "keepout"), "vias")[1] = "allowed"
        with self.assertRaises(AssertionError):
            validate(b)

    def test_output_cannot_bypass_current_limiter_or_remap_ground(self):
        b = copy.deepcopy(self.pins)
        b["J401"]["1"] = "FAN5V_IN"
        self.assertTrue(topology(b))
        b = copy.deepcopy(self.pins)
        b["C403"]["2"] = "NF_RAW5"
        self.assertTrue(topology(b))

    def test_actual_resistor_primary_range_and_complete_tolerance(self):
        for bad in [249000, 300000, 10000]:
            with self.assertRaises(ValueError):
                current_interval(bad, 0.01)
        lo, hi = self.a["ILIM"]["full_temp_process_equation1_interval_a"]
        self.assertGreater(lo, 1.2 * self.a["normal"]["NF_RAW5_guarded_a"])
        self.assertLess(hi, 0.150)
        self.assertEqual(self.a["ILIM"]["actual_resistor_interval_ohm"], [217800, 222200])

    def test_source_load_counted_once_and_inside_existing_plan(self):
        n = self.a["normal"]
        self.assertAlmostEqual(
            n["full_known_DIG_guarded_a"] - n["extra_branch_guarded_a"],
            json.loads((ROOT / "sources/NF05R/generated/analysis.json").read_text())["power"][
                "full_known_DIG_guarded_a"
            ],
        )
        self.assertAlmostEqual(n["FPC_input_total_guarded_a"] + 1.984, n["full_known_DIG_guarded_a"])
        self.assertAlmostEqual(n["NF_shared_AGND_arithmetic_receiving_a"] - n["NF_RAW5_guarded_a"], 0.014)
        self.assertAlmostEqual(
            n["FPC_shared_return_arithmetic_receiving_a"] - n["FPC_input_total_guarded_a"], 0.014
        )
        self.assertLess(n["full_known_DIG_guarded_a"], 2.44)
        self.assertFalse(n["complete_hot_current_and_DIG_PDN_accepted"])

    def test_input_and_limited_output_caps_not_combined_for_charge_time(self):
        s = self.a["startup"]
        self.assertGreaterEqual(
            s["local_input_effective_minimum_receiving_f"], s["primary_minimum_input_bypass_f"]
        )
        self.assertAlmostEqual(s["whole_source_known_external_partial_subtotal_f"], 0.971e-6)
        self.assertAlmostEqual(s["limited_output_cap_known_partial_subtotal_f"], 0.718e-6)
        self.assertLess(s["target_with20pct_a"], self.a["ILIM"]["full_temp_process_equation1_interval_a"][0])
        self.assertIsNone(s["ISO_startup_current_or_input_burst_guaranteed_a"])
        self.assertIsNone(s["full_external_internal_wire_hot_capacitance_upper_f"])

    def test_PH_upper_board_thickness_scenario_is_failed_not_pass(self):
        c = self.a["connector"]
        self.assertGreater(c["inherited_receiving_maximum_PCB_mm"], c["primary_PCB_thickness_mm"][1])
        self.assertTrue(c["inherited1p76_PCB_scenario_status"].startswith("FAILED"))
        self.assertTrue(c["actual_max1p6_stack_or_alternate_connector_required"])

    def test_timing_thermal_and_FAULT_flag_do_not_invent_hardoff(self):
        self.assertIsNone(self.a["fault"]["guaranteed_loaded_cutoff_upper_s"])
        self.assertIsNone(self.a["fault"]["full_fault_energy_upper_j"])
        self.assertFalse(self.a["fault"]["sustained_fault_thermal_cycle_and_RESET_rearm_accepted"])
        self.assertFalse(self.a["thermal"]["local_junction_and_installed_cooling_qualified"])

    def test_actual_reference_plane_and_native_raw_reports(self):
        n = json.loads((ROOT / "native-reference-check.json").read_text())
        self.assertEqual(len(n["actual_GND_pads_connected_to_actual_In1"]), 75)
        self.assertEqual(n["vias"], 136)
        self.assertEqual(n["PCB_sha256"], sha(ROOT / "fan_power_health.kicad_pcb"))
        for name in ["filled-drc", "final-drc"]:
            r = json.loads((ROOT / "generated" / f"{name}.json").read_text())
            for k in ["violations", "unconnected_items", "schematic_parity", "ignored_checks"]:
                self.assertFalse(r[k], (name, k))

    def test_all_parent_sources_and_current_source_bound(self):
        for name, d in json.loads((ROOT / "sources/manifest.json").read_text()).items():
            self.assertEqual(sha(ROOT / "sources" / name), d, name)
        for name, d in json.loads((ROOT / "generated/analysis.json").read_text())["source_sha256"].items():
            self.assertEqual(sha(ROOT / name), d, name)
        for folder in ["composite", "composite_mount"]:
            p = ROOT.parent / folder
            for name, d in json.loads((p / "handoff.json").read_text())["files_sha256"].items():
                self.assertEqual(sha(p / name), d, (folder, name))
        if (ROOT / "handoff.json").exists():
            for name, d in json.loads((ROOT / "handoff.json").read_text())["files_sha256"].items():
                self.assertEqual(sha(ROOT / name), d, name)


if __name__ == "__main__":
    unittest.main()
