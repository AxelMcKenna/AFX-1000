import unittest
from hardware.fabrication.verify_native_zone_unfracture import verify


class NativeZoneUnfractureTests(unittest.TestCase):
    def test_nanometre_shift_preserves_copper(self):
        old = [dict(outer=[[0,0],[2,0],[2,2],[0,2]], holes=[])]
        new = [dict(outer=[[0,0],[2.0000005,0],[2.0000005,2],[0,2]], holes=[])]
        self.assertLess(verify(old,new)['boundary_displacement_mm'], 1e-6)

    def test_removed_clearance_hole_is_rejected(self):
        outer = [[0,0],[2,0],[2,2],[0,2]]
        hole = [[.8,.8],[1.2,.8],[1.2,1.2],[.8,1.2]]
        with self.assertRaises(AssertionError):
            verify([dict(outer=outer,holes=[hole])], [dict(outer=outer,holes=[])])

    def test_equal_area_shift_is_rejected(self):
        old = [dict(outer=[[0,0],[2,0],[2,2],[0,2]],holes=[])]
        new = [dict(outer=[[.1,0],[2.1,0],[2.1,2],[.1,2]],holes=[])]
        with self.assertRaises(AssertionError):
            verify(old,new)


if __name__ == '__main__':
    unittest.main()
