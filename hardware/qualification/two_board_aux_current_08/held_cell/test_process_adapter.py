import json,sys,tempfile,unittest
from pathlib import Path
from .process_adapter import run_recorded
class AdapterTests(unittest.TestCase):
 def run_case(self,code,timeout=2):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);out=Path(t.name)/'run';r=run_recorded([sys.executable,'-c',code],out,timeout);self.assertEqual(json.loads((out/'process.json').read_text()),r);return r,out
 def test_success_records_output(self):
  r,p=self.run_case("print('complete')");self.assertEqual(r['status'],'passed');self.assertEqual((p/'stdout.log').read_text().strip(),'complete')
 def test_nonzero_is_not_success(self):
  r,_=self.run_case('raise SystemExit(7)');self.assertEqual(r['status'],'failed');self.assertEqual(r['returncode'],7)
 def test_signal_is_recorded(self):
  r,_=self.run_case('import os,signal;os.kill(os.getpid(),signal.SIGTERM)');self.assertEqual(r['status'],'failed');self.assertEqual(r['signal'],15)
 def test_timeout_is_not_success(self):
  r,_=self.run_case('import time;time.sleep(5)',timeout=.05);self.assertEqual(r['status'],'timeout')
 def test_cannot_overwrite_previous_evidence(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name)/'run';run_recorded([sys.executable,'-c','pass'],p)
  with self.assertRaises(FileExistsError):run_recorded([sys.executable,'-c','pass'],p)
if __name__=='__main__':unittest.main()
