"""Native topology, analytical failure controls and settled-state safety checks.

No propagation/metastability/photorelay/physical assertion is made here.
"""
import copy
import json
import unittest
from pathlib import Path
from hardware.electronics.common.netlists import netlist
from hardware.qualification.boards.startup_negative_protection.capture import sha
from .analyze import ROOT,PARENT,feed,recenter,complete_power,startup
from hardware.qualification.boards.startup_negative_protection.analyze import native


def graph():
    parts,pins=netlist(ROOT/'generated/netlist.xml')
    functions=[]
    for ref,c in parts.items():
        part=c.findtext('value');p=pins[ref]
        if part.startswith(('SN74HCS08','SN74HCS32')):
            op='AND' if 'HCS08' in part else 'OR'
            for a,b,y in [(1,2,3),(4,5,6),(9,10,8),(12,13,11)]:
                if not p[str(y)].startswith('unconnected-('):functions.append((op,p[str(a)],p[str(b)],p[str(y)]))
        elif part.startswith('SN74HCS14'):
            for a,y in [(1,2),(3,4),(5,6),(9,8),(11,10),(13,12)]:
                if not p[str(y)].startswith('unconnected-('):functions.append(('INV',p[str(a)],None,p[str(y)]))
        elif part.startswith('SN74AUP2G14'):
            for a,y in [(1,6),(3,4)]:functions.append(('INV',p[str(a)],None,p[str(y)]))
    return functions


def evaluate(changes=None, functions=None):
    s={'AGND':0,'AUX2V6':1,'AUX_VALID':1,'GLOBAL_MASTER':1,'E28_NOT_FAULT':1,'E28_NATIVE_FAULT_REQUEST':0}
    for n in ['N19','N12']:
        s.update({n+'_'+k:v for k,v in {'ARM':1,'START':0,'OV_OK':1,'BIAS_VALID':1,'SOURCE_UV_GOOD':1,'OUTPUT_UV_GOOD':1,'OUTPUT_OV_GOOD':1,'WDO':1,'WD_ARMED':1,'PERMIT':1,'NOT_PERMIT':0,'COMPLETE':1,'NOT_COMPLETE':0}.items()})
    s.update(changes or {})
    funcs=functions or graph()
    for _ in range(40):
        before=dict(s)
        for op,a,b,y in funcs:
            if a in s and (op=='INV' or b in s):s[y]=int(not s[a]) if op=='INV' else int(bool(s[a] and s[b])) if op=='AND' else int(bool(s[a] or s[b]))
        if s==before:break
    return s


class Compact(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/'parameters.json').read_text())
    def test_feed_normal_and_initial_corners(self):
        a=feed(self.p)
        self.assertTrue(a['normal_load_has20pct_headroom']);self.assertTrue(a['initial_feed_has20pct_below50ma'])
        self.assertTrue(a['normal_shunt_feed_below25ma']);self.assertGreater(a['rejected15v_213ohm_initial_current_a'],0.05)
    def test_15v_feed_mutation_is_rejected(self):
        p=copy.deepcopy(self.p);p['complete_delivered_module_voltage_requirement_v']=[14.2,15.8];p['feed_series_resistors_ohm']=[100,113]
        self.assertFalse(feed(p)['initial_feed_has20pct_below50ma'])
    def test_too_large_feed_resistor_rejected(self):
        p=copy.deepcopy(self.p);p['feed_series_resistors_ohm']=[1000,1000]
        self.assertFalse(feed(p)['normal_load_has20pct_headroom'])
    def test_both_voltage_corners_not_just_loaded_minimum(self):
        parts,_,_=native(PARENT/'sources/p03-fresh-netlist.xml');rows=recenter(self.p,parts)
        self.assertFalse(rows[0]['interval_within_retained_target']);self.assertTrue(rows[2]['interval_within_retained_target'])
        p=copy.deepcopy(self.p);p['new_n12_r40_top_total_comparison_ohm']=183000
        r=recenter(p,parts)[2];self.assertGreater(r['guarded_low_margin_v'],0);self.assertLess(r['guarded_high_margin_v'],0)
    def test_real_ramp_filter_and_gate_compensation_drawing(self):
        parts,pins=netlist(ROOT/'generated/netlist.xml')
        for name,count in [('N19',12),('N12',9)]:
            ctrl=[r for r,c in parts.items() if c.findtext('value')=='LTC4261IGN#PBF' and pins[r]['13']==name+'_P03_SRC']
            self.assertEqual(len(ctrl),1);p=pins[ctrl[0]]
            self.assertEqual(p['15'],name+'_PASS_GATE');self.assertEqual(p['22'],name+'_INTVCC')
            ramps=[r for r,c in parts.items() if c.findtext('value').startswith('100nF 50V C0G C1210') and set(pins[r].values())=={name+'_CR_TOP',name+'_E28_SRC'}]
            self.assertEqual(len(ramps),count)
            cf=[r for r,c in parts.items() if 'EFFECTIVE CF' in c.findtext('value') and set(pins[r].values())=={name+'_RAMP',name+'_P03_SRC'}]
            self.assertEqual(len(cf),2)
            rg=[r for r,c in parts.items() if c.findtext('value').startswith('10ohm') and set(pins[r].values())=={name+'_PASS_GATE',name+'_CG_SERIES'}]
            self.assertEqual(len(rg),1)
    def test_correct_form_b_contacts_referenced_to_actual_sources(self):
        parts,pins=netlist(ROOT/'generated/netlist.xml')
        relays=[r for r,c in parts.items() if c.findtext('value').startswith('TLP4590')]
        self.assertEqual(len(relays),4)
        for r in relays:
            p=pins[r];self.assertTrue(p['5'].startswith('unconnected-('));self.assertTrue(p['6'].endswith(('PASS_SOURCE','BANK_COMMON')))
    def test_complete_does_not_self_clear_when_permit_falls(self):
        a=evaluate({'N19_PERMIT':0,'N19_NOT_PERMIT':1,'N19_OUTPUT_UV_GOOD':0})
        self.assertEqual(a['N19_COMPLETE_CLR_N'],1);self.assertEqual(a['N19_FAULT_REQUEST'],1)
        for name in ['N19','N12']:
            self.assertEqual(a[name+'_PERMIT_CLR_N'],0);self.assertEqual(a[name+'_CLAMPS_RELEASE'],0)
    def test_native_global_masks_and_source_collapse(self):
        for bad in [{'AUX_VALID':0},{'GLOBAL_MASTER':0},{'E28_NOT_FAULT':0},{'N19_SOURCE_UV_GOOD':0},{'N19_BIAS_VALID':0},{'N12_OUTPUT_OV_GOOD':0}]:
            a=evaluate(bad)
            for name in ['N19','N12']:
                self.assertEqual(a[name+'_CLAMPS_RELEASE'],0,bad);self.assertEqual(a[name+'_PERMIT_CLR_N'],0,bad)
    def test_normal_ramp_uv_does_not_trip_before_completion(self):
        a=evaluate({'N19_COMPLETE':0,'N19_NOT_COMPLETE':1,'N19_OUTPUT_UV_GOOD':0})
        self.assertEqual(a['N19_FAULT_REQUEST'],0);self.assertEqual(a['N19_CLAMPS_RELEASE'],1)
    def test_reject_completion_clear_mutation(self):
        f=graph();mutated=[(op,'N19_PERMIT' if y=='N19_COMPLETE_CLR_N' else a,b,y) for op,a,b,y in f]
        self.assertEqual(evaluate({'N19_PERMIT':0},mutated)['N19_COMPLETE_CLR_N'],0)
        self.assertEqual(evaluate({'N19_PERMIT':0})['N19_COMPLETE_CLR_N'],1)
    def test_power_and_reserve_accounting(self):
        a=complete_power(self.p,feed(self.p));pt=a['normal_feed_point']
        self.assertAlmostEqual(pt['plug_power_w'],pt['feed_loss_w']+pt['board_received_power_w'],places=10)
        self.assertGreater(a['remaining_for_fan_health_after_nf20pct_and_fp01_a'],.006177)
        self.assertTrue(a['aux_provision_has20pct']);self.assertGreater(a['new_enclosing_whole_inside_heat_requirement_w'],35.4315)
        self.assertFalse(a['capacity_corner_is_same_as_normal_feed_point'])
    def test_gate_compensation_invalidates_old_charge_allowance(self):
        for row in startup(self.p).values():
            self.assertTrue(row['old500nc_whole_node_allowance_insufficient_even_before_mos'])
            self.assertTrue(row['cutoff20pct_headroom'])
            self.assertTrue(row['watchdog_min_has20pct_over_complete'])
            self.assertTrue(row['native_limit20pct_over_normal'])
            self.assertIsNone(row['actual_fault_energy_upper_j'])
    def test_both_floating_bias_rails_independently_supervised(self):
        parts,pins=netlist(ROOT/'generated/netlist.xml')
        supervisors=[r for r,c in parts.items() if c.findtext('value')=='TPS389001DSET']
        self.assertEqual(len(supervisors),4)
        for rail in ('N19','N12'):
            rows=[pins[r] for r in supervisors if pins[r]['2']==rail+'_P03_SRC']
            self.assertEqual(len(rows),2)
            self.assertEqual({p['1'] for p in rows},{rail+'_BIAS_SENSE',rail+'_VIN_VALID_SENSE'})
            self.assertEqual({p['6'] for p in rows},{rail+'_BIAS_RESET_N'})
    def test_power_off_clears_completion_without_permit_self_erase(self):
        a=evaluate({'GLOBAL_MASTER':0})
        self.assertEqual(a['N19_COMPLETE_CLR_N'],0)
        self.assertEqual(evaluate({'N19_PERMIT':0})['N19_COMPLETE_CLR_N'],1)
    def test_native_receipt_current(self):
        a=json.loads((ROOT/'generated/current-native.json').read_text())
        self.assertEqual(a['erc']['error'],0);self.assertFalse(a['pin_parity_differences'])
        for group in ['source_sha256','artifact_sha256']:
            for n,h in a[group].items():self.assertEqual(sha(ROOT/n),h,n)
        self.assertFalse(a['physical_qualified']);self.assertFalse(a['startup_qualified']);self.assertFalse(a['pcb_implemented'])

if __name__=='__main__':unittest.main()
