"""Reject scope/geometry/ground identity mutations at the exact replacement gate."""
import copy,json,traceback,unittest
from pathlib import Path
from hardware.cad.two_board_sensor_05.signal_dac import verify_portable_r148 as gate
class ReplacementRegression(unittest.TestCase):
 def test_authorized_scope_and_replacement_identity(self):
  original=json.loads((gate.HERE/'candidate-r148/routing.json').read_text())
  for case,expected in [('retired',"==expected"),('width',"o['width_mm']==row['width_mm']"),('endpoint',"o['position_mm']==p"),('ground',"o['net']==v['net']")]:
   value=copy.deepcopy(original)
   if case=='retired':value['declared_removed'].pop()
   elif case=='width':value['routes'][2]['width_mm']+=.01
   elif case=='endpoint':value['routes'][2]['path_mm'][0][0]+=.01
   else:value['new_ground_vias'][0]['net']='/wrong-ground'
   gate.ROUTING_OVERRIDE=value
   try:
    try:gate.execute(gate.HERE/'replacement_audit_r148.py')
    except AssertionError as error:final=traceback.extract_tb(error.__traceback__)[-1]
    else:self.fail('replacement mutation accepted: '+case)
    self.assertEqual(Path(final.filename),gate.HERE/'replacement_audit_r148.py');line=(gate.HERE/'replacement_audit_r148.py').read_text().splitlines()[final.lineno-1];self.assertIn(expected,line)
   finally:gate.ROUTING_OVERRIDE=None
