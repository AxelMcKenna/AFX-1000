"""Boundary cases for packing conventional through-via signal escapes."""
import unittest
from hardware.fabrication.digital_serial1_joint_escape_survey import compatible

def option(face,points,vias=()):
    return dict(runs=[(face,points)],vias=list(vias))

class EscapeCompatibilityTests(unittest.TestCase):
    def test_crossed_same_face_tracks_are_rejected(self):
        self.assertFalse(compatible(option('F.Cu',[(0,0),(2,2)]),option('F.Cu',[(0,2),(2,0)])))
    def test_crossed_separate_faces_without_vias_are_allowed(self):
        self.assertTrue(compatible(option('F.Cu',[(0,0),(2,2)]),option('B.Cu',[(0,2),(2,0)])))
    def test_through_via_blocks_track_on_opposite_face(self):
        self.assertFalse(compatible(option('F.Cu',[(0,0),(1,0)],[(1,0)]),option('B.Cu',[(1,-1),(1,1)])))
    def test_close_barrels_on_separate_faces_are_rejected(self):
        self.assertFalse(compatible(option('F.Cu',[(-1,0),(0,0)],[(0,0)]),option('B.Cu',[(.8,0),(2,0)],[(.8,0)])))
    def test_parallel_trace_guard_includes_both_widths(self):
        self.assertFalse(compatible(option('F.Cu',[(0,0),(2,0)]),option('F.Cu',[(0,.4),(2,.4)])))
    def test_separated_complete_escapes_are_allowed(self):
        self.assertTrue(compatible(option('F.Cu',[(0,0),(1,0)],[(1,0)]),option('F.Cu',[(0,1),(1,1)],[(1,1)])))
    def test_order_does_not_change_rejection(self):
        a=option('B.Cu',[(0,0),(2,0)]);b=option('F.Cu',[(1,1),(1,.5)],[(1,.5)])
        self.assertFalse(compatible(a,b));self.assertEqual(compatible(a,b),compatible(b,a))

if __name__=='__main__':unittest.main()
