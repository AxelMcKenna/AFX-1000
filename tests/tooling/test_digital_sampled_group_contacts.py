import unittest
from hardware.fabrication.digital_sampled_group_contacts import contacts

class SampledGroupTests(unittest.TestCase):
    def fixtures(self):
        source=dict(net='n',kind='PAD',group='source',position_mm=[0,0],layers={'B.Cu':[1]})
        track=dict(net='n',kind='PCB_TRACK',group='target',position_mm=[1,0],end_mm=[2,0],layers={'In3.Cu':[1]})
        return source,track
    def test_includes_midtrack_contacts_on_actual_layer(self):
        source,track=self.fixtures();r=contacts(dict(objects=[source,track]),source,('F.Cu','In3.Cu','B.Cu'))
        self.assertIn(('In3.Cu',(1.4,0.)),r)
        self.assertEqual({f for f,p in r},{'In3.Cu'})
        self.assertIn(('In3.Cu',(1.,0.)),r);self.assertIn(('In3.Cu',(2.,0.)),r)
    def test_excludes_own_stub_and_foreign_net(self):
        source,track=self.fixtures();own=dict(track,group='source',position_mm=[0,0],end_mm=[.5,0]);foreign=dict(track,net='other',position_mm=[3,0],end_mm=[4,0])
        r=contacts(dict(objects=[source,track,own,foreign]),source,('In3.Cu','B.Cu'))
        self.assertTrue(all(1<=p[0]<=2 for f,p in r))
    def test_rejects_coarser_or_invalid_sampling(self):
        source,track=self.fixtures()
        for step in (0,-1,.21):
            with self.assertRaises(AssertionError):contacts(dict(objects=[source,track]),source,('In3.Cu',),step)

if __name__=='__main__':unittest.main()
