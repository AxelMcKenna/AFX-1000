"""Fail closed on changed ownership or enlarged transported sensitive-pad openings."""
import copy,json,unittest
from pathlib import Path
from shapely.geometry import mapping
from hardware.fabrication.route_nf_surface import shape
from hardware.cad.two_board_sensor_05.signal_dac.sensitive_placement import validated_exclusions
R=Path(__file__).resolve().parent
class SensitivePlacement(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=json.loads((R.parent/'signal_input/capture-r7/capture.json').read_text());cls.after=json.loads((R/'capture-r53/capture.json').read_text());cls.contracts=json.loads((R/'candidate-r53/routing.json').read_text())['supplemental_lowcap_exclusions']
 def test_exact_transported_source_rule(self):
  rows=validated_exclusions(self.before,self.after,self.contracts)
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['net'],'/A_DAC/RX_NEG_L')
 def test_wrong_net_is_rejected(self):
  contracts=copy.deepcopy(self.contracts);contracts[0]['net']='/A_DAC/IV_P_L'
  with self.assertRaises(AssertionError):validated_exclusions(self.before,self.after,contracts)
 def test_enlarged_native_opening_is_rejected(self):
  after={**self.after,'zones':copy.deepcopy(self.after['zones'])}
  z=next(z for z in after['zones']if z['uuid']==self.contracts[0]['zone_uuid']and z['layer']=='In1.Cu');g=shape(z['polygons']).buffer(.1);z['polygons']=[{'outer':list(g.exterior.coords),'holes':[list(h.coords)for h in g.interiors]}]
  with self.assertRaises(AssertionError):validated_exclusions(self.before,after,self.contracts)
if __name__=='__main__':unittest.main()
