"""FH02 actual-export/interface and design-mutation checks, no silicon claim."""

import copy
import json
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.qualification.boards.fan_health.circuit.analyze import (
    analyze,
    latch_sequence,
    topology_findings,
)
from hardware.qualification.boards.fan_health.circuit.design import ROOT, sha

CAP = ROOT / "sources/repository"
FW = CAP / "hardware/qualification/boards/fan_health"
NF = CAP / "hardware/qualification/boards/startup_negative_circuit/compact/generated/analysis.json"


class Circuit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = json.loads((ROOT / "components.json").read_text())
        cls.by = {p["ref"]: p for p in cls.parts}
        cls.nf = json.loads(NF.read_text())["power"]
        cls.result = analyze(cls.parts, cls.nf)
        cls.native, cls.pins = netlist(ROOT / "generated/netlist.xml")

    def test_actual_native_export_matches_separately_declared_MCU_pin_contract(self):
        self.assertEqual(
            self.pins["U1"],
            {
                "1": "V3V3",
                "2": "XTAL1",
                "3": "XTAL2",
                "4": "MCU_RESET_N",
                "5": "MCU_TACH_R",
                "6": "MCU_HEALTH",
                "7": "ISP_MOSI",
                "8": "ISP_MISO",
                "9": "ISP_SCK",
                "10": "MCU_TACH_L",
                "11": "HEARTBEAT",
                "12": "TEMP_R_ADC",
                "13": "TEMP_L_ADC",
                "14": "GND",
            },
        )
        adapter = (FW / "firmware/attiny84a.c").read_text()
        for macro, port in {"HEARTBEAT": "PA2", "TACH_L": "PA3", "HEALTH": "PA7", "TACH_R": "PB2"}.items():
            self.assertRegex(adapter, r"#define\s+" + macro + r"\s+" + port + r"\b")
        for text in [
            "#define F_CPU 4000000UL",
            "CLKPR = 0;",
            "_BV(CS11)",
            "_BV(ADPS2) | _BV(ADPS1)",
            "lfuse != 0x7d || hfuse != 0xdd",
        ]:
            self.assertIn(text, adapter)

    def test_all_actual_native_pin_maps_and_ERC(self):
        self.assertEqual(set(self.native), set(self.by))
        for ref, p in self.by.items():
            self.assertEqual(self.native[ref].findtext("value"), p["part"])
            self.assertEqual(self.native[ref].findtext("footprint"), p["footprint"])
            for pin in p["pins"]:
                actual = self.pins[ref][pin["number"]]
                if pin["net"] is None:
                    self.assertTrue(actual.startswith("unconnected-"))
                else:
                    self.assertEqual(actual, pin["net"])
        raw = json.loads((ROOT / "generated/erc.json").read_text())
        self.assertFalse([v for s in raw["sheets"] for v in s["violations"]])

    def test_WD_retry_cannot_reclose_with_MCU_HEALTH_stuck_HIGH(self):
        events = [(True, False, True), (False, False, True), (False, True, True)]
        events += [(False, False, True), (False, True, True)] * 100
        states = latch_sequence(events)
        self.assertTrue(states[2]["permission"])
        self.assertTrue(all(s["latched_fault"] and not s["permission"] for s in states[3:]))
        self.assertTrue(
            latch_sequence(events + [(True, False, False), (False, True, True)])[-1]["permission"]
        )

    def test_3V3_only_fault_does_not_clear_RAW_latch(self):
        events = [(True, False, False), (False, True, True), (False, False, False), (False, True, True)]
        self.assertFalse(latch_sequence(events)[-1]["permission"])
        mutated = copy.deepcopy(self.parts)
        next(p for p in next(c for c in mutated if c["ref"] == "U8")["pins"] if p["number"] == "8")["net"] = (
            "V3V3"
        )
        self.assertFalse(topology_findings(mutated)["latch_independent_RAW5_power"])

    def test_first_WD_low_does_not_generate_false_clock_startup(self):
        seq = [(True, False, False), (False, False, False), (False, True, False), (False, True, True)]
        self.assertEqual([s["latched_fault"] for s in latch_sequence(seq)], [False] * 4)
        self.assertFalse(latch_sequence(seq)[-2]["permission"])
        self.assertTrue(latch_sequence(seq)[-1]["permission"])

    def test_startup_WD_does_not_drive_external_reset_flag(self):
        self.assertNotEqual(self.pins["U4"]["7"], self.pins["U1"]["4"])
        self.assertEqual(self.pins["U1"]["4"], self.pins["J5"]["5"])
        mutated = copy.deepcopy(self.parts)
        next(p for p in next(c for c in mutated if c["ref"] == "U1")["pins"] if p["number"] == "4")["net"] = (
            "WD_OK"
        )
        self.assertFalse(topology_findings(mutated)["startup_WD_does_NOT_create_MCU_EXTRF"])

    def test_correct_TLP_pins_and_ONLY_POWER_RUN_leaf(self):
        self.assertEqual(
            self.pins["U15"], {"1": "LED_A", "3": "LED_K", "4": "P03_POWER_RUN", "6": "E28_POWER_RUN"}
        )
        ports = {self.pins["J4"]["1"], self.pins["J4"]["2"]}
        self.assertEqual(ports, {"P03_POWER_RUN", "E28_POWER_RUN"})
        self.assertTrue(
            all("MASTER_ENABLE" not in str(v) for pins in self.pins.values() for v in pins.values())
        )
        e28 = json.loads(
            (CAP / "hardware/electronics/rail_disconnect/revision28/components.json").read_text()
        )
        native = {p["ref"]: {n["number"]: n["net"] for n in p["pins"]} for p in e28}
        self.assertEqual(native["J5"]["3"], "POWER_RUN")
        self.assertEqual(native["U29"]["7"], "E28_MASTER_ENABLE")
        self.assertEqual(native["R93"], {"1": "POWER_RUN", "2": "AGND"})
        _, exported = netlist(ROOT / "generated/captured-E28-netlist.xml")
        self.assertEqual(exported["J5"]["3"], "POWER_RUN")
        self.assertEqual(exported["R93"], {"1": "POWER_RUN", "2": "AGND"})
        self.assertEqual(exported["U29"]["7"], "E28_MASTER_ENABLE")
        _, p03 = netlist(
            CAP
            / "hardware/electronics/power_distribution/p03/candidates/aux-u10-combined/generated/netlist.xml"
        )
        self.assertEqual(p03["J106"]["3"], "POWER_RUN")

    def test_loaded_LED_and_permission_default_OFF(self):
        result = self.result
        self.assertGreaterEqual(result["LED"]["min_current_under_receiving_VF_VOL_a"], 0.0024)
        self.assertLess(result["LED"]["permission_Ioff10ua_plus_input5ua_pulldown_voltage_v"], 0.2)
        self.assertLess(result["LED"]["off_sink_Ioff_10ua_shunt_voltage_v"], 0.11)
        mutated = copy.deepcopy(self.parts)
        next(c for c in mutated if c["ref"] == "R13")["part"] = "47k"
        self.assertFalse(topology_findings(mutated)["LED_permission_loaded_OFF_pulldown"])
        next(p for p in next(c for c in mutated if c["ref"] == "R2")["pins"] if p["number"] == "2")["net"] = (
            "GND"
        )
        self.assertFalse(topology_findings(mutated)["LED_raw_feed_shunt_Ioff_sink"])

    def test_missing_latch_clock_or_wrong_D_are_detected(self):
        for ref, pin, value, key in [
            ("U8", "2", "GND", "latch_D_high_and_PRE_inactive"),
            ("U6", "6", "V3V3", "WD_raw_clock_power_isolation"),
            ("U15", "3", "GND", "ONLY_correct_leaf_contact_exact_TLP_pins"),
        ]:
            parts = copy.deepcopy(self.parts)
            next(p for p in next(c for c in parts if c["ref"] == ref)["pins"] if p["number"] == pin)[
                "net"
            ] = value
            self.assertFalse(topology_findings(parts)[key])

    def test_real_timeout_cap_and_clock_loading(self):
        self.assertEqual(self.by["C7"]["part"], "2.7nF 50V C0G C1206C272J5GACTU")
        self.assertTrue(self.result["watchdog"]["first_heartbeat_has20pct_timeout_headroom"])
        self.assertLess(
            self.result["watchdog"]["firmware_falling_edge_period_ms"] * 1.2,
            self.result["watchdog"]["timeout_interval_given_receiving_C_ms"][0],
        )
        self.assertAlmostEqual(self.result["crystal"]["implied_effective_stray_f"], 4.5e-12)
        self.assertEqual(self.result["crystal"]["complete_period_capture_error_receiving_engine_ticks"], 20)
        self.assertLess(self.result["sensors"]["max_filter_tau_receiving_s"] * 20, 0.020)

    def test_NEW_budget_delta_not_silent_old_pool_pass(self):
        b = self.result["budget"]
        self.assertFalse(b["fits_prior_2p4A_allocation"])
        self.assertTrue(b["fits_new_pool"])
        self.assertGreater(b["with20pct_a"], 0.019)
        self.assertLess(b["full_allocated_total_with_FH_guard_a"], 2.42)
        delta = self.result["source_delta"]
        self.assertAlmostEqual(delta["new_protected_power_increment_planning_w"], 0.12)
        self.assertAlmostEqual(delta["proposed_capacity_heat_w"], 37.40570585792509)
        old, new = delta["old_normal_feed_point"], delta["new_normal_feed_point_given_same_conditions"]
        self.assertGreater(new["feed_loss_w"], old["feed_loss_w"])
        self.assertAlmostEqual(new["plug_power_w"], new["board_received_power_w"] + new["feed_loss_w"])

    def test_package_pin_sets_and_source_captures(self):
        packages = json.loads((ROOT / "generated/package-review.json").read_text())
        self.assertEqual(len(packages["parts"]), 68)
        for p in packages["parts"]:
            self.assertEqual(p["pads"], p["expected_pins"])
            self.assertEqual(sha(ROOT / p["captured_path"]), p["sha256"])
        captured = json.loads((ROOT / "generated/captured-inputs.json").read_text())
        for path, digest in captured["repository_inputs_sha256"].items():
            self.assertEqual(sha(CAP / path), digest)

    def test_all_open_physical_claims_stay_open(self):
        r = self.result
        for key in ("physical_qualified", "fabrication_released", "production_released"):
            self.assertIs(r[key], False)
        self.assertIs(r["budget"]["proposed_DIG_revision_adopted"], False)
        self.assertIs(r["watchdog"]["first_heartbeat_and_full_ramps_measured"], False)
        self.assertIsNone(r["leaf"]["complete_turnoff_and_capacitor_discharge_bound_s"])
        self.assertIs(
            r["crystal"]["actual_drive_startup_pulling_aging_and_loaded_frequency_qualified"], False
        )


if __name__ == "__main__":
    unittest.main()
