"""A passing test suite here means rejected candidates remain rejected."""
import json,unittest
from shapely.geometry import Polygon
from shapely.ops import unary_union
from ..routed.plan import shape
from .verify import verify as verify_route,transition_check,H
from .verify_fill import verify as verify_fill
class DiagnosticsTests(unittest.TestCase):
 def test_unfilled_route_is_rejected(self):
  with self.assertRaises(AssertionError):verify_route()
 def test_nonlocal_cutback_is_rejected(self):
  with self.assertRaisesRegex(AssertionError,'exceeds local removal-only'):verify_fill()
 def test_antipad_exception_cannot_expand(self):
  p=json.loads((H/'plan.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());ref=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in p['reference_zone_uuids']]);p['transition']['allowed_antipad_polygon_mm']=list(Polygon(p['transition']['allowed_antipad_polygon_mm']).buffer(.1).exterior.coords)
  with self.assertRaises(AssertionError):transition_check(p,c,ref)
 def test_return_must_be_paired_to_actual_added_via(self):
  p=json.loads((H/'plan.json').read_text());c=json.loads((H/'capture-01/capture.json').read_text());ref=unary_union([shape(z['polygons']) for z in c['zones'] if z['uuid'] in p['reference_zone_uuids']]);p['transition']['return_position_mm']=[200,120]
  with self.assertRaises(AssertionError):transition_check(p,c,ref)
if __name__=='__main__':unittest.main()
