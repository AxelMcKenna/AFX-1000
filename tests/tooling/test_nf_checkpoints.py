"""Portable source-bound NF and fan mounting checks in the normal CI suite."""

import unittest

from hardware.qualification.boards.fan_health.composite_mount import test_mount
from hardware.qualification.boards.nf_passive_selection_checkout.verify import check
from hardware.qualification.boards.nf_passive_selection_portable import test_portable
from hardware.qualification.boards.startup_negative_circuit.uv_recovery import test_recovery


class CheckoutPortablePolicy(test_portable.PortablePolicy):
    def test_runtime_replay_obeys_bound(self):
        report = check()
        self.assertEqual(report["errors"],[])
        self.assertTrue(all(max(p["ulp_distances"]) <= 4 for p in report["accepted_computed_sum_differences"]))
        self.assertFalse(report["physical_qualified"])


def load_tests(loader, tests, pattern):
    legacy_models = unittest.TestSuite()
    test_portable.load_tests(loader,legacy_models,pattern)
    return unittest.TestSuite([
        loader.loadTestsFromModule(test_mount),
        loader.loadTestsFromTestCase(CheckoutPortablePolicy),
        legacy_models,
        loader.loadTestsFromModule(test_recovery),
    ])
