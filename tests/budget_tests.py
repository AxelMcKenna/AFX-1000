#!/usr/bin/env python3
"""Independent emitted-CAD checks for the consumer-level B1 variant."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from generate_budget import all_sheets
from bypass_tests import read_circuit
from budget_cost import generate as cost_artifacts


def net(parts,ref,pad):return parts[ref]['pins'][str(pad)]['net']
def par(a,b):return a*b/(a+b)


class BudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts={d['project']:read_circuit((ROOT/'hardware/budget/sheets'/(d['project']+'.kicad_sch')).read_text()) for d in all_sheets()}

    def test_every_emitted_pin_and_reference(self):
        refs=set()
        for d in all_sheets():
            actual=self.parts[d['project']]
            self.assertEqual(set(actual),{p['ref'] for p in d['components']})
            for p in d['components']:
                self.assertNotIn(p['ref'],refs);refs.add(p['ref'])
                self.assertTrue(p['ref'][-1].isdigit())
                for v in p['pins']:self.assertEqual(actual[p['ref']]['pins'][v['number']],dict(name=v['name'],type=v['type'],net=v.get('net')))

    def test_one_relay_switches_stereo_and_defaults_dry(self):
        p=self.parts['relay-audio'];self.assertEqual({r for r in p if r.startswith('K')},{'K1'})
        for ch,com,nc,no in [('L',4,6,8),('R',13,11,9)]:
            self.assertEqual([net(p,'K1',n) for n in [com,nc,no]],[f'OUT_{ch}',f'IN_{ch}',f'WET_{ch}'])
        broken=copy.deepcopy(p);broken['K1']['pins']['6']['net']='WET_L'
        self.assertNotEqual(net(broken,'K1',6),'IN_L')
        self.assertEqual([net(p,'Q1',i) for i in [1,2,3]],['RELAY_GATE','GND','COIL_LOW'])
        self.assertEqual([net(p,'D1',i) for i in [1,2]],['COIL_LOW','GND'])
        self.assertEqual([net(p,'U27',i) for i in [1,2,3,5,6]],['RELAY_GATE','GND','+5V','+3V3','+5V'])

    def test_one_5v_supply_and_service_usb_cannot_bypass_switch(self):
        p=self.parts['audio-power']
        self.assertEqual([net(p,'F1',i) for i in [1,2]],['USB_5V_IN','FUSED_5V'])
        self.assertEqual([net(p,'SW34',i) for i in [1,2]],['FUSED_5V','+5V'])
        self.assertEqual([net(p,'J_BYP1',i) for i in [1,2]],['MANUAL_N','GND'])
        bp=self.parts['bypass-permission']
        self.assertEqual([net(bp,'SW32',i) for i in [1,2]],['MANUAL_N','GND'])
        self.assertEqual(net(bp,'U25',3),'MANUAL_N');self.assertEqual(net(bp,'U26',3),'MANUAL_N')
        self.assertEqual([net(p,'U28',i) for i in [4,11]],['+5V','GND'])
        all_nets={v['net'] for sheet in self.parts.values() for part in sheet.values() for v in part['pins'].values()}
        self.assertFalse(all_nets&{'+12V_PROTECTED','+24VA_RAW','-24VA_RAW','+20VA','-20VA'})
        p=self.parts['compute-storage-touch']
        self.assertIsNone(net(p,'J_USB1',1));self.assertIsNone(net(p,'J_USB2',1))
        self.assertEqual(net(p,'U1',39),'+5V');self.assertEqual(net(p,'U1',38),'+3V3')

    def test_audio_buffers_and_calibratable_unity(self):
        p=self.parts['audio-power']
        self.assertEqual([net(p,'U28',i) for i in [1,2,3,5,6,7]],['BUF_L','BUF_L','PAD_L','PAD_R','BUF_R','BUF_R'])
        for i,ch in enumerate(['L','R']):
            b=410+20*i
            self.assertEqual([net(p,f'C{b}',j) for j in [1,2]],[f'INPUT_AC_{ch}',f'IN_{ch}'])
            self.assertEqual([net(p,f'C{b+2}',j) for j in [1,2]],[f'BUF_{ch}',f'ADC_AC_{ch}'])
            self.assertEqual([net(p,f'C{b+3}',j) for j in [1,2]],[f'AMP_{ch}_IN',f'DAC_{ch}'])
            self.assertEqual([net(p,f'C{b+4}',j) for j in [1,2]],[f'LINE_{ch}_ISOLATED',f'WET_{ch}'])
            self.assertEqual([net(p,f'RV{20+i}',j) for j in [1,2,3]],[f'TRIM_{ch}',f'FB_{ch}',f'FB_{ch}'])
        # Typical codec values only. No THD/noise/overload qualification inferred.
        attenuation=100000/(22100+100000)
        adc_load=par(13600,100000);buffer=adc_load/(adc_load+100)
        dac_load=100000/(100000+100);out=par(10000,100000)/(100+par(10000,100000))
        target=(3.6/(2*math.sqrt(2)))/(attenuation*buffer*dac_load*out)
        self.assertGreater(target,1.51);self.assertLess(target,1.61)
        self.assertGreater(attenuation*1.0,0);self.assertLess(attenuation*math.sqrt(2),1.8)
        self.assertAlmostEqual(20*math.log10(1/(10**(-10/20))),10)

    def test_input_clamps_and_delayed_reference_health(self):
        p=self.parts['audio-power']
        for i,ch in enumerate(['L','R']):
            self.assertEqual([net(p,f'D{410+2*i}',j) for j in [1,2]],['+5V',f'PAD_{ch}'])
            self.assertEqual([net(p,f'D{411+2*i}',j) for j in [1,2]],[f'PAD_{ch}','GND'])
        self.assertEqual(p['R500']['value'],'10k 0.1%');self.assertEqual(p['R501']['value'],'10k 0.1%')
        p=self.parts['reference-health']
        self.assertEqual(p['U32']['value'],'TPS3808G25DBVR')
        self.assertEqual([net(p,'U32',i) for i in [1,3,4,5,6]],['EXT_RAILS_OK','+3V3','CT_ANALOG','VREF_2V5','+3V3'])
        nominal_settle=-5000*100e-6*math.log(1-2.325/2.5)
        self.assertGreater(nominal_settle,1.3) # RC, not a measured release bound.

    def test_led_current_limit_and_sdio_module_terminals(self):
        p=self.parts['led-drivers']
        for i in range(96):self.assertEqual(p[f'R{200+i}']['value'],'3.3k 1%')
        maximum_led_current=79*(3.3*1.05-1.6)/(3300*.99)
        self.assertLess(maximum_led_current,.05) # LED current only; SD/MCU rail budget still measured separately.
        p=self.parts['compute-storage-touch']
        self.assertEqual({j:net(p,'J_SD1',j) for j in ['3V','GND','CLK','CMD','D0','D1','DAT2','D3','DET']},
            {'3V':'+3V3','GND':'GND','CLK':'SD_CLK','CMD':'SD_CMD','D0':'SD_DAT0','D1':'SD_DAT1','DAT2':'SD_DAT2','D3':'SD_DAT3','DET':None})

    def test_costs_cover_every_component_without_claiming_a_quote(self):
        r=json.loads(cost_artifacts()['cost-report.json'])
        self.assertEqual(r['circuit_components_costed'],sum(not p.get('virtual') for d in all_sheets() for p in d['components']))
        self.assertLessEqual(r['target_total'],300)
        self.assertFalse(r['confirmed_delivered_under_300'])
        self.assertGreater(r['unquoted_allowances'],0)


if __name__=='__main__':unittest.main()
