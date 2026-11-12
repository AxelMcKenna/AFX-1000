import json,shutil,tempfile,unittest
from pathlib import Path
from .verify import HERE,verify
class EvidenceTests(unittest.TestCase):
    def test_native_geometry_reports_real_rule_conflict(self):
        r=verify();self.assertFalse(r['fabrication_qualified']);self.assertEqual(len(r['unresolved_rule_conflicts']),1)
    def test_changed_footprint_rejects_stale_native_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d)/'placement';shutil.copytree(HERE,h)
            p=next((h/'AUX_READY.pretty').glob('*.kicad_mod'));p.write_text(p.read_text()+'\n')
            with self.assertRaisesRegex(AssertionError,'Stale native'):verify(h)
    def test_unexpected_native_pad_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d)/'placement';shutil.copytree(HERE,h)
            p=h/'native/native-footprints.json';n=json.loads(p.read_text());n['footprints'][0]['pads'].append(n['footprints'][0]['pads'][0]);p.write_text(json.dumps(n))
            with self.assertRaisesRegex(AssertionError,'Unexpected pad'):verify(h)
if __name__=='__main__':unittest.main()
