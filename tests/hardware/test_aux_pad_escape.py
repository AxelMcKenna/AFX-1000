import unittest
from shapely.geometry import box
from hardware.fabrication.plan_two_board_aux_local_distribution_v6 import newly_added_copper_referenced

class PadEscapeTests(unittest.TestCase):
    def test_empty_added_copper_is_not_a_reference_failure(self):
        self.assertTrue(newly_added_copper_referenced([(-.5,0),(-.49999,0)],box(0,-1,3,1),box(-1,-.5,1,.5)))
    def test_inherited_pad_overlap_is_not_new_copper(self):
        self.assertTrue(newly_added_copper_referenced([(-.5,0),(2,0)], box(0,-1,3,1),box(-1,-.5,1,.5)))
    def test_new_copper_outside_pad_cannot_use_exemption(self):
        self.assertFalse(newly_added_copper_referenced([(-1.2,0),(2,0)],box(0,-1,3,1),box(-1,-.5,1,.5)))
    def test_gap_after_escape_is_rejected(self):
        field=box(0,-1,1.2,1).union(box(1.3,-1,3,1))
        self.assertFalse(newly_added_copper_referenced([(-.5,0),(2,0)],field,box(-1,-.5,1,.5)))

if __name__=='__main__':unittest.main()
