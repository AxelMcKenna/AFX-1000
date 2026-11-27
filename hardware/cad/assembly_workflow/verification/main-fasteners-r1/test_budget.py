import importlib,unittest
b=importlib.import_module('hardware.cad.assembly_workflow.verification.main-fasteners-r1.budget')
class BudgetTests(unittest.TestCase):
    def test_existing_power_length_does_not_satisfy_full_thread_allowance(self):
        with self.assertRaises(AssertionError):b.calc('power',length=(9.71,10.29))
    def test_short_signal_screw_is_rejected(self):
        with self.assertRaises(AssertionError):b.calc('signal',length=(7.71,8.29))
    def test_compressed_feet_fail_tip_clearance(self):
        with self.assertRaises(AssertionError):b.calc('power',feet=3.)
    def test_thicker_washer_changes_thread_engagement(self):
        with self.assertRaises(AssertionError):b.calc('signal',washer=(.75,.85))
    def test_sensor_mount_cannot_be_replaced(self):
        with self.assertRaises(AssertionError):b.calc('signal',mount='D_H2')
    def test_sourced_conditional_stack_meets_declared_limits(self):
        self.assertGreaterEqual(b.calc('signal')['full_thread_beyond_nut_min_mm'],.5)
        self.assertAlmostEqual(b.calc('power')['table_gap_min_mm'],3.2)
if __name__=='__main__':unittest.main()
