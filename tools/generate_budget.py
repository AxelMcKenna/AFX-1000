#!/usr/bin/env python3
"""Generate the B1 5V consumer-level hardware variant; preserve the A0.2 design.

Budget figures are procurement ceilings, never invented supplier quotes. Native
ERC, layout checks and physical qualification are independent evidence gates.
"""
import argparse
import copy
import csv
import io
import json
from pathlib import Path
from generate_bypass import artifacts, schematic, library_symbol, uid, effects, quote
from generate_carrier import (Sheet, pin, button_sheet, analog_control_sheet,
                              led_sheet, compute_sheet, TI_SUPERVISOR, OMRON,
                              MOSFET, TVS)

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'hardware/budget'
DOC='hardware/budget/README.md'
SO14='Package_SO:SOIC-14_3.9x8.7mm_P1.27mm'


def supervisor(s,ref,part,reset,mr,sense,supply='+3V3',ct=None):
    s.part(ref,part,[pin(1,'RESET_N',reset,'open_collector'),pin(2,'GND','GND','power_in'),
        pin(3,'MR_N',mr,'input'),pin(4,'CT',ct,'input'),pin(5,'SENSE',sense,'input'),
        pin(6,'VDD',supply,'power_in')],TI_SUPERVISOR,'Package_TO_SOT_SMD:SOT-23-6','SOT-23-6',part)


def audio_power():
    s=Sheet('audio-power','B1 single-supply audio and power',[
        'RMX B1 / 5V CONSUMER-LEVEL AUDIO / ENGINEERING DRAFT - not a +24dBu interface',
        'Regulated 5V/1A external source; never 12V. RCA only, shared unbalanced ground. Nominal -10dBV, recommended peak programme level <=1Vrms.',
        'TLV9064 input buffers and output gain share a filtered midrail. Trim unity with the actual Rev7 codec and >=10k load.',
        'Current limiting / rail clamps do not constitute certified ESD or overload survival. Qualify powered/unpowered injection and power sequencing.',
        'Service USB cable MUST block VBUS; otherwise the Seed USB supply bypasses SW34 and the unit cannot be fully switched off.',
    ])
    s.header('J_PWR1','REGULATED 5V ONLY',['USB_5V_IN','GND'])
    s.two('F1','750mA resettable fuse','USB_5V_IN','FUSED_5V',
          'Fuse:Fuse_1206_3216Metric','1206',mpn='1206L075YR',source='https://www.littelfuse.com/products/polyswitch-resettable-pptcs/surface-mount/1206l')
    s.header('J_SW1','SW34 PANEL POWER',['FUSED_5V','+5V'])
    s.two('SW34','LATCHING POWER (5V DC)','FUSED_5V','+5V',package='offboard panel switch; DC rated >=1A; fit drawing required')
    s.two('C500','100uF 10V (+ to 5V)','+5V','GND',
          'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm','radial 6.3mm',mpn='EEU-FR1A101',source='https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/series/fr')
    s.cap('C501','100nF X7R 25V','+5V','GND')
    # VREF is a quiet AC reference, not a second power source or exposed jack.
    s.resistor('R500','10k','+5V','VREF_2V5')
    s.resistor('R501','10k','VREF_2V5','GND')
    for p in s.data['components'][-2:]:
        p['value']='10k 0.1%';p['mpn']='RT0603BRD0710KL'
    s.two('C502','100uF 10V (+ to VREF)','VREF_2V5','GND',
          'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm','radial 6.3mm',mpn='EEU-FR1A101',source='https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/series/fr')
    s.cap('C503','100nF X7R 25V','VREF_2V5','GND')
    s.part('U28','TLV9064IDR',[
        pin(1,'OUT_A','BUF_L','output'),pin(2,'IN_A_N','BUF_L','input'),pin(3,'IN_A_P','PAD_L','input'),
        pin(4,'VCC','+5V','power_in'),pin(5,'IN_B_P','PAD_R','input'),pin(6,'IN_B_N','BUF_R','input'),
        pin(7,'OUT_B','BUF_R','output'),pin(8,'OUT_C','LINE_L_RAW','output'),pin(9,'IN_C_N','FB_L','input'),
        pin(10,'IN_C_P','AMP_L_IN','input'),pin(11,'GND','GND','power_in'),
        pin(12,'IN_D_P','AMP_R_IN','input'),pin(13,'IN_D_N','FB_R','input'),pin(14,'OUT_D','LINE_R_RAW','output')],
        'https://www.ti.com/lit/gpn/tlv9064',SO14,'SOIC-14','TLV9064IDR',
        '1.8..5.5V quad RRIO. Validate noise, capacitive load, bias/offset and overload recovery on the actual board.')
    s.cap('C400','100nF X7R 25V','+5V','GND')
    for i,ch in enumerate(('L','R')):
        b=410+i*20
        # Caps have positive terminals toward the 2.5V-biased amplifier nodes.
        s.header(f'J_IN{i+1}',f'RCA INPUT {ch}',['IN_'+ch,'GND'])
        s.header(f'J_OUT{i+1}',f'RCA OUTPUT {ch}',['OUT_'+ch,'GND'])
        s.two(f'C{b}','10uF 25V (+ to biased node)',f'INPUT_AC_{ch}',f'IN_{ch}',
              'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm','radial 5mm',mpn='ECA-1EM100',source='https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/series/m')
        s.resistor(f'R{b}','22.1k',f'INPUT_AC_{ch}',f'PAD_{ch}')
        s.resistor(f'R{b+1}','100k',f'PAD_{ch}','VREF_2V5')
        for off,k,a in [(0,'+5V',f'PAD_{ch}'),(1,f'PAD_{ch}','GND')]:
            s.part(f'D{410+i*2+off}','BAT54WS-7-F',[pin(1,'K',k),pin(2,'A',a)],
                'https://www.diodes.com/datasheet/download/BAT54WS.pdf','Diode_SMD:D_SOD-323','SOD-323','BAT54WS-7-F')
        s.cap(f'C{b+1}','100pF C0G 50V',f'PAD_{ch}','GND')
        s.two(f'C{b+2}','10uF 25V (+ to buffer)',f'BUF_{ch}',f'ADC_AC_{ch}',
              'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm','radial 5mm',mpn='ECA-1EM100')
        s.resistor(f'R{b+2}','100',f'ADC_AC_{ch}',f'ADC_{ch}')
        s.resistor(f'R{b+3}','100k',f'ADC_{ch}','GND')
        s.two(f'C{b+3}','10uF 25V (+ to amp)',f'AMP_{ch}_IN',f'DAC_{ch}',
              'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm','radial 5mm',mpn='ECA-1EM100')
        s.resistor(f'R{b+4}','100k',f'AMP_{ch}_IN','VREF_2V5')
        s.resistor(f'R{b+5}','10k',f'FB_{ch}','VREF_2V5')
        s.resistor(f'R{b+6}','5.1k',f'LINE_{ch}_RAW',f'TRIM_{ch}')
        s.part(f'RV{20+i}','1k unity trim',[
            pin(1,'END_A',f'TRIM_{ch}'),pin(2,'WIPER',f'FB_{ch}'),pin(3,'END_B',f'FB_{ch}')],
            'https://www.bourns.com/docs/product-datasheets/3296.pdf',
            'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical','3296W','3296W-1-102LF',
            'Wiper strapped to end B; minimum feedback remains connected. Calibrate both channels physically.')
        s.resistor(f'R{b+7}','100',f'LINE_{ch}_RAW',f'LINE_{ch}_ISOLATED')
        s.two(f'C{b+4}','10uF 25V (+ to output)',f'LINE_{ch}_ISOLATED',f'WET_{ch}',
              'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm','radial 5mm',mpn='ECA-1EM100')
        s.resistor(f'R{b+8}','100k',f'WET_{ch}','GND')
    s.header('J_AUD1','SEED CODEC',['ADC_L','ADC_R','DAC_L','DAC_R','GND'])
    s.header('J_AUD3','TO RELAY INPUTS',['IN_L','IN_R','GND'])
    s.header('J_AUD4','TO RELAY WET',['WET_L','WET_R','GND'])
    s.header('J_AUD5','FROM RELAY OUTPUTS',['OUT_L','OUT_R','GND'])
    s.header('J_PWR2','SEED POWER: 39 / 40 / 38',['+5V','GND','+3V3'])
    s.header('J_PWR3','BYPASS POWER',['+3V3','+5V','GND'])
    s.header('J_PWR4','RELAY POWER',['+5V','+3V3','GND'])
    s.header('J_PWR6','REFERENCE HEALTH',['+5V','+3V3','GND','VREF_2V5'])
    s.header('J_BYP1','MANUAL BYPASS SWITCH',['MANUAL_N','GND'])
    for ref,rail in [('#FLG03','+5V'),('#FLG04','GND')]:
        s.part(ref,'EXTERNAL SWITCHED 5V SOURCE',[pin(1,rail,rail,'power_out')],package='virtual',
               qualification='ERC assertion after fuse/switch; no regulator or voltage protection implied')
        s.data['components'][-1]['virtual']=True
    return s.finish()


def relay():
    s=Sheet('relay-audio','B1 single stereo dry relay',[
        'RMX B1 / SINGLE STEREO RELAY / NC = DRY WITHOUT POWER',
        'One pole switches each unbalanced channel. Ground is common; this interface is not balanced.',
        'Independent 5V-powered supervisor clamps the gate during 3.3V loss. TVS is drain-to-GND, not a diode across the coil.',
        'No separate analog input-mute relay. Physical startup/fault pop and complete fault-to-dry timing remain unqualified.',
    ])
    s.header('J_RY1','REGULATED POWER',['+5V','+3V3','GND'])
    s.header('J_RY2','BYPASS PERMISSION',['RELAY_PERMISSION','GND'])
    s.header('J_RY3','DRY INPUTS',['IN_L','IN_R','GND'])
    s.header('J_RY4','PROCESSED INPUTS',['WET_L','WET_R','GND'])
    s.header('J_RY5','OUTPUTS',['OUT_L','OUT_R','GND'])
    s.part('K1','G5V-2 DC5',[
        pin(1,'COIL_A','+5V'),pin(16,'COIL_B','COIL_LOW'),
        pin(4,'COM_L','OUT_L'),pin(6,'NC_L','IN_L'),pin(8,'NO_L','WET_L'),
        pin(13,'COM_R','OUT_R'),pin(11,'NC_R','IN_R'),pin(9,'NO_R','WET_R')],
        OMRON,'Relay_THT:Relay_DPDT_Omron_G5V-2','DPDT standard 500mW','G5V-2 DC5')
    s.part('Q1','DMN3023L-7',[pin(1,'G','RELAY_GATE','input'),pin(2,'S','GND'),pin(3,'D','COIL_LOW')],
        MOSFET,'Package_TO_SOT_SMD:SOT-23','SOT-23','DMN3023L-7')
    s.part('D1','SMAJ12A (Littelfuse)',[pin(1,'K','COIL_LOW'),pin(2,'A','GND')],
        TVS,'Diode_SMD:D_SMA','SMA','SMAJ12A')
    s.resistor('R30','10k','CONTACTS_DRIVE','RELAY_GATE')
    s.resistor('R31','100k','RELAY_GATE','GND')
    supervisor(s,'U27','TPS3808G33DBVR','RELAY_GATE','+5V','+3V3','+5V')
    s.part('U35','74HCT14D,653',[
        pin(1,'1A','RELAY_PERMISSION','input'),pin(2,'1Y','PERMISSION_N','output'),
        pin(3,'2A','PERMISSION_N','input'),pin(4,'2Y','CONTACTS_DRIVE','output'),
        pin(5,'3A','GND','input'),pin(6,'3Y',None,'output'),pin(7,'GND','GND','power_in'),
        pin(8,'4Y',None,'output'),pin(9,'4A','GND','input'),pin(10,'5Y',None,'output'),
        pin(11,'5A','GND','input'),pin(12,'6Y',None,'output'),pin(13,'6A','GND','input'),
        pin(14,'VCC','+5V','power_in')],
        'https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf',SO14,'SOIC-14','74HCT14D,653')
    s.cap('C30','100nF X7R 25V','+5V','GND')
    s.cap('C33','100nF X7R 25V','+5V','GND')
    return s.finish()


def health():
    s=Sheet('reference-health','B1 midrail startup qualification',[
        'RMX B1 / MIDRAIL HEALTH / no high-voltage analog rails',
        'U32 monitors the filtered midrail. Recovery starts only after VREF exceeds the G25 threshold, then nominal 300ms CT delay.',
        'The unbuffered midrail RC settles slowly. Verify thresholds, supply ripple, temperature and pop/click behavior physically.',
    ])
    s.header('J_HL1','POWER AND MIDRAIL',['+5V','+3V3','GND','VREF_2V5'])
    s.header('J_HL2','BYPASS ANALOG HEALTH',['EXT_RAILS_OK','GND'])
    supervisor(s,'U32','TPS3808G25DBVR','EXT_RAILS_OK','+3V3','VREF_2V5',ct='CT_ANALOG')
    s.resistor('R528','10k','+3V3','EXT_RAILS_OK')
    s.resistor('R529','100k','+3V3','CT_ANALOG')
    s.cap('C521','100nF X7R 25V','+3V3','GND')
    return s.finish()


def all_sheets():
    bypass=copy.deepcopy(json.loads((ROOT/'hardware/electrical/bypass.json').read_text()))
    bypass['project']='bypass-permission'
    bypass['components']=[p for p in bypass['components'] if not p.get('virtual')]
    next(p for p in bypass['components'] if p['ref']=='U21')['footprint']='Package_TO_SOT_SMD:Texas_DDF0008A_SOT-8_1.6x2.9mm_P0.65mm'
    bypass['sheet_notes'][2]='B1 external 5V/3.3V, midrail health and one stereo dry relay; original watchdog/stage logic retained.'
    leds=led_sheet()
    for p in leds['components']:
        if p['ref'].startswith('R2'):p['value']='3.3k 1%'
    leds['sheet_notes'][0]='RMX B1 / LOW-CURRENT LED CHAIN / 3.3k per segment, 3.3V logic; test brightness and Seed rail budget'
    compute=compute_sheet()
    for p in compute['components']:
        if p['ref']=='J_SD1':
            p['value']='ADAFRUIT 4682 SDIO BREAKOUT (3V ONLY)'
            p['mpn']='Adafruit 4682'
            p['source']='https://learn.adafruit.com/adafruit-microsd-spi-sdio/pinouts'
            p['pins']=[pin('3V','3V','+3V3','power_in'),pin('GND','GND','GND','power_in'),
                pin('CLK','CLK','SD_CLK'),pin('CMD','CMD/SI','SD_CMD'),pin('D0','D0/SO','SD_DAT0'),
                pin('D1','D1','SD_DAT1'),pin('DAT2','DAT2','SD_DAT2'),pin('D3','D3/CS','SD_DAT3'),
                pin('DET','DET',None,'output')]
            p['package']='module terminals by silkscreen, not bare socket contact numbers'
            p['qualification']='Native SDIO module; use very short 3.3V harness, account for built-in pull-ups in parallel with external 47k. DET unused; no live insertion firmware.'
        if p['ref'] in ('J_USB1','J_USB2'):
            for v in p['pins']:
                if v['name']=='VBUS':v.pop('net',None);v['no_connect']=True
            p['qualification']='Service USB extension with VBUS disconnected; continuity-check before connection. Data/ground/shield only; switched external 5V powers Seed.'
    compute['sheet_notes'][3]='Service USB VBUS must be blocked at both cable ends. Direct USB power bypasses the power switch. D29/D30 remain unused.'
    sheets=[audio_power(),relay(),health(),bypass,button_sheet(),analog_control_sheet(),leds,compute]
    for d in sheets:
        d['revision']='B1-5V-draft'
        for p in d['components']:
            if p['source']=='hardware/electrical/carrier.md':p['source']=DOC
            if p['ref'].startswith('RV') and int(p['ref'][2:])<=11:
                p['mpn']='CR0208 (supplier code)'
                p['source']='https://surplustronics.co.nz/categories/198-potentiometers-trimpots'
                p['package']='24mm panel pot, split shaft; rear body/shaft measurement and harness terminal check required'
            if p['ref'].startswith('R') and not p['ref'].startswith('RV') and p.get('footprint','').startswith('Resistor_SMD:') and not p.get('mpn'):
                value=p['value'].split()[0]
                if value!='0':
                    if value.endswith('k'):
                        a=value[:-1].split('.');code=a[0]+'K'+(a[1] if len(a)>1 else '')
                    else:code=value+'R'
                    p['mpn']='RC0603FR-07'+code+'L'
                else:p['mpn']='RC0603JR-070RL'
    return sheets


def integrated(sheets):
    root=uid('budget5v:root');generated={}
    globals_={v['net'] for d in sheets for p in d['components'] if p['ref'].startswith('J') for v in p['pins'] if v.get('net')}
    out=['(kicad_sch (version 20231120) (generator rmx_generate_budget)',
         f'(uuid {root}) (paper "A3") (lib_symbols)',
         '(title_block (title "RMX B1 - 5V budget prototype") (date "2026-10-23") (rev "B1") (comment 1 "ENGINEERING DRAFT - consumer levels; physical qualification pending"))']
    for i,d in enumerate(sheets):
        name=d['project'];sid=uid('budget5v:sheet:'+name);x=20+(i%3)*125;y=35+(i//3)*75
        out += [f'(sheet (at {x} {y}) (size 105 45) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {sid})',
                f'(property "Sheetname" {quote(name)} (at {x} {y-1.27} 0) {effects(justify="left bottom")})',
                f'(property "Sheetfile" "sheets/{name}.kicad_sch" (at {x} {y+46.27} 0) {effects(justify="left top")})',
                f'(instances (project "budget5v" (path "/{root}" (page "{i+2}"))))',')']
        generated['sheets/'+name+'.kicad_sch']=schematic(d,dict(project='budget5v',path=f'/{root}/{sid}',global_nets=globals_)).replace('(date "2026-10-22")','(date "2026-10-23")')
    out+=['(sheet_instances (path "/" (page "1")))',')']
    generated['budget5v.kicad_sch']='\n'.join(out)+'\n'
    generated['budget5v.kicad_pro']='{"meta":{"filename":"budget5v.kicad_pro","version":1}}\n'
    parts=[p for d in sheets for p in d['components']]
    assert len({p['ref'] for p in parts})==len(parts),'Duplicate B1 reference'
    generated['RMX.kicad_sym']='\n'.join(['(kicad_symbol_lib (version 20231120) (generator rmx_generate_budget)',*[library_symbol(p,True) for p in parts],')'])+'\n'
    generated['sym-lib-table']='(sym_lib_table (version 7) (lib (name "RMX") (type "KiCad") (uri "${KIPRJMOD}/RMX.kicad_sym") (options "") (descr "B1 circuit symbols")))\n'
    libs=sorted({p['footprint'].split(':')[0] for p in parts if p.get('footprint')})
    generated['fp-lib-table']='(fp_lib_table (version 7)\n'+'\n'.join(f'(lib (name "{n}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{n}.pretty") (options "") (descr "KiCad 10"))' for n in libs)+')\n'
    return generated


def generate():
    sheets=all_sheets();out=integrated(sheets)
    bom=io.StringIO();bw=csv.writer(bom,lineterminator='\n')
    bw.writerow(['Sheet','Reference','Value','MPN','Footprint','Package','Source','Qualification'])
    connections=io.StringIO();pw=csv.writer(connections,lineterminator='\n');pw.writerow(['Sheet','Reference','Pad','Pin','Net','Type','NoConnect'])
    physical=[]
    for d in sheets:
        out[d['project']+'.json']=json.dumps(d,indent=2)+'\n'
        for name,content in artifacts(d).items():
            if name.endswith('.svg'):out[name]=content
        for p in d['components']:
            if not p.get('virtual'):
                physical.append(p)
                bw.writerow([d['project'],p['ref'],p['value'],p.get('mpn',''),p.get('footprint',''),p['package'],p['source'],p['qualification']])
            for v in p['pins']:pw.writerow([d['project'],p['ref'],v['number'],v['name'],v.get('net',''),v['type'],bool(v.get('no_connect'))])
    out['bom.csv']=bom.getvalue();out['connections.csv']=connections.getvalue()
    out['inventory.json']=json.dumps(dict(revision='B1-5V-draft',physical_components=len(physical),
        missing_mpn=[p['ref'] for p in physical if not p.get('mpn')],
        missing_footprint=[p['ref'] for p in physical if not p.get('footprint')],
        native_check='native-check.json; validate current hashes with tools/check_budget.py --check',
        fabrication_released=False,physical_tests_performed=False,budget_is_supplier_quote=False),indent=2)+'\n'
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for name,content in generate().items():
        path=DEST/name
        if args.check:assert path.exists() and path.read_text()==content,'Stale budget artifact: '+name
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    print('PASS: B1 5V budget circuit files reproduce; not a native/physical check')


if __name__=='__main__':main()
