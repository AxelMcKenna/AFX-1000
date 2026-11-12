import unittest,tempfile,shutil,json
from pathlib import Path
from .verify_individual import HERE,verify
class PoseTests(unittest.TestCase):
 def test_native_matches_mirrored_pad_coordinates(self):self.assertEqual(verify()['native_pose_count'],18)
 def test_mirrored_pad_error_is_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   h=Path(t);(h/'native').mkdir();shutil.copy(HERE/'individual-placement.json',h)
   n=json.loads((HERE/'native/native-poses.json').read_text());n['poses'][0]['pads']['1'][0]+=.1;(h/'native/native-poses.json').write_text(json.dumps(n))
   with self.assertRaisesRegex(AssertionError,'coordinate mismatch'):verify(h)
 def test_stale_native_pose_is_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   h=Path(t);(h/'native').mkdir();shutil.copy(HERE/'individual-placement.json',h);shutil.copy(HERE/'native/native-poses.json',h/'native')
   p=h/'individual-placement.json';p.write_text(p.read_text()+'\n')
   with self.assertRaisesRegex(AssertionError,'Stale native'):verify(h)
if __name__=='__main__':unittest.main()
