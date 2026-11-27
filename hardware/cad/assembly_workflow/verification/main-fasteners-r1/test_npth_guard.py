import importlib,unittest
v=importlib.import_module('hardware.cad.assembly_workflow.verification.main-fasteners-r1.npth_guard').validate
class NPTHTests(unittest.TestCase):
    def pad(self,shape='circle',size='2.4',drill=None):return ['pad','','np_thru_hole',shape,['size',size,size],drill or ['drill','2.4']]
    def test_drill_only_circle_is_not_copper(self):self.assertTrue(v(self.pad()))
    def test_enlarged_npth_annulus_is_rejected(self):
        with self.assertRaises(AssertionError):v(self.pad(size='2.5'))
    def test_offset_hole_can_expose_copper(self):
        with self.assertRaises(AssertionError):v(self.pad(drill=['drill','2.4',['offset','.1','0']]))
    def test_nonround_pad_is_not_silently_skipped(self):
        with self.assertRaises(AssertionError):v(self.pad(shape='rect'))
    def test_unimplemented_slotted_drill_is_rejected(self):
        with self.assertRaises(AssertionError):v(self.pad(drill=['drill','oval','2.4','3.0']))
if __name__=='__main__':unittest.main()
