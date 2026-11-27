import json,unittest
from .verify import H,verify,selection_valid
class PrecisionTests(unittest.TestCase):
 def test_native_checkpoint(self):self.assertEqual(verify()['unchanged_netted_pins'],3476)
 def test_wrong_tolerance_code_rejected(self):
  s={x['ref']:x for x in json.loads((H/'selection.json').read_text())['parts']};s['E_R83']['MPN']='PLT0805Z1072AST1'
  with self.assertRaises(AssertionError):selection_valid(s)
 def test_wrong_resistance_code_rejected(self):
  s={x['ref']:x for x in json.loads((H/'selection.json').read_text())['parts']};s['E_R84']['MPN']='PLT0805Z5762LST1'
  with self.assertRaises(AssertionError):selection_valid(s)
if __name__=='__main__':unittest.main()
