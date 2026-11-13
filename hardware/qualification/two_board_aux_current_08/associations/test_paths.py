import copy,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,Atom
from .paths import bind,expected_paths
from .build import stripped
H=Path(__file__).resolve().parents[1]
class AssociationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.board=read_sexpr((H/'main_ldo/native-03/power_protection.kicad_pcb').read_text());cls.paths=expected_paths(H/'precision/authored/power_protection.kicad_sch',H/'precision/native-01/candidate-netlist.xml')
 def test_only_missing_paths_change(self):
  b=copy.deepcopy(self.board);r=bind(b,self.paths);self.assertEqual(len(r['changes']),18);self.assertEqual(stripped(b),stripped(self.board))
 def test_wrong_existing_path_rejected(self):
  b=copy.deepcopy(self.board)
  f=next(f for f in children(b,'footprint') if children(f,'path'));children(f,'path')[0][1]='/wrong'
  with self.assertRaises(AssertionError):bind(b,self.paths)
 def test_duplicate_ref_rejected(self):
  b=copy.deepcopy(self.board);b.append(copy.deepcopy(children(b,'footprint')[0]))
  with self.assertRaises(AssertionError):bind(b,self.paths)
 def test_unassociated_electrical_rejected(self):
  b=copy.deepcopy(self.board);f=next(f for f in children(b,'footprint') if children(f,'path'));f[:]=[n for n in f if not isinstance(n,list) or n[0]!='path']
  with self.assertRaises(AssertionError):bind(b,self.paths)
 def test_unknown_electrical_rejected(self):
  b=copy.deepcopy(self.board);f=next(f for f in children(b,'footprint') if children(f,'path'));next(p for p in children(f,'property') if p[1]=='Reference')[2]='UNKNOWN'
  with self.assertRaises(AssertionError):bind(b,self.paths)
