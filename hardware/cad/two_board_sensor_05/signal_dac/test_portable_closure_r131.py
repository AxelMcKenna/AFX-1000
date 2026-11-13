"""Unrelated shared-folder files cannot affect closure; contract tampering must fail."""
import contextlib,hashlib,io,json,tempfile,unittest
from pathlib import Path
from hardware.cad.two_board_sensor_05.signal_dac import verify_portable_r131 as gate

class ClosureRegression(unittest.TestCase):
 def test_unrelated_shared_files_and_contract_mutation(self):
  folder=gate.ROOT/'hardware/cad/assembly_workflow/verification/main-fasteners-r1'
  # Unique test-owned paths; never alter another task's files.
  with tempfile.TemporaryDirectory(prefix='unrelated-regression-',dir=folder)as name:
   extra=Path(name);(extra/'__pycache__').mkdir();(extra/'new-note.txt').write_text('unrelated shared-folder addition\n');(extra/'__pycache__/cached.pyc').write_bytes(b'not a dependency')
   with contextlib.redirect_stdout(io.StringIO()):gate.execute(gate.HERE/'final_review_r131.py')
  # In-memory mutation prevents writes to the frozen contract and tests the
  # exact local-byte integrity boundary used in both complete and reference gates.
  target=folder/'contact-keepouts.json';original_read=gate.LocalPath.read_bytes
  def tampered(path):
   data=original_read(path)
   return data+b' 'if path==target else data
  gate.LocalPath.read_bytes=tampered
  try:
   with self.assertRaisesRegex(AssertionError,'stale source'):
    with contextlib.redirect_stdout(io.StringIO()):gate.execute(gate.HERE/'final_review_r131.py')
  finally:gate.LocalPath.read_bytes=original_read

if __name__=='__main__':unittest.main()
