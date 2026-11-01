"""Earlier rejected shunts, extra capacitance and live-load pass energy."""

import unittest

from hardware.qualification.boards.bipolar_slew import screen


class BipolarSlewRequirements(unittest.TestCase):
    def test_rejected_large_shunt_cannot_return_as_a_slew_candidate(self):
        with self.assertRaisesRegex(AssertionError, "100 milliohm"):
            screen(12, 264e-6, 0.151, [8e-6, 24e-6], [0.3e-6, 0.4e-6], 0.21, [0.28, 0.29])
        with self.assertRaisesRegex(AssertionError, "100 milliohm"):
            screen(12, 264e-6, 0.151, [8e-6, 24e-6], [0.3e-6, 0.4e-6], 0.21, [0.099, 0.101])

    def test_downstream_capacitance_cannot_inherit_local_only_margin(self):
        local = screen(12, 264e-6, 0.151, [8e-6, 24e-6], [0.3e-6, 0.4e-6], 0.21, [0.089, 0.093])
        full = screen(12, 1e-3, 0.151, [8e-6, 24e-6], [0.3e-6, 0.4e-6], 0.21, [0.089, 0.093])
        self.assertGreater(local["local_only_current_margin_a"], 0)
        self.assertLess(full["local_only_current_margin_a"], 0)
        self.assertIsNone(local["overall_startup_time_bound_s"])
        self.assertFalse(local["startup_qualified"])

    def test_integrated_pass_power_includes_live_load_during_ramp(self):
        result = screen(10, 0.1, 1, [1e-6, 1e-6], [1e-6, 1e-6], 2, [0.09, 0.09])
        # Independent midpoint integration: Vout=t for10s, capacitor current
        # C*dVout/dt=.1A and constant live load1A throughout the ramp.
        steps = 1000
        dt = 10 / steps
        integrated = sum((10 - (i + 0.5) * dt) * 1.1 * dt for i in range(steps))
        declared = (
            result["capacitor_charge_energy_j"]
            + result["live_constant_load_pass_energy_at_slowest_ideal_ramp_j"]
        )
        self.assertAlmostEqual(declared, integrated)
        self.assertGreater(declared, 10 * result["capacitor_charge_energy_j"])


if __name__ == "__main__":
    unittest.main()
