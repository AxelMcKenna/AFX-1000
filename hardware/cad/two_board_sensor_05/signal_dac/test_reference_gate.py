"""Fail-closed regressions for independently required transition identity proofs."""
import copy,json,runpy,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parent
class TransitionIdentityGate(unittest.TestCase):
 def reject(self,mutation):
  target=R/'transitions-r26.json';data=json.loads(target.read_text());mutation(data)
  original=Path.read_text
  def read(path,*args,**kwargs):
   return json.dumps(data)if path==target else original(path,*args,**kwargs)
  with patch.object(Path,'read_text',read),patch.object(Path,'write_text',side_effect=RuntimeError('audit unexpectedly reached output')):
   with self.assertRaises(AssertionError):runpy.run_path(str(R/'review_r26.py'))
 def test_missing_signal_via_proof_is_rejected(self):
  def mutate(d):
   r=json.loads((R/'candidate-r26/routing.json').read_text());uid=r['vias'][0]['uuid'];d['transitions']=[v for v in d['transitions']if v['signal_uuid']!=uid]
  self.reject(mutate)
 def test_wrong_signal_net_is_rejected(self):
  def mutate(d):
   r=json.loads((R/'candidate-r26/routing.json').read_text());uid=r['vias'][0]['uuid'];next(v for v in d['transitions']if v['signal_uuid']==uid)['signal_net']='/wrong-net'
  self.reject(mutate)
if __name__=='__main__':unittest.main()
