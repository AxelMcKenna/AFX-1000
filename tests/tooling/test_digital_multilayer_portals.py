"""A surface contact must not acquire layer access without a real via."""
import copy,unittest
from hardware.fabrication.digital_multilayer_escape_routes_v3 import multilayer_portals
from hardware.fabrication import route_nf_surface as surface
class MultilayerPortalTests(unittest.TestCase):
 def setUp(self):
  self.previous=surface.SIGNAL_LAYERS
  surface.SIGNAL_LAYERS=('F.Cu','In3.Cu','In5.Cu','B.Cu')
 def tearDown(self):surface.SIGNAL_LAYERS=self.previous
 def test_existing_surface_contact_stays_on_its_face(self):
  rows=multilayer_portals({('B.Cu',(1.,2.))},[],'group')
  self.assertEqual(rows[0]['layers'],['B.Cu']);self.assertEqual(rows[0]['vias'],[])
 def test_only_drilled_escape_gains_layers(self):
  escaped=[dict(point=(3.,4.),layers=['In5.Cu'],runs=[],vias=[(3.,4.)],cost=1.,group='g'),dict(point=(5.,6.),layers=['In5.Cu'],runs=[],vias=[],cost=0.,group='g')]
  before=copy.deepcopy(escaped);rows=multilayer_portals(set(),escaped,'g')
  self.assertEqual(rows[0]['layers'],list(surface.SIGNAL_LAYERS));self.assertEqual(rows[1]['layers'],['In5.Cu']);self.assertEqual(escaped,before)
if __name__=='__main__':unittest.main()
