import copy,unittest
from shapely.geometry import LineString
from .routing_zones import obstacles
class ZoneTests(unittest.TestCase):
 def setUp(self):self.z={'uuid':'z','net':'PWR_DC_IN','layer':'B.Cu','keepout':False,'polygons':[{'outer':[[0,0],[2,0],[2,2],[0,2]],'holes':[]}],'authored_outline':[{'outer':[[0,0],[2,0],[2,2],[0,2]],'holes':[]}]}
 def test_foreign_filled_zone_blocks_track(self):self.assertTrue(obstacles([self.z],'B.Cu','VIN',.3).intersects(LineString([[-1,1],[3,1]])))
 def test_only_declared_cutback_can_cross(self):self.assertTrue(obstacles([self.z],'B.Cu','VIN',.3,['z']).is_empty)
 def test_cutback_cannot_waive_keepout(self):
  self.z.update(keepout=True,prohibit_tracks=True)
  with self.assertRaises(AssertionError):obstacles([self.z],'B.Cu','VIN',.3,['z'])
if __name__=='__main__':unittest.main()
