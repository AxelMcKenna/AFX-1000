import unittest
from .verify import EXPECTED,check_pin_delta,verify
class SharedCutoverTests(unittest.TestCase):
 def test_native_checkpoint(self):verify()
 def test_reset_supply_confusion_rejected(self):
  old={k:'old' for k in EXPECTED};new=dict(EXPECTED);new['E_U31','6']='PWR_AUX_HELD3V3'
  with self.assertRaises(AssertionError):check_pin_delta(old,new,EXPECTED)
 def test_unrelated_pin_change_rejected(self):
  old={k:'old' for k in EXPECTED};old['E_U1','2']='TT';new=dict(EXPECTED);new['E_U1','2']='PWR_AGND'
  with self.assertRaises(AssertionError):check_pin_delta(old,new,EXPECTED)
 def test_missing_schematic_pin_rejected(self):
  old={k:'old' for k in EXPECTED};required=dict(EXPECTED);required['missing','1']='some_net'
  with self.assertRaises(AssertionError):check_pin_delta(old,EXPECTED,required)
if __name__=='__main__':unittest.main()
