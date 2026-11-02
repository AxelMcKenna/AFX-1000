"""Annotation normalization must not conceal an electrical or placement change."""
import ast,copy,unittest
from pathlib import Path
from hardware.fabrication.source_audit_tools import normalize_annotation_half_turns
from hardware.electronics.common.sexpr import first,children,read_sexpr

class AnnotationBoundary(unittest.TestCase):
    def test_pure_normalizer_is_the_exact_frozen_native_function(self):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication'
        functions=[]
        for name in ('audit_digital_cell_native.py','source_audit_tools.py'):
            tree=ast.parse((root/name).read_text())
            fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='normalize_annotation_half_turns')
            functions.append(ast.dump(fn,include_attributes=False))
        self.assertEqual(*functions)
    def setUp(self):
        self.source=read_sexpr('(kicad_pcb (footprint "Lib:Part" (at 10 20 90) (layer "B.Cu") (property "Reference" "C1" (at 0 2 90) (layer "B.Fab")) (pad "1" smd rect (at -1 0 90) (size 1 2) (layers "B.Cu" "B.Mask" "B.Paste") (net "SUPPLY"))))')
    def test_annotation_half_turn_is_only_normalized_difference(self):
        changed=copy.deepcopy(self.source);f=children(changed,'footprint')[0];first(first(f,'property'),'at')[3]=270
        self.assertEqual(normalize_annotation_half_turns(self.source),normalize_annotation_half_turns(changed))
    def reject(self,edit):
        changed=copy.deepcopy(self.source);edit(children(changed,'footprint')[0])
        self.assertNotEqual(normalize_annotation_half_turns(self.source),normalize_annotation_half_turns(changed))
    def test_pad_rotation_not_hidden(self):self.reject(lambda f:first(first(f,'pad'),'at').__setitem__(3,270))
    def test_pad_size_not_hidden(self):self.reject(lambda f:first(first(f,'pad'),'size').__setitem__(1,1.1))
    def test_pin_net_not_hidden(self):self.reject(lambda f:first(first(f,'pad'),'net').__setitem__(1,'AGND'))
    def test_component_position_not_hidden(self):self.reject(lambda f:first(f,'at').__setitem__(1,10.1))
    def test_component_face_not_hidden(self):self.reject(lambda f:first(f,'layer').__setitem__(1,'F.Cu'))
    def test_annotation_position_not_hidden(self):self.reject(lambda f:first(first(f,'property'),'at').__setitem__(1,.2))

if __name__=='__main__':unittest.main()
