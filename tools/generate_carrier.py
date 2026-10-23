#!/usr/bin/env python3
"""Carrier circuit sources and reproducible, pin-connected KiCad drafts.

These drawings describe real pin numbers and nets, not PCB placement. They are
engineering drafts until native ERC, footprint review and bench qualification.
"""
import argparse
import copy
import csv
import io
import json
from pathlib import Path
from generate_bypass import artifacts, validate, schematic, library_symbol, uid, quote, effects

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'hardware/electrical'
DOC = 'hardware/electrical/carrier.md'
TI_SUPERVISOR = 'https://www.ti.com/lit/gpn/tps3808'
OMRON = 'https://omronfs.omron.com/en_US/ecb/products/pdf/en-g5v_2.pdf'
MOSFET = 'https://www.diodes.com/datasheet/download/DMN3023L.pdf'
TVS = 'https://www.littelfuse.com/assetdocs/tvs-diodes-smaj-datasheet?assetguid=13c2a823-03b8-4d1f-9ddc-9b44670aed9d'


def pin(number, name, net, kind='passive'):
    return dict(number=str(number), name=name, type=kind,
                **({'net': net} if net is not None else {'no_connect': True}))


class Sheet:
    def __init__(self, name, title, notes):
        self.data = dict(schema=1, revision='A0.2-draft', project=name,
                         title='RMX - ' + title, paper='A0', mcu_gpio={},
                         bom_file=name + '-bom.csv', sheet_notes=notes,
                         components=[])

    def part(self, ref, value, pins, source=DOC, footprint='', package='', mpn='', qualification='Native ERC, footprint and bench qualification pending'):
        assert ref[-1].isdigit(), 'KiCad requires an annotated numeric suffix: '+ref
        self.data['components'].append(dict(ref=ref, value=value, pins=pins,
            source=source, footprint=footprint, package=package, mpn=mpn,
            qualification=qualification, at=[0, 0]))

    def two(self, ref, value, a, b, footprint='', package='', mpn='', source=DOC):
        self.part(ref, value, [pin(1,'1',a),pin(2,'2',b)], source, footprint, package, mpn)

    def resistor(self, ref, value, a, b):
        self.two(ref, value + ' 1%', a, b, 'Resistor_SMD:R_0603_1608Metric', '0603')

    def cap(self, ref, value, a, b):
        self.two(ref, value, a, b, 'Capacitor_SMD:C_0805_2012Metric', '0805; dielectric/voltage per value')

    def header(self, ref, name, nets):
        self.part(ref, name, [pin(i+1,n,n) for i,n in enumerate(nets)],
            footprint=f'Connector_PinHeader_2.54mm:PinHeader_1x{len(nets):02}_P2.54mm_Vertical',
            package=f'1x{len(nets)} 2.54 mm; shrouded/keyed production connector pending')

    def finish(self):
        # Group components into rows with variable height. All positions lie on
        # KiCad's 50-mil grid; a tall module cannot overlap the next row.
        parts = self.data['components']
        for paper,columns,height in [('A2',5,420),('A1',7,594),('A0',10,841)]:
            y = 63.5
            for first in range(0, len(parts), columns):
                row = parts[first:first+columns]
                half = max(max(3.81,(len(p['pins'])+1)*1.27) for p in row)
                for col, p in enumerate(row):
                    p['at'] = [round(45.72+111.76*col,5),round(y+half,5)]
                y += half*2 + 17.78
            if y < height-20:
                self.data['paper']=paper
                break
        else:
            raise ValueError(f'{self.data["project"]}: split oversized sheet ({y:g}mm)')
        validate(self.data)
        return self.data


def relay_sheet():
    s = Sheet('relay-audio', 'de-energized dry audio and coil driver', [
        'RMX A0.2 / RELAY DRIVER AND AUDIO CONTACTS / DRAFT - no fabrication release',
        'NC selects dry; NO selects processed. Both poles switch, permitting balanced harness use. All coil current returns directly to power ground.',
        'K3 first releases the input mute; U33 delays K1/K2 reconnect. Q1/Q2 each have a local pull-down and separate 5V-powered 3V3 clamp.',
        'D1 is a drain-to-ground unidirectional TVS, not a diode across the coils. Scope flyback energy, overshoot and release time.',
    ])
    s.header('J_RY1', 'REGULATED POWER', ['+5V','+3V3','GND'])
    s.header('J_RY2', 'FROM BYPASS J_BP4', ['RELAY_PERMISSION','GND'])
    s.part('Q1','DMN3023L-7', [pin(1,'G','RELAY_GATE','input'),pin(2,'S','GND'),pin(3,'D','COIL_LOW')],
        MOSFET,'Package_TO_SOT_SMD:SOT-23','SOT-23','DMN3023L-7')
    s.resistor('R30','10k','CONTACTS_DRIVE','RELAY_GATE')
    s.resistor('R31','100k','RELAY_GATE','GND')
    s.part('D1','SMAJ12A (Littelfuse)',[pin(1,'K','COIL_LOW'),pin(2,'A','GND')],
        TVS,'Diode_SMD:D_SMA','DO-214AC SMA','SMAJ12A',
        '12V standoff; 19.9V max specified clamp at 20.1A/25C; pulse/temperature/lead overshoot qualification required')
    s.part('U27','TPS3808G33DBVR',[
        pin(1,'RESET_N','RELAY_GATE','open_collector'),pin(2,'GND','GND','power_in'),
        pin(3,'MR_N','+5V','input'),pin(4,'CT',None,'input'),
        pin(5,'SENSE','+3V3','input'),pin(6,'VDD','+5V','power_in')],
        TI_SUPERVISOR,'Package_TO_SOT_SMD:SOT-23-6','SOT-23-6','TPS3808G33DBVR',
        'Independent local clamp powered by coil supply; CT open = 20ms nominal. No blanket guarantee outside supervisor valid supply range.')
    s.cap('C30','100nF X7R 25V','+5V','GND')
    s.two('C31','47uF 16V electrolytic (+ to 5V)','+5V','GND',
          'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm','radial 5mm; exact series pending')
    for ref, ch in [('K1','L'),('K2','R')]:
        s.part(ref,'G5V-2 DC5',[
            pin(1,'COIL_A','+5V'),pin(16,'COIL_B','COIL_LOW'),
            pin(4,'COM_1',f'OUT_{ch}_P'),pin(6,'NC_1',f'IN_{ch}_P'),pin(8,'NO_1',f'WET_{ch}_P'),
            pin(13,'COM_2',f'OUT_{ch}_N'),pin(11,'NC_2',f'IN_{ch}_N'),pin(9,'NO_2',f'WET_{ch}_N')],
            OMRON,'Relay_THT:Relay_DPDT_Omron_G5V-2','DIP DPDT non-latching','G5V-2 DC5',
            'STANDARD 500mW coil, not H1: 50 ohm +/-10% at 23C. Verify bottom-view footprint by unpowered continuity before assembly.')
    for i, prefix in enumerate(('IN','WET','OUT')):
        s.header(f'J_RY{i+3}', prefix+' AUDIO',
            [f'{prefix}_L_P',f'{prefix}_L_N','GND',f'{prefix}_R_P',f'{prefix}_R_N','GND'])
    s.part('U33','TPS3808G33DBVR',[
        pin(1,'RESET_N','CONTACTS_ENABLE','open_collector'),pin(2,'GND','GND','power_in'),
        pin(3,'MR_N','RELAY_PERMISSION','input'),pin(4,'CT',None,'input'),
        pin(5,'SENSE','+3V3','input'),pin(6,'VDD','+3V3','power_in')],
        TI_SUPERVISOR,'Package_TO_SOT_SMD:SOT-23-6','SOT-23-6','TPS3808G33DBVR',
        '20ms nominal output contact enable delay after permission, immediate fault assertion; verify minimum delay versus K3 maximum operation time')
    s.resistor('R32','10k','+3V3','CONTACTS_ENABLE')
    s.part('U35','74HCT14D,653',[
        pin(1,'1A','CONTACTS_ENABLE','input'),pin(2,'1Y','CONTACTS_N','output'),
        pin(3,'2A','CONTACTS_N','input'),pin(4,'2Y','CONTACTS_DRIVE','output'),
        pin(5,'3A','RELAY_PERMISSION','input'),pin(6,'3Y','MUTE_N','output'),
        pin(7,'GND','GND','power_in'),pin(8,'4Y','MUTE_DRIVE','output'),pin(9,'4A','MUTE_N','input'),
        pin(10,'5Y',None,'output'),pin(11,'5A','GND','input'),pin(12,'6Y',None,'output'),
        pin(13,'6A','GND','input'),pin(14,'VCC','+5V','power_in')],
        'https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf',
        'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm','SOIC-14','74HCT14D,653',
        'Two Schmitt inverters per non-inverting 5V gate drive. TTL thresholds accept 3.3V; Schmitt inputs tolerate supervisor pull-up rise. Do not substitute HC.')
    s.resistor('R33','10k','MUTE_DRIVE','MUTE_GATE')
    s.resistor('R34','100k','MUTE_GATE','GND')
    s.part('Q2','DMN3023L-7',[pin(1,'G','MUTE_GATE','input'),pin(2,'S','GND'),pin(3,'D','MUTE_COIL_LOW')],
        MOSFET,'Package_TO_SOT_SMD:SOT-23','SOT-23','DMN3023L-7')
    s.part('D2','SMAJ12A (Littelfuse)',[pin(1,'K','MUTE_COIL_LOW'),pin(2,'A','GND')],
        TVS,'Diode_SMD:D_SMA','DO-214AC SMA','SMAJ12A')
    s.part('U34','TPS3808G33DBVR',[
        pin(1,'RESET_N','MUTE_GATE','open_collector'),pin(2,'GND','GND','power_in'),
        pin(3,'MR_N','+5V','input'),pin(4,'CT',None,'input'),
        pin(5,'SENSE','+3V3','input'),pin(6,'VDD','+5V','power_in')],
        TI_SUPERVISOR,'Package_TO_SOT_SMD:SOT-23-6','SOT-23-6','TPS3808G33DBVR')
    s.part('K3','G5V-2 DC5',[
        pin(1,'COIL_A','+5V'),pin(16,'COIL_B','MUTE_COIL_LOW'),
        pin(4,'COM_1','AMP_L_IN'),pin(6,'NC_1','GND'),pin(8,'NO_1','DAC_L_AC'),
        pin(13,'COM_2','AMP_R_IN'),pin(11,'NC_2','GND'),pin(9,'NO_2','DAC_R_AC')],
        OMRON,'Relay_THT:Relay_DPDT_Omron_G5V-2','DIP DPDT non-latching','G5V-2 DC5',
        'Unpowered clamps line amplifier inputs to ground; processed input release precedes delayed output contacts. Pop/click and dropout ordering need physical measurement.')
    s.cap('C32','100nF X7R 25V','+3V3','GND')
    s.cap('C33','100nF X7R 25V','+5V','GND')
    s.cap('C34','100nF X7R 25V','+5V','GND')
    s.header('J_RY6','MUTE TO LINE AUDIO',['AMP_L_IN','DAC_L_AC','GND','AMP_R_IN','DAC_R_AC','GND'])
    d = s.finish()
    d['design_limits'] = dict(coil_ohm=50, coil_tolerance=.1, coil_count=2,
        mute_coil_count=1, supply_min=4.75, supply_max=5.25, mosfet_rds_ohm_at_2v5=.068,
        mosfet_vds_rating=30, tvs_clamp_at_25c=19.9,
        gate_series_ohm=10000, gate_pull_down_ohm=100000,
        resistor_tolerance=.01, supervisor_threshold=3.07,
        supervisor_threshold_tolerance=.015, buffer_voh_min=3.7, buffer_vih_min=2.1,
        gate_leakage_budget_a=2e-6, qualified_vgs=2.5,
        supervisor_vol_max=.4, supervisor_sink_test_a=.001,
        leakage_and_temperature_qualified=False,
        release_latency_measured=False)
    return d


HC165 = 'https://assets.nexperia.com/documents/data-sheet/74HC_HCT165.pdf'
HC595 = 'https://assets.nexperia.com/documents/data-sheet/74HC_HCT595.pdf'
HC4051 = 'https://assets.nexperia.com/documents/data-sheet/74HC_HCT4051.pdf'
SO16 = 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm'


def button_sheet():
    s = Sheet('button-inputs','32 switch inputs',[
        'RMX A0.2 / BUTTONS / DRAFT - active-low switches, all logic at 3.3V',
        'U2 is nearest MCU: Q7 is read BEFORE shifting. H/D7 is bit 0; A/D0 is bit 7. Tail serial input is grounded.',
        'SW30/SW31 pin names are project harness positions, not a frozen manufacturer footprint.',
    ])
    s.data['mcu_gpio'] = {k:v for k,v in json.loads((ROOT/'hardware/prototype.json').read_text())['pins'].items() if k.startswith('button_')}
    s.header('J_BTN1','SEED BUTTON HARNESS',['+3V3','GND','BUTTON_LOAD','BUTTON_CLOCK','BUTTON_DATA'])
    data_pins = [11,12,13,14,3,4,5,6] # A through H / D0 through D7
    proto = json.loads((ROOT/'hardware/prototype.json').read_text())
    names = {c['channel']:c['label'] for c in proto['controls'] if c['kind']=='button'}
    for index in range(4):
        pins = [pin(1,'PL_N','BUTTON_LOAD','input'),pin(2,'CP','BUTTON_CLOCK','input'),
                pin(7,'Q7_N',None,'output'),pin(8,'GND','GND','power_in'),
                pin(9,'Q7','BUTTON_DATA' if index==0 else f'BUTTON_SERIAL_{index}','output'),
                pin(10,'DS',f'BUTTON_SERIAL_{index+1}' if index<3 else 'GND','input'),
                pin(15,'CE','GND','input'),pin(16,'VCC','+3V3','power_in')]
        pins += [pin(n,f'D{j}',f'BUTTON_{index*8+7-j:02}','input') for j,n in enumerate(data_pins)]
        s.part(f'U{index+2}','74HC165D,653',pins,HC165,SO16,'SOIC-16','74HC165D,653')
        s.cap(f'C{100+index}','100nF X7R 25V','+3V3','GND')
    for bit in range(32):
        s.resistor(f'R{100+bit}','10k','+3V3',f'BUTTON_{bit:02}')
        if bit<29:
            s.two(f'SW{bit+1}',names[bit]+' NO',f'BUTTON_{bit:02}','GND',package='panel momentary; part dimensions pending')
    s.part('SW30','BACK / ECHO / BRAKE ON-OFF-ON',[
        pin(1,'BACK','BUTTON_29'),pin(2,'COMMON','GND'),pin(3,'BRAKE','BUTTON_30')],
        package='SPDT center-off panel switch; harness numbering only')
    s.two('SW31','DEFAULT / USER (closed = User)','BUTTON_31','GND',package='SPST/SPDT panel switch; harness numbering only')
    return s.finish()


def analog_control_sheet():
    s = Sheet('analog-controls','knob and release-lever scan',[
        'RMX A0.2 / ANALOG CONTROLS / DRAFT - 10k linear pots, 1k / 10nF pre-mux filter',
        'All pot high terminals and mux VCC use the same 3.3V source as the Seed ADC reference. Never feed 5V into these inputs.',
        'Mux B Y3..Y7 are grounded. Shared address lines require synchronized eight-position scans; verify on the board.',
    ])
    proto = json.loads((ROOT/'hardware/prototype.json').read_text())
    s.data['mcu_gpio'] = {k:proto['pins'][k] for k in ('adc_mux_a','adc_mux_b','mux_s0','mux_s1','mux_s2')}
    s.header('J_ADC1','SEED ADC/MUX',['+3V3','GND','MUX_A','MUX_B','MUX_S0','MUX_S1','MUX_S2'])
    channel_pins = [13,14,15,12,1,5,2,4]
    for index in range(2):
        pins=[pin(3,'Z','MUX_A' if index==0 else 'MUX_B'),pin(6,'E','GND','input'),
              pin(7,'VEE','GND','power_in'),pin(8,'GND','GND','power_in'),
              pin(9,'S2','MUX_S2','input'),pin(10,'S1','MUX_S1','input'),pin(11,'S0','MUX_S0','input'),
              pin(16,'VCC','+3V3','power_in')]
        pins += [pin(n,f'Y{j}',f'CONTROL_{index*8+j:02}' if index*8+j<11 else 'GND') for j,n in enumerate(channel_pins)]
        s.part(f'U{6+index}','74HC4051D,653',pins,HC4051,SO16,'SOIC-16','74HC4051D,653')
        s.cap(f'C{110+index}','100nF X7R 25V','+3V3','GND')
    for i,name in enumerate(proto['adc_params']):
        s.part(f'RV{i+1}',f'10k linear {name}',[
            pin(1,'CCW','GND'),pin(2,'WIPER',f'WIPER_{i:02}'),pin(3,'CW','+3V3')],
            package='panel pot; RV11 spring-return lever position sensor; footprint not frozen')
        s.resistor(f'R{140+i}','1k',f'WIPER_{i:02}',f'CONTROL_{i:02}')
        s.cap(f'C{120+i}','10nF X7R 25V',f'CONTROL_{i:02}','GND')
    return s.finish()


def led_sheet():
    s = Sheet('led-drivers','static 96-bit LED chain',[
        'RMX A0.2 / LEDS / DRAFT - common-cathode display, 1k per lit segment, 3.3V HC logic',
        'U9 nearest MCU drives bits 0..7. Its Q7S feeds U10 DS. Clock/latch shared. OE pull-up keeps outputs dark through reset.',
        'Do not replace common-cathode digits with common-anode parts. Final display pinout and panel footprints are release gates.',
    ])
    proto = json.loads((ROOT/'hardware/prototype.json').read_text())
    s.data['mcu_gpio'] = {k:v for k,v in proto['pins'].items() if k.startswith('led_')}
    s.header('J_LED1','SEED LED HARNESS',['+3V3','GND','LED_DATA','LED_CLOCK','LED_LATCH','LED_OE_N'])
    s.resistor('R160','47k','LED_OE_N','+3V3')
    for i in range(12):
        pins=[pin(8,'GND','GND','power_in'),pin(9,'Q7S',f'LED_SERIAL_{i+1}' if i<11 else None,'output'),
              pin(10,'MR_N','+3V3','input'),pin(11,'SHCP','LED_CLOCK','input'),
              pin(12,'STCP','LED_LATCH','input'),pin(13,'OE_N','LED_OE_N','input'),
              pin(14,'DS','LED_DATA' if i==0 else f'LED_SERIAL_{i}','input'),pin(16,'VCC','+3V3','power_in')]
        pins += [pin(n,f'Q{j}',f'LED_BIT_{8*i+j:02}','output') for j,n in enumerate([15,1,2,3,4,5,6,7])]
        s.part(f'U{9+i}','74HC595D,118',pins,HC595,SO16,'SOIC-16','74HC595D,118')
        s.cap(f'C{160+i}','100nF X7R 25V','+3V3','GND')
    # All 96 outputs have resistors. Unused positions terminate on labelled
    # expansion pads; no unbounded path from a register output to a LED.
    for bit in range(96):
        s.resistor(f'R{200+bit}','1k',f'LED_BIT_{bit:02}',f'LED_ANODE_{bit:02}')
        if bit < 55:
            s.part(f'D{100+bit}',f'LOW CURRENT LED bit {bit}',[
                pin(1,'K','GND'),pin(2,'A',f'LED_ANODE_{bit:02}')],package='LED_0603/panel light pipe; exact color/bin pending')
    for digit in range(3):
        s.part(f'DS{digit+1}','COMMON CATHODE DIGIT',[
            pin(seg,seg,f'LED_ANODE_{55+digit*8+i:02}') for i,seg in enumerate(('a','b','c','d','e','f','g','dp'))
        ]+[pin('K','COMMON_K','GND')],package='display module terminal names; numerical pinout pending selected module')
    for start in (79,87):
        s.header(f'J_LED{start}','RESERVED LED ANODES',[f'LED_ANODE_{i:02}' for i in range(start,min(start+8,96))]+['GND'])
    s.header('J_LED95','RESERVED LED ANODE',['LED_ANODE_95','GND'])
    return s.finish()


LME = 'https://www.ti.com/lit/ds/symlink/lme49860.pdf'
SEED = 'https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed/Daisy_Seed_datasheet.pdf'


def line_audio_sheet():
    s = Sheet('line-audio','unbalanced line interface and gain modes',[
        'RMX A0.2 / LINE AUDIO / DRAFT - RCA and TS harness, 10kohm minimum external load; match the actual Rev7 Seed by calibration',
        'Passive ADC pad includes the Seed 13.6kohm TYPICAL input impedance. No high-voltage amplifier is connected to the ADC input.',
        'SW33 is one four-pole mode switch: MASTER adds input shunts; SEND/RETURN adds output feedback shunts. Change modes in manual bypass.',
        'K3 mute is on relay-audio; delayed K1/K2 choose dry/wet. Pop/click, stability, headroom, protection and final parts require physical validation.',
    ])
    s.header('J_AUD1','SEED AUDIO HEADER PINS 16/17/18/19/20',[
        'ADC_L','ADC_R','DAC_L','DAC_R','GND'])
    s.header('J_AUD2','ANALOG POWER',['+20VA','GND','-20VA'])
    for ch in ('L','R'):
        # Both connector types are the same unbalanced signal. Only one input
        # family is used at a time; external sources must never be joined.
        s.part('J_IN_'+ch+'1','TS INPUT '+ch,[pin('T','TIP',f'IN_{ch}_P'),pin('S','SLEEVE','GND')],
            package='isolated panel TS jack; no normal contact model until part is frozen')
        s.part('J_RCA_IN_'+ch+'1','RCA INPUT '+ch,[pin('C','CENTER',f'IN_{ch}_P'),pin('S','SHELL','GND')],
            package='isolated panel RCA jack; exact part pending')
        s.part('J_OUT_'+ch+'1','TS OUTPUT '+ch,[pin('T','TIP',f'OUT_{ch}_P'),pin('S','SLEEVE','GND')],
            package='isolated panel TS jack; exact part pending')
        s.part('J_RCA_OUT_'+ch+'1','RCA OUTPUT '+ch,[pin('C','CENTER',f'OUT_{ch}_P'),pin('S','SHELL','GND')],
            package='isolated panel RCA jack; exact part pending')
    s.part('U28','LME49860MAX/NOPB',[
        pin(1,'OUT_A','LINE_L_RAW','output'),pin(2,'IN_A_N','FB_L','input'),pin(3,'IN_A_P','AMP_L_IN','input'),
        pin(4,'VEE','-20VA','power_in'),pin(5,'IN_B_P','AMP_R_IN','input'),
        pin(6,'IN_B_N','FB_R','input'),pin(7,'OUT_B','LINE_R_RAW','output'),pin(8,'VCC','+20VA','power_in')],
        LME,'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm','SOIC-8','LME49860MAX/NOPB',
        '44V maximum operating total supply; do not connect raw +/-24V rails. Stability and full-band output swing need board tests.')
    s.cap('C400','100nF X7R 50V','+20VA','GND')
    s.cap('C401','100nF X7R 50V','GND','-20VA')
    switch_pins=[]
    for i,ch in enumerate(('L','R')):
        base=400+i*20
        # These pads are passive even when power is off. The carrier must be
        # calibrated against the actual module impedance and converter levels.
        s.resistor(f'R{base}','22.1k',f'IN_{ch}_P',f'ADC_{ch}')
        s.resistor(f'R{base+1}','680k',f'ADC_{ch}','GND')
        s.resistor(f'R{base+2}','2.87k',f'ADC_{ch}',f'PAD_{ch}_MASTER')
        # K3 sees AC-coupled converter output and clamps the amp input when off.
        s.two(f'C{base+2}','4.7uF film 50V',f'DAC_{ch}',f'DAC_{ch}_AC',package='film; actual dimensions pending')
        s.resistor(f'R{base+3}','100k',f'DAC_{ch}_AC','GND')
        s.resistor(f'R{base+4}','47k',f'AMP_{ch}_IN','GND')
        s.resistor(f'R{base+5}','1k',f'FB_{ch}','GND')
        s.resistor(f'R{base+6}','12.1k',f'LINE_{ch}_RAW',f'MASTER_TRIM_{ch}')
        s.part(f'RV{20+i*2}','500 ohm MASTER trim',[
            pin(1,'END_A',f'MASTER_TRIM_{ch}'),pin(2,'WIPER',f'FB_{ch}'),pin(3,'END_B',f'FB_{ch}')],
            package='multiturn trim; wiper strapped to end B; no open-loop failure on wiper loss')
        s.resistor(f'R{base+7}','3.01k',f'LINE_{ch}_RAW',f'SEND_TRIM_{ch}')
        s.part(f'RV{21+i*2}','200 ohm SEND trim',[
            pin(1,'END_A',f'SEND_TRIM_{ch}'),pin(2,'WIPER',f'SEND_FB_{ch}'),pin(3,'END_B',f'SEND_FB_{ch}')],
            package='multiturn trim; wiper strapped to end B')
        # Film bypass is not a substitute for evaluating the op amp with the
        # real converter, cable capacitance and output load.
        s.resistor(f'R{base+8}','100',f'LINE_{ch}_RAW',f'LINE_{ch}_ISOLATED')
        s.two(f'C{base+3}','22uF bipolar 50V',f'LINE_{ch}_ISOLATED',f'WET_{ch}_P',
            package='bipolar audio electrolytic; ESR and physical part pending')
        s.resistor(f'R{base+9}','100k',f'WET_{ch}_P','GND')
        for j,prefix in enumerate(('IN','WET','OUT')):
            s.two(f'R{base+10+j}','0 ohm UNBALANCED RETURN STRAP',f'{prefix}_{ch}_N','GND',
                  'Resistor_SMD:R_0603_1608Metric','0603')
        # Four poles, each C/MASTER/SEND. Terminal identifiers deliberately
        # remain harness identifiers until an exact switch is selected.
        switch_pins += [pin(f'{i+1}C','COMMON','GND'),pin(f'{i+1}M','MASTER',f'PAD_{ch}_MASTER'),pin(f'{i+1}S','SEND',None)]
        switch_pins += [pin(f'{i+3}C','COMMON',f'FB_{ch}'),pin(f'{i+3}M','MASTER',None),pin(f'{i+3}S','SEND',f'SEND_FB_{ch}')]
    s.part('SW33','4PDT MASTER / SEND-RETURN',switch_pins,
        package='one mechanically ganged four-pole switch; harness terminal IDs; exact switch/footprint pending')
    s.header('J_AUD3','DRY TO RELAY J_RY3',['IN_L_P','IN_L_N','GND','IN_R_P','IN_R_N','GND'])
    s.header('J_AUD4','WET TO RELAY J_RY4',['WET_L_P','WET_L_N','GND','WET_R_P','WET_R_N','GND'])
    s.header('J_AUD5','OUTPUT FROM RELAY J_RY5',['OUT_L_P','OUT_L_N','GND','OUT_R_P','OUT_R_N','GND'])
    s.header('J_AUD6','MUTE FROM RELAY J_RY6',['AMP_L_IN','DAC_L_AC','GND','AMP_R_IN','DAC_R_AC','GND'])
    d=s.finish()
    d['design_assumptions'] = dict(codec_revision='Daisy Seed Rev7 PCM3060',
        adc_full_scale_vrms=3.6/(2*2**.5), adc_input_ohm_typical=13600,
        dac_full_scale_vrms=1, dac_source_ohm_typical=100,
        master_nominal_dbu=4, send_nominal_dbv=-10, headroom_db=20,
        minimum_external_load_ohm=10000, analog_rails_nominal_v=20,
        calibration_required=True, input_protection_qualified=False,
        mono_normalling_implemented=False, electrical_performance_measured=False)
    return d


TRACO_TMR = 'https://www.tracopower.com/products/tmr6.pdf'
TRACO_TSR = 'https://www.tracopower.com/sites/default/files/products/datasheets/tsr2_datasheet.pdf'
LT3012 = 'https://www.analog.com/media/en/technical-documentation/data-sheets/lt3012.pdf'
LT3015 = 'https://www.analog.com/media/en/technical-documentation/data-sheets/3015fb.pdf'


def power_sheet():
    s=Sheet('carrier-power','12V input, digital and bipolar audio power',[
        'RMX A0.2 / POWER / DRAFT - regulated external 12V DC, center positive, current-limited 2A source; NO mains circuitry in chassis',
        'Two ISOLATED 24V modules create separate raw positive and negative rails; their output returns are bonded at GND.',
        'LDOs reduce raw +/-24V to approximately +/-20V. Never connect raw rails to U28. Use rated capacitors with guaranteed effective capacitance.',
        '+3V3 is supplied by Seed pin 38, not an external parallel regulator. Measure available rail current, temperature and startup before attaching controls.',
    ])
    s.header('J_PWR1','EXTERNAL 12V DC',['DC_IN_P','GND'])
    s.two('F1','2A time-delay fuse','DC_IN_P','DC_FUSED',package='rated fuse and holder; selection and fault coordination pending')
    s.two('SW34','POWER maintained','DC_FUSED','DC_SWITCHED',package='panel DC-rated switch; exact part pending')
    s.part('D3','B540C-13-F',[pin(1,'K','+12V_PROTECTED'),pin(2,'A','DC_SWITCHED')],
        'https://www.diodes.com/part/view/B540C','Diode_SMD:D_SMC','SMC','B540C-13-F',
        'Series 5A/40V reverse-polarity diode; current derating, surge coordination and thermal qualification pending')
    s.two('C500','22uF 50V electrolytic (+ to 12V)','+12V_PROTECTED','GND',package='input bulk; 22uF recommended by TSR for mechanical switch input')
    s.cap('C501','100nF X7R 50V','+12V_PROTECTED','GND')
    s.part('PS1','TSR 2-2450',[
        pin(1,'VIN','+12V_PROTECTED','power_in'),pin(2,'GND','GND','power_in'),pin(3,'VOUT','+5V','power_out')],
        TRACO_TSR,package='SIP3 14x7.5x10.1mm; verify manufacturer landing pattern',mpn='TSR 2-2450')
    for ref,plus,minus in [('PS2','+24VA_RAW','GND'),('PS3','GND','-24VA_RAW')]:
        s.part(ref,'TMR 6-1215',[
            pin(1,'VIN_N','GND','power_in'),pin(2,'VIN_P','+12V_PROTECTED','power_in'),
            pin(3,'REMOTE',None,'input'),pin(5,'NC',None),
            pin(6,'VOUT_P',plus,'passive' if plus=='GND' else 'power_out'),
            pin(7,'VOUT_N',minus,'passive' if minus=='GND' else 'power_out'),pin(8,'NC',None)],
            TRACO_TMR,package='SIP8 7 leads, 21.8x9.1x11.2mm; custom footprint review pending',mpn='TMR 6-1215',
            qualification='Isolated SINGLE 24V output, not dual 15V model; remote open = on. Output return bond is intentional; system audio ground is not isolated.')
    s.part('U29','LT3012EDE#PBF',[
        # Pads 2/3 are the SAME internal output. Model one ERC driver; pad 3
        # is its parallel current-carrying contact, not a second regulator.
        pin(1,'NC',None),pin(2,'OUT','+20VA','power_out'),pin(3,'OUT','+20VA'),
        pin(4,'ADJ','ADJ_POS','input'),pin(5,'GND','GND','power_in'),pin(6,'NC',None),pin(7,'NC',None),
        pin(8,'SHDN_N','+24VA_RAW','input'),pin(9,'NC',None),
        pin(10,'IN','+24VA_RAW','power_in'),pin(11,'IN','+24VA_RAW','power_in'),pin(12,'NC',None),
        pin(13,'EP_GND','GND','power_in')],LT3012,package='DFN12 4x3mm + GND EP13; reviewed footprint pending',mpn='LT3012EDE#PBF')
    s.part('U30','LT3015ET#PBF',[
        pin(1,'SHDN','-24VA_RAW','input'),pin(2,'GND','GND','power_in'),
        pin(3,'IN','-24VA_RAW','power_in'),pin(4,'ADJ','ADJ_NEG','input'),pin(5,'OUT','-20VA','power_out')],
        LT3015,package='5-lead TO-220; tab at INPUT (negative raw rail); electrically isolate mounting',mpn='LT3015ET#PBF')
    for ref,value,a,b in [('R500','151k','+20VA','ADJ_POS'),('R501','10k','ADJ_POS','GND'),
                           ('R502','154k','-20VA','ADJ_NEG'),('R503','10k','ADJ_NEG','GND')]:
        s.resistor(ref,value,a,b)
        s.data['components'][-1]['value']=value+' 0.1%'
    for ref,a,b in [('C502','+24VA_RAW','GND'),('C503','GND','-24VA_RAW'),
                    ('C504','+20VA','GND'),('C505','GND','-20VA')]:
        s.two(ref,'22uF 50V electrolytic (+ on pin 1)',a,b,
              package='>=16uF effective, ESR <=3ohm over operating temperature; exact series pending')
    s.cap('C506','100nF X7R 50V','+20VA','GND')
    s.cap('C507','100nF X7R 50V','GND','-20VA')
    s.header('J_PWR2','SEED POWER (39 VIN / 40 GND / 38 OUT)',['+5V','GND','+3V3'])
    s.header('J_PWR3','BYPASS J_BP1 POWER',['+3V3','+5V','GND'])
    s.header('J_PWR4','RELAY J_RY1 POWER',['+5V','+3V3','GND'])
    s.header('J_PWR5','LINE AUDIO POWER',['+20VA','GND','-20VA'])
    s.header('J_PWR6','RAIL MONITOR POWER',['+5V','+3V3','GND','+20VA','-20VA'])
    for ref,rail in [('#FLG03','+12V_PROTECTED'),('#FLG04','GND')]:
        s.part(ref,'EXTERNAL DC POWER DECLARATION', [pin(1,rail,rail,'power_out')],
            package='virtual',qualification='ERC declaration only: externally powered through J_PWR1/F1/SW34/D3; not a physical component')
        s.data['components'][-1]['virtual']=True
    return s.finish()


def rail_monitor_sheet():
    s=Sheet('analog-health','analog rail supervision and settling',[
        'RMX A0.2 / ANALOG RAIL HEALTH / DRAFT - comparator outputs wired open-collector, 300ms nominal recovery after both rails recover',
        'Negative rail is translated with a 2.5V reference; polarity is opposite the positive-rail comparator. Missing rails keep output low.',
        'Reference fault behavior, comparator offset/bias, all supply permutations and analog timing require bench tests. Not an overvoltage crowbar.',
    ])
    s.header('J_HL1','POWER',['+5V','+3V3','GND','+20VA','-20VA'])
    s.header('J_HL2','TO BYPASS J_BP3',['EXT_RAILS_OK','GND'])
    s.part('U31','LM393BDR',[
        pin(1,'OUT_A','ANALOG_RAW_OK','open_collector'),pin(2,'IN_A_N','REF_0409','input'),
        pin(3,'IN_A_P','SENSE_POS','input'),pin(4,'GND','GND','power_in'),
        pin(5,'IN_B_P','REF_0409','input'),pin(6,'IN_B_N','SENSE_NEG','input'),
        pin(7,'OUT_B','ANALOG_RAW_OK','open_collector'),pin(8,'VCC','+5V','power_in')],
        'https://www.ti.com/lit/gpn/lm393b','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm','SOIC-8','LM393BDR')
    s.part('D4','LM4040A25IDBZR',[
        pin(1,'CATHODE','REF_2V5'),pin(2,'ANODE','GND'),pin(3,'STAR_ANODE','GND')],
        'https://www.ti.com/lit/gpn/lm4040','Package_TO_SOT_SMD:SOT-23','SOT-23','LM4040A25IDBZR')
    for ref,value,a,b in [('R520','4.7k','+5V','REF_2V5'),('R521','51.1k','REF_2V5','REF_0409'),
        ('R522','10k','REF_0409','GND'),('R523','453k','+20VA','SENSE_POS'),('R524','10k','SENSE_POS','GND'),
        ('R525','100k','REF_2V5','SENSE_NEG'),('R526','931k','SENSE_NEG','-20VA'),
        ('R527','10k','+3V3','ANALOG_RAW_OK'),('R528','10k','+3V3','EXT_RAILS_OK'),('R529','100k','+3V3','CT_ANALOG')]:
        s.resistor(ref,value,a,b)
        if ref in ('R521','R522','R523','R524','R525','R526'):
            s.data['components'][-1]['value']=value+' 0.1%'
    s.part('U32','TPS3808G33DBVR',[
        pin(1,'RESET_N','EXT_RAILS_OK','open_collector'),pin(2,'GND','GND','power_in'),
        pin(3,'MR_N','ANALOG_RAW_OK','input'),pin(4,'CT','CT_ANALOG','input'),
        pin(5,'SENSE','+3V3','input'),pin(6,'VDD','+3V3','power_in')],
        TI_SUPERVISOR,'Package_TO_SOT_SMD:SOT-23-6','SOT-23-6','TPS3808G33DBVR')
    s.part('U36','TPS3808G25DBVR',[
        pin(1,'RESET_N','ANALOG_RAW_OK','open_collector'),pin(2,'GND','GND','power_in'),
        pin(3,'MR_N','+3V3','input'),pin(4,'CT',None,'input'),
        pin(5,'SENSE','REF_2V5','input'),pin(6,'VDD','+3V3','power_in')],
        TI_SUPERVISOR,'Package_TO_SOT_SMD:SOT-23-6','SOT-23-6','TPS3808G25DBVR',
        'Reference undervoltage also holds comparator wired output low; CT open nominal 20ms, followed by U32 nominal 300ms recovery')
    s.part('D5','BAT54WS-7-F',[
        pin(1,'K','SENSE_NEG'),pin(2,'A','GND')],
        'https://www.diodes.com/part/view/BAT54WS','Diode_SMD:D_SOD-323','SOD-323','BAT54WS-7-F',
        'Limits negative sense voltage on reference loss; comparator state outside valid input range is not trusted; U36 must hold permission low')
    s.cap('C520','100nF X7R 25V','+5V','GND')
    s.cap('C521','100nF X7R 25V','+3V3','GND')
    s.cap('C522','10nF C0G 50V','REF_2V5','GND')
    s.cap('C523','100nF X7R 25V','+3V3','GND')
    return s.finish()


def compute_sheet():
    s=Sheet('compute-storage-touch','Seed, native SD and touch module',[
        'RMX A0.2 / COMPUTE / DRAFT - U1 uses PHYSICAL header numbers. D numbers are carried in pin names, not pad numbers.',
        'Use the 64MB SDRAM Rev7 Seed. VIN = 5V. Pin 38 supplies 3.3V; never parallel another 3.3V regulator into this output.',
        'MPR121 breakout terminals are LABELS, not IC pin numbers. Vin = 3.3V. Check module revision, pull-ups and electrode/lens geometry.',
        'J_USB2 represents the Seed built-in micro-USB port. D29/D30 are a different USB peripheral and are deliberately left unused.',
    ])
    proto=json.loads((ROOT/'hardware/prototype.json').read_text())
    nets=dict(button_load='BUTTON_LOAD',button_clock='BUTTON_CLOCK',button_data='BUTTON_DATA',
        led_data='LED_DATA',led_clock='LED_CLOCK',led_latch='LED_LATCH',led_oe='LED_OE_N',
        i2c_scl='TOUCH_SCL',i2c_sda='TOUCH_SDA',adc_mux_a='MUX_A',adc_mux_b='MUX_B',
        mux_s0='MUX_S0',mux_s1='MUX_S1',mux_s2='MUX_S2',watchdog_heartbeat='HEARTBEAT',dsp_ready='DSP_READY')
    s.data['mcu_gpio']=proto['pins'].copy()
    # Manufacturer Table 2; pins 16..21 and 38..40 are not GPIO indices.
    physical={**{i:i+1 for i in range(15)},**{i:i+7 for i in range(15,31)}}
    by_gpio={proto['pins'][key]:(key,net) for key,net in nets.items()}
    sd={1:'SD_DAT3',2:'SD_DAT2',3:'SD_DAT1',4:'SD_DAT0',5:'SD_CMD',6:'SD_CLK'}
    module=[]
    for d,p in physical.items():
        if d in by_gpio:
            key,net=by_gpio[d]
            kind='input' if key in ('button_data','adc_mux_a','adc_mux_b') else 'bidirectional' if key.startswith('i2c') else 'output'
        elif d in sd:
            net,kind=sd[d],'output' if d==6 else 'bidirectional'
        else:
            net,kind=None,'bidirectional'
        module.append(pin(p,f'D{d}',net,kind))
    module += [pin(16,'AUDIO_IN_L','ADC_L','input'),pin(17,'AUDIO_IN_R','ADC_R','input'),
        pin(18,'AUDIO_OUT_L','DAC_L','output'),pin(19,'AUDIO_OUT_R','DAC_R','output'),
        pin(20,'AGND','GND','power_in'),pin(21,'3V3_ANALOG',None,'power_out'),
        pin(38,'3V3_DIGITAL','+3V3','power_out'),pin(39,'VIN','+5V','power_in'),pin(40,'DGND','GND','power_in')]
    module.sort(key=lambda p:int(p['number']))
    s.part('U1','DAISY SEED REV7 64MB SDRAM',module,SEED,
        package='40-pin module, 2 rows x20 @2.54mm, row spacing15.24mm; source footprint review pending',
        mpn='Daisy Seed 64MB with headers',qualification='Requires compatible QSPI bootloader, 64MB external SDRAM, physical bring-up and rail-current qualification.')
    sdnames=['SD_DAT2','SD_DAT3','SD_CMD','+3V3','SD_CLK','GND','SD_DAT0','SD_DAT1']
    s.part('J_SD1','MICROSD 3.3V NATIVE 4-BIT',[
        pin(i+1,n,n,'power_in' if i in (3,5) else 'passive') for i,n in enumerate(sdnames)
    ]+[pin('SH','SHIELD','GND')],package='microSD socket standard contacts 1..8; shell pad numbering/footprint pending',
        qualification='No 5V regulator or SPI-only breakout. Short SDMMC traces, local bulk and 47k pull-ups except CLK; exact socket must be selected.')
    for i,net in enumerate(['SD_DAT2','SD_DAT3','SD_CMD','SD_DAT0','SD_DAT1']):
        s.resistor(f'R{550+i}','47k','+3V3',net)
    s.cap('C550','100nF X7R 25V','+3V3','GND')
    s.cap('C551','10uF X7R 10V; >=4.7uF effective','+3V3','GND')
    s.part('U8','ADAFRUIT MPR121 BREAKOUT 1982',[
        pin('VIN','VIN','+3V3','power_in'),pin('GND','GND','GND','power_in'),
        pin('3VO','3VO',None,'power_out'),pin('SCL','SCL','TOUCH_SCL','input'),
        pin('SDA','SDA','TOUCH_SDA','bidirectional'),pin('ADDR','ADDR','GND','input'),pin('IRQ','IRQ',None,'open_collector')
    ]+[pin(str(i),f'E{i}',f'TOUCH_{i}' if i<8 else None) for i in range(12)],
        'https://learn.adafruit.com/adafruit-mpr121-12-key-capacitive-touch-sensor-breakout-tutorial/pinouts',
        package='module terminals by silkscreen label, not QFN pins; exact module revision mounting pending',mpn='Adafruit 1982',
        qualification='Prototype breakout; MPR121 lifecycle/supply replacement remains a production decision. Eight of twelve electrodes used at address 0x5A.')
    s.resistor('R555','4.7k','+3V3','TOUCH_SCL')
    s.resistor('R556','4.7k','+3V3','TOUCH_SDA')
    s.header('J_TOUCH1','ELECTRODES LEFT TO RIGHT',[f'TOUCH_{i}' for i in range(8)])
    s.header('J_CPU1','BUTTONS',['+3V3','GND','BUTTON_LOAD','BUTTON_CLOCK','BUTTON_DATA'])
    s.header('J_CPU2','ANALOG CONTROLS',['+3V3','GND','MUX_A','MUX_B','MUX_S0','MUX_S1','MUX_S2'])
    s.header('J_CPU3','LED CHAIN',['+3V3','GND','LED_DATA','LED_CLOCK','LED_LATCH','LED_OE_N'])
    s.header('J_CPU4','BYPASS HEARTBEAT',['HEARTBEAT','DSP_READY','GND'])
    s.header('J_CPU5','POWER',['+5V','GND','+3V3'])
    s.header('J_CPU6','LINE AUDIO',['ADC_L','ADC_R','DAC_L','DAC_R','GND'])
    s.part('J_USB1','PANEL USB-B EXTENSION',[
        pin(1,'VBUS','USB_VBUS'),pin(2,'D_N','USB_D_N'),pin(3,'D_P','USB_D_P'),pin(4,'GND','GND'),pin('SH','SHIELD','CHASSIS')],
        package='short shielded USB-B-female to micro-USB-male extension; no loose D+/D- flying wires')
    s.part('J_USB2','SEED BUILT-IN MICRO-USB PORT (CABLE END)',[
        pin(1,'VBUS','USB_VBUS'),pin(2,'D_N','USB_D_N'),pin(3,'D_P','USB_D_P'),pin(4,'ID',None),pin(5,'GND','GND'),pin('SH','SHIELD','CHASSIS')],
        SEED,package='cable end mates with Seed onboard port; not a separate MCU GPIO connection')
    s.two('R557','0 ohm CHASSIS BOND DRAFT','CHASSIS','GND',package='single controlled ground/chassis bond; EMC/ground-loop review pending')
    return s.finish()


def all_sheets():
    return [relay_sheet(),button_sheet(),analog_control_sheet(),led_sheet(),
            line_audio_sheet(),power_sheet(),rail_monitor_sheet(),compute_sheet()]


def assembly_artifacts(sheets):
    """Consolidate all sheets without pretending they form a routed PCB."""
    bypass=json.loads((DEST/'bypass.json').read_text())
    bypass['project']='bypass-permission'
    sheets=[bypass,*sheets]
    bom=io.StringIO()
    bw=csv.writer(bom,lineterminator='\n')
    bw.writerow(['Sheet','Reference','Value','MPN','Footprint','Package','Source','Qualification'])
    pins=io.StringIO()
    pw=csv.writer(pins,lineterminator='\n')
    pw.writerow(['Sheet','Reference','Pad','Pin','Net','Type','NoConnect'])
    missing_mpn=[]
    missing_footprint=[]
    physical=0
    references=set()
    for data in sheets:
        for p in data['components']:
            assert p['ref'] not in references, 'Duplicate carrier reference: '+p['ref']
            references.add(p['ref'])
            if not p.get('virtual'):
                physical+=1
                mpn=p.get('mpn',p['value'] if p['ref'].startswith('U') else '')
                bw.writerow([data['project'],p['ref'],p['value'],mpn,p.get('footprint',''),p['package'],p['source'],p['qualification']])
                if not mpn: missing_mpn.append(p['ref'])
                if not p.get('footprint'): missing_footprint.append(p['ref'])
            for v in p['pins']:
                pw.writerow([data['project'],p['ref'],v['number'],v['name'],v.get('net',''),v['type'],bool(v.get('no_connect'))])
    inventory=dict(revision='A0.2-draft',status='Engineering draft; not fabrication-ready',
        schematic_count=len(sheets),physical_component_count=physical,
        missing_explicit_mpn=missing_mpn,missing_footprint=missing_footprint,
        native_kicad_evidence='native-check.json; run tools/check_carrier.py --check to reject stale evidence',
        pcb_layout_complete=False,
        mechanical_assembly_verified=False,hardware_flashed=False,
        analog_performance_measured=False,reference_sound_matched=False)
    return {'carrier-bom.csv':bom.getvalue(),'carrier-connections.csv':pins.getvalue(),
            'carrier-inventory.json':json.dumps(inventory,indent=2)+'\n'}


def project_artifacts(sheets):
    """Native multi-sheet project: only harness nets cross sheet boundaries.

    Standalone permission-sheet power flags are intentionally omitted here:
    the Seed and 5V regulator are the real sources in the assembled system.
    """
    bypass=copy.deepcopy(json.loads((DEST/'bypass.json').read_text()))
    bypass['project']='bypass-permission'
    bypass['components']=[p for p in bypass['components'] if not p.get('virtual')]
    sheets=[bypass,*sheets]
    project='carrier'
    root=uid('carrier:root')
    globals_={v['net'] for d in sheets for p in d['components'] if p['ref'].startswith('J')
              for v in p['pins'] if v.get('net')}
    out=['(kicad_sch (version 20231120) (generator rmx_generate_carrier)',
         f'(uuid {root}) (paper "A3")',
         '(title_block (title "RMX - integrated carrier") (date "2026-10-22") (rev "A0.2-draft") (comment 1 "ENGINEERING DRAFT - NOT FOR FABRICATION"))',
         '(lib_symbols)',
         f'(text "Full carrier connectivity / harness nets are global / NC dry relay paths require physical testing" (at 20 18 0) {effects(1.6,justify="left")} (uuid {uid("carrier:note")}))']
    generated={}
    for index,data in enumerate(sheets):
        name=data['project']
        sheet_id=uid('carrier:sheet:'+name)
        x,y=20+(index%3)*125,40+(index//3)*75
        out += [f'(sheet (at {x} {y}) (size 105 45) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {sheet_id})',
                f'(property "Sheetname" {quote(name)} (at {x} {y-1.27} 0) {effects(justify="left bottom")})',
                f'(property "Sheetfile" "carrier/{name}.kicad_sch" (at {x} {y+46.27} 0) {effects(justify="left top")})',
                f'(instances (project "{project}" (path "/{root}" (page "{index+2}"))))',')']
        generated['carrier/'+name+'.kicad_sch']=schematic(data,
            dict(project=project,path=f'/{root}/{sheet_id}',global_nets=globals_))
    out+=['(sheet_instances (path "/" (page "1")))',')']
    generated['carrier.kicad_sch']='\n'.join(out)+'\n'
    generated['carrier.kicad_pro']=json.dumps({'meta':{'filename':'carrier.kicad_pro','version':1}},indent=2)+'\n'
    # Include the two standalone bypass flags too, so its independent drawing
    # resolves against the same library without changing the integrated design.
    original_bypass=json.loads((DEST/'bypass.json').read_text())
    all_parts=original_bypass['components']+[p for d in sheets[1:] for p in d['components']]
    generated['RMX.kicad_sym']='\n'.join([
        '(kicad_symbol_lib (version 20231120) (generator rmx_generate_carrier)',
        *[library_symbol(p,external=True) for p in all_parts],')'])+'\n'
    generated['sym-lib-table']='(sym_lib_table (version 7)\n (lib (name "RMX") (type "KiCad") (uri "${KIPRJMOD}/RMX.kicad_sym") (options "") (descr "Generated RMX circuit pin blocks")))\n'
    libraries=sorted({p['footprint'].split(':')[0] for p in all_parts if p.get('footprint')})
    generated['fp-lib-table']='(fp_lib_table (version 7)\n'+'\n'.join(
        f' (lib (name "{n}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{n}.pretty") (options "") (descr "KiCad bundled library; footprint selection remains subject to review"))'
        for n in libraries)+')\n'
    return generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    sheets = all_sheets()
    generated = {}
    for data in sheets:
        generated[data['project']+'.json'] = json.dumps(data,indent=2)+'\n'
        generated.update(artifacts(data))
    generated.update(assembly_artifacts(sheets))
    generated.update(project_artifacts(sheets))
    for name, content in generated.items():
        path = DEST / name
        if args.check:
            assert path.exists() and path.read_text()==content, f'Stale generated carrier file: {name}'
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
    summary_bom=ROOT/'hardware/bom.csv'
    if args.check:
        assert summary_bom.read_text()==generated['carrier-bom.csv'], 'Stale hardware/bom.csv'
    else:
        summary_bom.write_text(generated['carrier-bom.csv'])
    print(f'PASS: {len(sheets)} carrier sheets, {sum(len(d["components"]) for d in sheets)} components; CAD/BOM reproduction only, not native ERC')


if __name__=='__main__':
    main()
