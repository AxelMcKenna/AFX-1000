"""Meaningful topology, state and receiving-corner mutation checks."""

import copy
import json
import unittest

from .analyze import ROOT, analyze, armed_state, sha, timing
from .review import main, validate


class StandaloneSequence(unittest.TestCase):
    def test_source_and_native_receipt_freshness(self):
        for name,digest in json.loads((ROOT/'sources/manifest.json').read_text()).items():
            self.assertEqual(sha(ROOT/'sources'/name),digest,name)
        r=json.loads((ROOT/'generated/native-review.json').read_text())
        for group in ['source_sha256','artifact_sha256']:
            for name,digest in r[group].items():
                self.assertEqual(sha(ROOT/name),digest,name)

    def test_actual_native_export_cone(self):
        main()

    def test_watchdog_missing_safe_not_masked_by_arm(self):
        _, pins = main()
        p = copy.deepcopy(pins)
        p["U35"]["12"] = "N19_ARM_CONDITIONED"
        self.assertTrue(validate(p))
        p = copy.deepcopy(pins)
        p["U38"]["12"] = "N12_ARM_CONDITIONED"
        self.assertTrue(validate(p))

    def test_safe_fall_does_not_erase_arm_fault(self):
        self.assertFalse(armed_state(False, False, False))
        self.assertFalse(armed_state(False, True, False))
        state = armed_state(False, True, True)
        self.assertTrue(state)
        for _ in range(100):
            state = armed_state(state, True, False)
            self.assertTrue(state)
        self.assertFalse(armed_state(state, False, True))

    def test_sequential_not_parallel_start(self):
        _, pins = main()
        p = copy.deepcopy(pins)
        p["U51"]["5"] = "GLOBAL_VALID"
        self.assertTrue(validate(p))

    def test_start_is_delayed_retained_state_not_live_safe(self):
        _, pins = main()
        for ref, net in [("U52", "N19_PERMIT_D"), ("U54", "N12_PERMIT_D")]:
            p = copy.deepcopy(pins)
            p[ref]["1"] = net
            self.assertTrue(validate(p))

    def test_delay_has_conditional_clamp_release_margin(self):
        t = timing()
        self.assertTrue(t["delay_has20pct_over_release_requirement"])
        self.assertLess(t["CT_discharge_to_100mV_conditional_s"], 0.001)
        self.assertFalse(t["timing_qualified"])
        self.assertIsNone(t["rails"]["N19"]["maximum_power_conduction_s"])

    def test_module_startup_power_corrected_without_zero_volt_min_claim(self):
        f = analyze()["module_feed"]
        self.assertLess(f["initial_20pct_power_w"], 1)
        self.assertGreater(1.2 * 26.4**2 / (784 * 0.97), 1)
        self.assertTrue(f["min_voltage_applies_only_settled_not_0V_startup"])
        self.assertFalse(f["module_22p8V_before_first_ARM_correlation_implemented"])

    def test_full_package_current_not_old_aggregate_iq(self):
        a = analyze()["AUX"]
        self.assertLessEqual(a["normal20pct_a"], a["normal_receiving_allocation_a"])
        self.assertLessEqual(a["fault20pct_a"], a["fault_receiving_allocation_a"])
        self.assertGreater(a["normal20pct_a"], 0.005)
        self.assertFalse(a["full_source_pool_partition_accepted"])

    def test_actual_CWD_parts_and_six_DCU_lands(self):
        cs = {c["ref"]: c for c in json.loads((ROOT / "components.json").read_text())}
        self.assertIn("C1206C563J5GACTU", cs["C1"]["part"])
        self.assertIn("C1206C333J5GACTU", cs["C2"]["part"])
        self.assertEqual(sum(c["footprint"] == "NF05S_Manufacturer:TI_DCU0008A" for c in cs.values()), 6)

    def test_no_accidental_physical_or_partial_power_pass(self):
        a = analyze()
        self.assertFalse(a["physical_qualified"])
        self.assertFalse(a["startup_qualified"])
        self.assertFalse(a["integration"]["intermediate_AUX_corruption_hardoff_implemented"])
        self.assertFalse(a["release_approved"])


if __name__ == "__main__":
    unittest.main()
