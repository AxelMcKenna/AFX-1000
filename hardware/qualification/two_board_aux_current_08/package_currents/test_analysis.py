import copy
import itertools
import json
import unittest
from .analyze import calculate, HERE

class CensusTests(unittest.TestCase):
    def setUp(self):
        self.facts=json.loads((HERE/'facts.json').read_text())
    def test_every_native_package_and_translator_port(self):
        r=calculate(self.facts)
        self.assertEqual((r['packages'],r['families']),(81,29))
        self.assertEqual(r['translator_aux_ports'],{'N_U16':'1','N_U27':'8'})
        self.assertEqual(r['regulator']['affected_packages'],['E_U10','E_U18','E_U9','N_U14','N_U15'])
        self.assertAlmostEqual(r['other_77_package_table_sum_A'],.000727)
        self.assertIsNone(r['full_current_bound_A'])
    def test_missing_package_rejected(self):
        self.facts['families'][0]['references'].pop()
        with self.assertRaises(AssertionError):calculate(self.facts)
    def test_duplicate_package_rejected(self):
        self.facts['families'][0]['references'].append(self.facts['families'][0]['references'][0])
        with self.assertRaises(AssertionError):calculate(self.facts)
    def test_channel_underestimate_rejected(self):
        next(f for f in self.facts['families'] if f['part']=='OPA2333AID')['units_per_package']=1
        with self.assertRaises(AssertionError):calculate(self.facts)
    def test_unproven_application_bound_rejected(self):
        self.facts['families'][0]['application_current_bound']=True
        with self.assertRaises(AssertionError):calculate(self.facts)
    def test_regulator_independent_all_corners(self):
        values=[]
        for st,sx,sb,sv,si in itertools.product([-1,1],repeat=5):
            a=11700*(1+st*.0035)+49.9*(1+sx*.0006)
            b=10000*(1+sb*.002)
            values.append(1.193*(1+sv*.02)*(1+a/b)+si*1e-7*a)
        lo,hi=calculate()['regulator']['conditional_output_V']
        # Conservative IFB uses maximumtop resistance even at lowV divider corner.
        self.assertLessEqual(lo,min(values));self.assertAlmostEqual(hi,max(values))
        self.assertGreater(lo,2.4);self.assertLess(lo-2.4,.135)
    def test_supervisor_margin_is_not_a_release_claim(self):
        r=calculate()['aux_supervisor']
        self.assertAlmostEqual(r['nominal_falling_threshold_V'],2.431008)
        self.assertGreater(r['falling_margin_to_2V4_V'],.003)
        self.assertLess(r['falling_margin_to_2V4_V'],.0031)
        self.assertFalse(r['proof_of_safe_enable_or_shutdown'])


class WindowTests(unittest.TestCase):
    def test_candidate_meets_explicit_allocations(self):
        from .threshold_window import window
        w=window()
        self.assertTrue(w['proposal']['meets_allocations'])
        self.assertFalse(w['applied_to_board']);self.assertFalse(w['qualified'])
        self.assertLess(11139.2,w['allowable_top_nominal_ohm'][0])
    def test_excessive_distribution_budget_has_no_solution(self):
        from .threshold_window import window
        w=window(shutdown_drop_slew_V=.1)
        self.assertFalse(w['nonempty_window']);self.assertFalse(w['proposal']['meets_allocations'])

if __name__=='__main__':unittest.main()
