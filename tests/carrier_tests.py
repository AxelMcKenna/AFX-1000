#!/usr/bin/env python3
"""Read emitted CAD and verify carrier topology and explicit design budgets.

These are ideal connectivity/calculation tests. They do not replace KiCad ERC,
transistor/analog simulation, physical pin checks or commissioning measurements.
"""
import copy
import itertools
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import generate_carrier as source
from bypass_tests import read_circuit


def net(parts, ref, number):
    return parts[ref]['pins'][str(number)]['net']


def connected(parts, ref, a, b):
    return {net(parts,ref,1),net(parts,ref,2)} == {a,b}


def resistance(parts, ref):
    value=parts[ref]['value'].split()[0]
    if value.endswith('k'):
        return float(value[:-1])*1000
    return float(value)


def parallel(*resistors):
    return 1/sum(1/r for r in resistors)


def switched_pairs(parts, energized):
    pairs=[]
    for relay in ('K1','K2','K3'):
        for common,nc,no in ((4,6,8),(13,11,9)):
            pairs.append((net(parts,relay,common),net(parts,relay,no if energized else nc)))
    return pairs


class CarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets={d['project']:read_circuit((ROOT/'hardware/electrical'/(d['project']+'.kicad_sch')).read_text()) for d in source.all_sheets()}

    def test_all_emitted_pin_connections_match_source(self):
        refs=set()
        for sheet in source.all_sheets():
            actual=self.sheets[sheet['project']]
            self.assertEqual(set(actual),{p['ref'] for p in sheet['components']})
            for part in sheet['components']:
                self.assertNotIn(part['ref'],refs,'Reference collision across carrier sheets')
                refs.add(part['ref'])
                for p in part['pins']:
                    self.assertEqual(actual[part['ref']]['pins'][p['number']],dict(name=p['name'],type=p['type'],net=p.get('net')))
        bypass=read_circuit((ROOT/'hardware/electrical/bypass-permission.kicad_sch').read_text())
        self.assertFalse(refs&set(bypass),'Carrier/bypass reference collision')

    def test_deenergized_contacts_are_dry_and_amp_inputs_muted(self):
        p=self.sheets['relay-audio']
        expected={(f'OUT_{ch}_{leg}',f'IN_{ch}_{leg}') for ch in ('L','R') for leg in ('P','N')}
        self.assertEqual(set(switched_pairs(p,False)),expected|{('AMP_L_IN','GND'),('AMP_R_IN','GND')})
        expected={(f'OUT_{ch}_{leg}',f'WET_{ch}_{leg}') for ch in ('L','R') for leg in ('P','N')}
        self.assertEqual(set(switched_pairs(p,True)),expected|{('AMP_L_IN','DAC_L_AC'),('AMP_R_IN','DAC_R_AC')})
        broken=copy.deepcopy(p)
        broken['K1']['pins']['6']['net']='WET_L_P'
        self.assertNotEqual(switched_pairs(broken,False),switched_pairs(p,False))

    def test_driver_polarity_clamp_and_delay_are_independent(self):
        p=self.sheets['relay-audio']
        for q,d,gate,drain,sup,series,pull,command in [
            ('Q1','D1','RELAY_GATE','COIL_LOW','U27','R30','R31','CONTACTS_DRIVE'),
            ('Q2','D2','MUTE_GATE','MUTE_COIL_LOW','U34','R33','R34','MUTE_DRIVE')]:
            self.assertEqual([net(p,q,i) for i in (1,2,3)],[gate,'GND',drain])
            self.assertEqual([net(p,d,i) for i in (1,2)],[drain,'GND'])
            self.assertTrue(connected(p,series,command,gate))
            self.assertTrue(connected(p,pull,gate,'GND'))
            self.assertEqual([net(p,sup,i) for i in (1,2,3,4,5,6)],[gate,'GND','+5V',None,'+3V3','+5V'])
        self.assertNotEqual(net(p,'U27',1),net(p,'U34',1),'Common clamp would short the two independent gates and defeat the delay')
        self.assertEqual([net(p,'U33',i) for i in (1,3,4,5,6)],['CONTACTS_ENABLE','RELAY_PERMISSION',None,'+3V3','+3V3'])
        self.assertEqual([net(p,'U35',i) for i in range(1,15)],['CONTACTS_ENABLE','CONTACTS_N','CONTACTS_N','CONTACTS_DRIVE',
            'RELAY_PERMISSION','MUTE_N','GND','MUTE_DRIVE','MUTE_N',None,'GND',None,'GND','+5V'])
        self.assertEqual(p['U35']['value'],'74HCT14D,653')
        for relay,drain in [('K1','COIL_LOW'),('K2','COIL_LOW'),('K3','MUTE_COIL_LOW')]:
            self.assertEqual([net(p,relay,i) for i in (1,16)],['+5V',drain])

    def test_gate_and_coil_initial_room_temperature_budgets(self):
        d=source.relay_sheet()['design_limits']
        p=self.sheets['relay-audio']
        for series,pull in [('R30','R31'),('R33','R34')]:
            rs=resistance(p,series)*1.01
            rp=resistance(p,pull)*.99
            drive_min=d['buffer_voh_min']
            gate_min=drive_min*rp/(rs+rp)-d['gate_leakage_budget_a']*parallel(rs,rp)
            self.assertGreaterEqual(gate_min,d['qualified_vgs'])
            clamp_current=5.25/(resistance(p,series)*.99)
            self.assertLess(clamp_current,d['supervisor_sink_test_a'])
            # A passive 10k pull-up without U35 fails this on-state budget.
            if series=='R30':
                unbuffered=3.07*.985*rp/(10000+rs+rp)-2e-6*parallel(10000+rs,rp)
                self.assertLess(unbuffered,d['qualified_vgs'])
        total_count=d['coil_count']+d['mute_coil_count']
        maximum=total_count*d['supply_max']/(d['coil_ohm']*(1-d['coil_tolerance']))
        self.assertAlmostEqual(maximum,.35)
        self.assertLess(maximum,.4)
        self.assertLess(d['coil_count']*d['supply_max']/(d['coil_ohm']*.9)*d['mosfet_rds_ohm_at_2v5'],.02)
        self.assertLess(d['tvs_clamp_at_25c'],d['mosfet_vds_rating'])
        self.assertFalse(d['leakage_and_temperature_qualified'])
        self.assertFalse(d['release_latency_measured'])

    def test_32_button_scan_positions_match_firmware(self):
        p=self.sheets['button-inputs']
        # Manufacturer D7..D0 physical pins; Q7 is emitted before shift.
        pins=[6,5,4,3,14,13,12,11]
        stream=[]
        for i in range(4):
            ref=f'U{i+2}'
            self.assertEqual(net(p,ref,9),'BUTTON_DATA' if i==0 else f'BUTTON_SERIAL_{i}')
            self.assertEqual(net(p,ref,10),f'BUTTON_SERIAL_{i+1}' if i<3 else 'GND')
            self.assertEqual([net(p,ref,n) for n in (1,2,7,8,15,16)],['BUTTON_LOAD','BUTTON_CLOCK',None,'GND','GND','+3V3'])
            stream.extend(net(p,ref,n) for n in pins)
        self.assertEqual(stream,[f'BUTTON_{i:02}' for i in range(32)])
        for bit in range(32):
            self.assertTrue(connected(p,f'R{100+bit}','+3V3',stream[bit]))
            if bit<29:
                self.assertTrue(connected(p,f'SW{bit+1}',stream[bit],'GND'))
        self.assertEqual([net(p,'SW30',n) for n in (1,2,3)],['BUTTON_29','GND','BUTTON_30'])
        self.assertTrue(connected(p,'SW31','BUTTON_31','GND'))

    def test_mux_channels_and_unused_inputs(self):
        p=self.sheets['analog-controls']
        pins=[13,14,15,12,1,5,2,4]
        for index in range(2):
            ref=f'U{index+6}'
            self.assertEqual(net(p,ref,3),'MUX_A' if index==0 else 'MUX_B')
            self.assertEqual([net(p,ref,n) for n in (6,7,8,9,10,11,16)],['GND','GND','GND','MUX_S2','MUX_S1','MUX_S0','+3V3'])
            for j,pad in enumerate(pins):
                channel=index*8+j
                self.assertEqual(net(p,ref,pad),f'CONTROL_{channel:02}' if channel<11 else 'GND')
        for i in range(11):
            self.assertEqual([net(p,f'RV{i+1}',j) for j in (1,2,3)],['GND',f'WIPER_{i:02}','+3V3'])
            self.assertTrue(connected(p,f'R{140+i}',f'WIPER_{i:02}',f'CONTROL_{i:02}'))
            self.assertTrue(connected(p,f'C{120+i}',f'CONTROL_{i:02}','GND'))

    def test_led_serial_order_and_every_current_limiter(self):
        p=self.sheets['led-drivers']
        for i in range(12):
            ref=f'U{9+i}'
            self.assertEqual([net(p,ref,n) for n in (8,9,10,11,12,13,14,16)],
                ['GND',f'LED_SERIAL_{i+1}' if i<11 else None,'+3V3','LED_CLOCK','LED_LATCH','LED_OE_N','LED_DATA' if i==0 else f'LED_SERIAL_{i}','+3V3'])
            self.assertEqual([net(p,ref,n) for n in (15,1,2,3,4,5,6,7)],[f'LED_BIT_{i*8+j:02}' for j in range(8)])
        self.assertTrue(connected(p,'R160','+3V3','LED_OE_N'))
        # Shift the same 95..0 pattern used by ledFrame; newest byte stays
        # nearest the MCU. Check every single-bit frame, not just bit labels.
        for active in range(96):
            registers=[False]*96
            for bit in range(95,-1,-1):
                registers=[bit==active]+registers[:-1]
            self.assertEqual([i for i,b in enumerate(registers) if b],[active])
            self.assertTrue(connected(p,f'R{200+active}',f'LED_BIT_{active:02}',f'LED_ANODE_{active:02}'))
        for i in range(55):
            self.assertEqual([net(p,f'D{100+i}',n) for n in (1,2)],['GND',f'LED_ANODE_{i:02}'])
        for digit in range(3):
            self.assertEqual(net(p,f'DS{digit+1}','K'),'GND')
            self.assertEqual([net(p,f'DS{digit+1}',seg) for seg in ('a','b','c','d','e','f','g','dp')],
                [f'LED_ANODE_{55+digit*8+j:02}' for j in range(8)])

    def test_seed_physical_pad_numbers_and_sd_reservations(self):
        p=self.sheets['compute-storage-touch']
        expected={1:'BUTTON_LOAD',8:'BUTTON_CLOCK',9:'BUTTON_DATA',10:'LED_DATA',11:'LED_CLOCK',12:'TOUCH_SCL',13:'TOUCH_SDA',
            14:'LED_LATCH',15:'LED_OE_N',16:'ADC_L',17:'ADC_R',18:'DAC_L',19:'DAC_R',20:'GND',
            22:'MUX_A',23:'MUX_B',24:'DSP_READY',32:'MUX_S0',33:'MUX_S1',34:'MUX_S2',35:'HEARTBEAT',38:'+3V3',39:'+5V',40:'GND'}
        for pad,name in expected.items():
            self.assertEqual(net(p,'U1',pad),name)
        self.assertEqual([net(p,'U1',i) for i in range(2,8)],['SD_DAT3','SD_DAT2','SD_DAT1','SD_DAT0','SD_CMD','SD_CLK'])
        self.assertEqual([net(p,'J_SD1',i) for i in range(1,9)],['SD_DAT2','SD_DAT3','SD_CMD','+3V3','SD_CLK','GND','SD_DAT0','SD_DAT1'])
        pulled={net(p,f'R{i}',2) for i in range(550,555)}
        self.assertEqual(pulled,{'SD_DAT2','SD_DAT3','SD_DAT1','SD_DAT0','SD_CMD'})
        self.assertEqual([net(p,'U1',n) for n in (21,36,37)],[None,None,None])
        self.assertEqual([net(p,'U8',n) for n in ('VIN','GND','ADDR','3VO','SCL','SDA')],['+3V3','GND','GND',None,'TOUCH_SCL','TOUCH_SDA'])

    def test_named_harnesses_have_same_pin_order(self):
        links=[('compute-storage-touch','J_CPU1','button-inputs','J_BTN1'),
            ('compute-storage-touch','J_CPU2','analog-controls','J_ADC1'),
            ('compute-storage-touch','J_CPU3','led-drivers','J_LED1'),
            ('compute-storage-touch','J_CPU5','carrier-power','J_PWR2'),
            ('compute-storage-touch','J_CPU6','line-audio','J_AUD1'),
            ('line-audio','J_AUD2','carrier-power','J_PWR5'),
            ('relay-audio','J_RY1','carrier-power','J_PWR4'),
            ('line-audio','J_AUD3','relay-audio','J_RY3'),
            ('line-audio','J_AUD4','relay-audio','J_RY4'),
            ('line-audio','J_AUD5','relay-audio','J_RY5'),
            ('line-audio','J_AUD6','relay-audio','J_RY6'),
            ('analog-health','J_HL1','carrier-power','J_PWR6')]
        for sheet1,j1,sheet2,j2 in links:
            pins1=self.sheets[sheet1][j1]['pins']
            pins2=self.sheets[sheet2][j2]['pins']
            self.assertEqual({k:v['net'] for k,v in pins1.items()},{k:v['net'] for k,v in pins2.items()},(j1,j2))
        bypass=read_circuit((ROOT/'hardware/electrical/bypass-permission.kicad_sch').read_text())
        for sheet,ref,bp in [('relay-audio','J_RY2','J_BP4'),('analog-health','J_HL2','J_BP3'),
                             ('compute-storage-touch','J_CPU4','J_BP2'),('carrier-power','J_PWR3','J_BP1')]:
            self.assertEqual({k:v['net'] for k,v in self.sheets[sheet][ref]['pins'].items()},
                             {k:v['net'] for k,v in bypass[bp]['pins'].items()})

    def test_power_polarity_and_correct_ldo_pinouts(self):
        p=self.sheets['carrier-power']
        self.assertTrue(connected(p,'F1','DC_IN_P','DC_FUSED'))
        self.assertTrue(connected(p,'SW34','DC_FUSED','DC_SWITCHED'))
        self.assertEqual([net(p,'D3',i) for i in (1,2)],['+12V_PROTECTED','DC_SWITCHED'])
        self.assertEqual([net(p,'PS1',i) for i in (1,2,3)],['+12V_PROTECTED','GND','+5V'])
        for ref,plus,minus in [('PS2','+24VA_RAW','GND'),('PS3','GND','-24VA_RAW')]:
            self.assertEqual([net(p,ref,i) for i in (1,2,3,5,6,7,8)],['GND','+12V_PROTECTED',None,None,plus,minus,None])
        self.assertEqual([net(p,'U29',i) for i in range(1,14)],[None,'+20VA','+20VA','ADJ_POS','GND',None,None,'+24VA_RAW',None,'+24VA_RAW','+24VA_RAW',None,'GND'])
        self.assertEqual([net(p,'U30',i) for i in range(1,6)],['-24VA_RAW','GND','-24VA_RAW','ADJ_NEG','-20VA'])
        positive=1.24*(1+resistance(p,'R500')/resistance(p,'R501'))
        negative=1.22*(1+resistance(p,'R502')/resistance(p,'R503'))
        self.assertAlmostEqual(positive,19.964)
        self.assertAlmostEqual(negative,20.008)
        for v in (positive,negative):
            self.assertGreater(v*.97,19)
            self.assertLess(v*1.03,22)
            self.assertGreater(24*.97-v*1.03,1)

    def test_rail_comparator_direction_reference_guard_and_settling(self):
        p=self.sheets['analog-health']
        self.assertEqual([net(p,'U31',i) for i in range(1,9)],['ANALOG_RAW_OK','REF_0409','SENSE_POS','GND','REF_0409','SENSE_NEG','ANALOG_RAW_OK','+5V'])
        self.assertEqual([net(p,'D4',i) for i in (1,2,3)],['REF_2V5','GND','GND'])
        self.assertEqual([net(p,'U36',i) for i in range(1,7)],['ANALOG_RAW_OK','GND','+3V3',None,'REF_2V5','+3V3'])
        self.assertEqual([net(p,'U32',i) for i in range(1,7)],['EXT_RAILS_OK','GND','ANALOG_RAW_OK','CT_ANALOG','+3V3','+3V3'])
        self.assertTrue(connected(p,'R529','CT_ANALOG','+3V3'))
        ref=2.5*resistance(p,'R522')/(resistance(p,'R521')+resistance(p,'R522'))
        def good(pos,neg):
            a=pos*resistance(p,'R524')/(resistance(p,'R523')+resistance(p,'R524'))
            b=(2.5/resistance(p,'R525')+neg/resistance(p,'R526'))/(1/resistance(p,'R525')+1/resistance(p,'R526'))
            return a>=ref and ref>=b
        for pos,neg in itertools.product((0,5,15,18,20), (0,-5,-15,-18,-20)):
            self.assertEqual(good(pos,neg),pos==20 and neg==-20,(pos,neg))
        self.assertFalse(good(0,-20))
        self.assertFalse(good(20,0))

    def test_audio_closed_feedback_and_passive_adc_pad(self):
        p=self.sheets['line-audio']
        self.assertEqual([net(p,'U28',i) for i in range(1,9)],['LINE_L_RAW','FB_L','AMP_L_IN','-20VA','AMP_R_IN','FB_R','LINE_R_RAW','+20VA'])
        for index,ch in enumerate(('L','R')):
            r=400+index*20
            self.assertTrue(connected(p,f'R{r}',f'IN_{ch}_P',f'ADC_{ch}'))
            self.assertTrue(connected(p,f'R{r+1}',f'ADC_{ch}','GND'))
            self.assertTrue(connected(p,f'R{r+2}',f'ADC_{ch}',f'PAD_{ch}_MASTER'))
            self.assertTrue(connected(p,f'R{r+5}',f'FB_{ch}','GND'))
            self.assertTrue(connected(p,f'R{r+6}',f'LINE_{ch}_RAW',f'MASTER_TRIM_{ch}'))
            self.assertEqual(net(p,f'RV{20+index*2}',2),net(p,f'RV{20+index*2}',3))
            self.assertEqual(net(p,f'RV{21+index*2}',2),net(p,f'RV{21+index*2}',3))
            for j,prefix in enumerate(('IN','WET','OUT')):
                self.assertTrue(connected(p,f'R{r+10+j}',f'{prefix}_{ch}_N','GND'))
            # A single ganged switch changes both pads and feedback branches.
            # Base feedback remains connected in both modes and during travel.
            pole=index+1
            self.assertEqual([net(p,'SW33',f'{pole}{contact}') for contact in ('C','M','S')],['GND',f'PAD_{ch}_MASTER',None])
            pole=index+3
            self.assertEqual([net(p,'SW33',f'{pole}{contact}') for contact in ('C','M','S')],[f'FB_{ch}',None,f'SEND_FB_{ch}'])

    def test_typical_converter_gain_and_headroom_calculations(self):
        p=self.sheets['line-audio']
        assumptions=source.line_audio_sheet()['design_assumptions']
        fs=assumptions['adc_full_scale_vrms']
        master_max=.7745966692*10**((4+20)/20)
        send_max=10**((-10+20)/20)
        dac_load=parallel(100000,47000)
        dac_factor=dac_load/(dac_load+100)
        out_load=parallel(100000,10000)
        out_factor=out_load/(out_load+100)
        for master,maximum in ((True,master_max),(False,send_max)):
            shunt=parallel(680000,2870) if master else 680000
            effective=parallel(shunt,13600)
            attenuation=effective/(22100+effective)
            self.assertGreater(22100+effective,22000)
            self.assertLess(maximum*attenuation*math.sqrt(2),1.8)
            needed_gain=fs/(attenuation*dac_factor*out_factor)
            if master:
                gain_min,gain_max=1+12100/1000,1+12600/1000
            else:
                gain_min=1+parallel(12100,3010)/1000
                gain_max=1+parallel(12600,3210)/1000
            self.assertGreaterEqual(needed_gain,gain_min)
            self.assertLessEqual(needed_gain,gain_max)
        # Worst initial resistor tolerances at a TYPICAL module impedance.
        # Module impedance/FS tolerances are intentionally not invented here.
        for topf,bottomf,padf in itertools.product((.99,1.01),repeat=3):
            effective=parallel(680000*bottomf,2870*padf,13600)
            adc_peak=master_max*effective/(22100*topf+effective)*math.sqrt(2)
            self.assertLess(adc_peak,1.8)
        self.assertFalse(assumptions['electrical_performance_measured'])


if __name__=='__main__':
    unittest.main()
