"""Portable source-bound NF and fan mounting checks in the normal CI suite."""

import unittest

from hardware.qualification.boards.fan_health.composite_mount import test_mount
from hardware.qualification.boards.nf_passive_selection_portable import test_portable
from hardware.qualification.boards.startup_negative_circuit.uv_recovery import test_recovery


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        loader.loadTestsFromModule(test_mount),
        loader.loadTestsFromModule(test_portable),
        loader.loadTestsFromModule(test_recovery),
    ])
