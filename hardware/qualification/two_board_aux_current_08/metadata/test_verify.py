import copy,json,unittest
from hardware.electronics.common.sexpr import read_sexpr,children,first
from .verify import verify,exact_delta
from .build import H,ROOT,props
class MetadataTests(unittest.TestCase):
 def setUp(self):
  self.old=read_sexpr((ROOT/'held_cell/native-local-02/power_protection.kicad_pcb').read_text());self.new=read_sexpr((H/'native-01/power_protection.kicad_pcb').read_text());self.changes=json.loads((H/'changes.json').read_text())['changes']
 def test_checkpoint(self):self.assertEqual(verify()['components_value_parity'],1104)
 def test_moved_pad_rejected(self):
  first(children(children(self.new,'footprint')[0],'pad')[0],'at')[1]='123'
  with self.assertRaises(AssertionError):exact_delta(self.old,self.new,self.changes)
 def test_extra_metadata_rejected(self):
  props(children(self.new,'footprint')[0])['Value'][2]='wrong'
  with self.assertRaises(AssertionError):exact_delta(self.old,self.new,self.changes)
 def test_missing_change_rejected(self):
  with self.assertRaises(AssertionError):exact_delta(self.old,self.new,self.changes[:-1])
if __name__=='__main__':unittest.main()
