"""Compact NF03C complete two-rail proposal; E28 native integration not adopted.

Retains the reference's exact host latch equations, packs equivalent gates,
shares actual E28 source monitors and implements the formerly external power
controllers. Package land/thermal/AC/partial-power proof remain separate holds.
"""
import copy
from pathlib import Path
from .sources.reference.circuit import components as reference_components

ROOT=Path(__file__).resolve().parent
TI='https://www.ti.com/lit/ds/symlink/'
ADI='https://www.analog.com/media/en/technical-documentation/data-sheets/'
BYPASS='100nF 25V C0G C1206C104J3GACTU'


def components():
    parts=[]
    gates={'AND':[], 'OR':[], 'INV':[]}
    def add(prefix,part,fp,pins,source='',note=''):
        ref=prefix+str(1+sum(c['ref'].startswith(prefix) for c in parts))
        ps=[dict(number=str(n),name=name,net=net,kind=kind,side='R' if kind in ('output','open_collector','power_out') else 'L') for n,name,net,kind in pins]
        parts.append(dict(ref=ref,part=part,footprint=fp,pins=ps,source=source,note=note))
        return ref
    def passive(prefix,part,a,b,fp,source='',note=''):
        return add(prefix,part,fp,[(1,'1',a,'passive'),(2,'2',b,'passive')],source,note)
    def r(value,a,b,fp='Resistor_SMD:R_0805_2012Metric',note=''):
        return passive('R',value,a,b,fp,note=note)
    def c(value,a,b,fp='Capacitor_SMD:C_1206_3216Metric',note=''):
        if value==BYPASS and b=='AGND':
            value='100nF 50V X7R10% C0603C104K5RACTU - bypass effective/PDN HOLD'
            fp='Capacitor_SMD:C_0603_1608Metric'
        return passive('C',value,a,b,fp,note=note)
    def ic(part,fp,pmap,source,power=(),out=(),oc=(),nc=()):
        return add('U',part,fp,[(n,name,net,'power_in' if n in power else 'output' if n in out else 'open_collector' if n in oc else 'no_connect' if n in nc else 'input') for n,(name,net) in pmap.items()],source)
    def gate(func,a,b,y): gates[func].append((a,b,y))
    def bypins(c):return {p['number']:p['net'] for p in c['pins']}
    # Exact copied functional host equations, excluding redundant empty inverter.
    for old in reference_components():
        part=old['part'];pins=bypins(old);nets=set(pins.values())
        if part.startswith('SN74AUP1G') and not part.startswith('SN74AUP1G74'):
            func='AND' if '1G08' in part else 'OR' if '1G32' in part else 'INV'
            if pins.get('4')!='NOT_GLOBAL_VALID' and not any(str(pins.get('4')).endswith('_'+v) for v in ('NOT_ARM','RESET_ALLOWED','NOT_RESET_ALLOWED','FAULT_CLR_N')):
                gate(func,pins['2'] if func=='INV' else pins['1'],None if func=='INV' else pins['2'],pins['4'])
        elif part.startswith(('SN74AUP1G74','TPS3431','SN74LVC1G06','TLP4590')) and not (part.startswith('SN74AUP1G74') and str(pins.get('5')).endswith('_FAULT')):
            copied=copy.deepcopy(old)
            copied['ref']='U'+str(1+sum(c['ref'].startswith('U') for c in parts))
            parts.append(copied)
        elif old['ref'].startswith('R') and any(n and ('CLAMP' in n or n.endswith(('_WDO','_WD_ARMED'))) for n in nets):
            copied=copy.deepcopy(old);copied['ref']='R'+str(1+sum(c['ref'].startswith('R') for c in parts));parts.append(copied)
        elif old['ref'].startswith('C') and any(n and n.endswith('_CWD') for n in nets):
            copied=copy.deepcopy(old);copied['ref']='C'+str(1+sum(c['ref'].startswith('C') for c in parts));parts.append(copied)
    # GLOBAL_MASTER is actual existing ALL_RAILS_ALLOW, not a firmware/PG proxy.
    # It includes existing E28 reference validity/all-source OV/user/AUX checks.
    controls=['AUX2V6','AGND','DIG5_FORCE','GUARDED_12V_FORCE','AUX_VALID','GLOBAL_MASTER','RESET_REQUEST',
              'PROTECT_REF','N19_OV_OK','N12_OV_OK','N19_OV_SENSE','N12_OV_SENSE','E28_NATIVE_FAULT_REQUEST','E28_COMBINED_FAULT_REQUEST','E28_NOT_FAULT','N19_BIAS_VALID','N12_BIAS_VALID']
    for rail in ('N19','N12'):
        controls += [rail+'_'+x for x in ('ARM','START','FAULT_REQUEST','COMPLETE','CLAMPS_RELEASE','PROTECTED')]
    add('J','NEW NF03C CONTROL/KELVIN INTERFACE - physical connector unselected','Connector_PinHeader_2.54mm:PinHeader_2x15_P2.54mm_Vertical',[(i+1,n,n,'passive') for i,n in enumerate(controls)]+[(30,'RESERVED_NC',None,'no_connect')],note='Pin contract only. Real force/control connectors, guard faults, return and harness not implemented; no TEST J3 use.')
    for n in ('GLOBAL_MASTER','AUX_VALID','RESET_REQUEST','N19_ARM','N19_START','N12_ARM','N12_START','E28_NOT_FAULT'):
        r('47k 3% TOTAL RECEIVING',n,'AGND')
    # Reuse SOURCE inverse/OV and REF from E28. New absolute protected sensing.
    ic('OPA2333AID','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
       {1:('OUTA','N19_OUT_INV'),2:('INA-','N19_OUT_SUM'),3:('INA+','AGND'),4:('V-','AGND'),5:('INB+','AGND'),6:('INB-','N12_OUT_SUM'),7:('OUTB','N12_OUT_INV'),8:('V+','AUX2V6')},TI+'opa333.pdf',power=(4,8),out=(1,7))
    refs={}
    for rail,ri,uvtop,ovtop in [('N19',160000,[8660,35.7],[2000,40.2]),('N12',102000,[10700,169],[2000])]:
        r(f'{ri}ohm COMPLETE0.1% RECEIVING',rail+'_PROTECTED',rail+'_OUT_SUM')
        r('10k COMPLETE0.1% RECEIVING',rail+'_OUT_INV',rail+'_OUT_SUM')
        for kind,values in [('UV',uvtop),('OV',ovtop)]:
            node='PROTECT_REF'
            for i,value in enumerate(values):
                end=rail+'_OUT_'+kind+'_REF' if i==len(values)-1 else rail+'_OUT_'+kind+'_RMID'
                r(f'{value}ohm COMPLETE0.1% RECEIVING',node,end);node=end
            r('100k COMPLETE0.1% RECEIVING',node,'AGND')
            refs[rail,kind]=node
            r('10k COMPLETE3% RECEIVING',rail+'_OUT_INV',rail+'_OUT_'+kind+'_SENSE')
        # SOURCE-UV only, at existing source filter; SOURCE-OV is retained E28.
        sourcevalues=[6040,75] if rail=='N19' else [8660,35.7]
        node='PROTECT_REF'
        for i,value in enumerate(sourcevalues):
            end=rail+'_SOURCE_UV_REF' if i==len(sourcevalues)-1 else rail+'_SOURCE_UV_RMID'
            r(f'{value}ohm COMPLETE0.1% RECEIVING',node,end);node=end
        r('100k COMPLETE0.1% RECEIVING',node,'AGND')
        r('10k COMPLETE3% RECEIVING',rail+'_OV_SENSE',rail+'_SOURCE_UV_SENSE')
        for net in (rail+'_SOURCE_UV_GOOD',rail+'_OUTPUT_UV_GOOD',rail+'_OUTPUT_OV_GOOD'):
            r('10k COMPLETE3% RECEIVING','AUX2V6',net)
        gate('AND',rail+'_SOURCE_UV_GOOD',rail+'_OV_OK',rail+'_SOURCE_SAFE0')
        gate('AND',rail+'_SOURCE_SAFE0',rail+'_OUTPUT_OV_GOOD',rail+'_SOURCE_SAFE1')
        gate('AND',rail+'_SOURCE_SAFE1',rail+'_BIAS_VALID',rail+'_SAFE')
        gate('AND',rail+'_OUTPUT_UV_GOOD',rail+'_OUTPUT_OV_GOOD',rail+'_READY')
    ic('TLV1822DR','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
       {1:('OUT1','N19_SOURCE_UV_GOOD'),2:('IN1-','N19_SOURCE_UV_REF'),3:('IN1+','N19_SOURCE_UV_SENSE'),4:('V-','AGND'),5:('IN2+','N12_SOURCE_UV_SENSE'),6:('IN2-','N12_SOURCE_UV_REF'),7:('OUT2','N12_SOURCE_UV_GOOD'),8:('V+','AUX2V6')},TI+'tlv1821.pdf',power=(4,8),oc=(1,7))
    ic('TLV1824DR','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
       {1:('OUT2','N19_OUTPUT_OV_GOOD'),2:('OUT1','N19_OUTPUT_UV_GOOD'),3:('V+','AUX2V6'),4:('IN1-','N19_OUT_UV_REF'),5:('IN1+','N19_OUT_UV_SENSE'),6:('IN2-','N19_OUT_OV_SENSE'),7:('IN2+','N19_OUT_OV_REF'),8:('IN3-','N12_OUT_UV_REF'),9:('IN3+','N12_OUT_UV_SENSE'),10:('IN4-','N12_OUT_OV_SENSE'),11:('IN4+','N12_OUT_OV_REF'),12:('V-','AGND'),13:('OUT4','N12_OUTPUT_OV_GOOD'),14:('OUT3','N12_OUTPUT_UV_GOOD')},TI+'tlv1821.pdf',power=(3,12),oc=(1,2,13,14))
    # One actual two-channel host translator, inputs AUX-domain, outputs DIG.
    ic('SN74LVC2T45DCUR','Package_SO:VSSOP-8_2.3x2mm_P0.5mm',
       {1:('VCCA','AUX2V6'),2:('A1','N19_PERMIT'),3:('A2','N12_PERMIT'),4:('GND','AGND'),5:('DIR','AUX2V6'),6:('B2','N12_RUN_HOST5'),7:('B1','N19_RUN_HOST5'),8:('VCCB','DIG5_FORCE')},TI+'sn74lvc2t45.pdf',power=(1,4,8),out=(6,7))
    c(BYPASS,'DIG5_FORCE','AGND')
    for rail,arrays,cf,rf,shunt in [('N19',12,'4.7uF',27,0.330),('N12',9,'3.3uF',39,0.120)]:
        n=lambda x:rail+'_'+x
        vee=n('P03_SRC')
        add('J',rail+' NEW FORCE IN/OUT - connector and harness unselected','Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',[(1,'P03_SRC',vee,'passive'),(2,'E28_SRC',n('E28_SRC'),'passive')],note='Series before existing E28 J1 receiving force pin, not a sense-wire power path. No contact rating accepted.')
        add('J',rail+' E28 BANK GATE/COMMON CLAMP - physical interface unselected','Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',[(1,'BANK_GATE',n('BANK_GATE'),'passive'),(2,'BANK_COMMON',n('BANK_COMMON'),'passive')])
        ic('TMR 1-1215','Converter_DCDC:Converter_DCDC_TRACO_TMR-1-xxxx_Single_THT',
           {1:('-VIN','AGND'),2:('+VIN','GUARDED_12V_FORCE'),4:('+VOUT',n('ISO24')),6:('-VOUT',vee)},'https://www.tracopower.com/sites/default/files/products/datasheets/tmr1_datasheet.pdf',power=(1,2),out=(4,))
        # Output-negative is a passive common, not an independent fake supply.
        parts[-1]['pins'][-1]['kind']='passive'
        c('10uF 25V X7R MODULE INPUT FILTER/EFFECTIVE/INRUSH HOLD','GUARDED_12V_FORCE','AGND')
        c('1uF 50V X7R MODULE OUTPUT FILTER/EFFECTIVE HOLD',n('ISO24'),vee)
        r('392ohm 1% CRCW2010392RFKEF - COMPLETE3% RECEIVING',n('ISO24'),n('FEED_MID'),'Resistor_SMD:R_2010_5025Metric')
        r('392ohm 1% CRCW2010392RFKEF - COMPLETE3% RECEIVING',n('FEED_MID'),n('VIN'),'Resistor_SMD:R_2010_5025Metric')
        r('47k COMPLETE3% RECEIVING',n('VIN'),vee)
        r('10k COMPLETE3% RECEIVING',vee,'AGND',note='Explicit discharge path; negative source current counted.')
        r('47k COMPLETE3% RECEIVING',n('CONTROLLER_ON'),vee)
        r('47k COMPLETE3% RECEIVING',n('RUN_HOST5'),'AGND')
        c('1uF 25V X7R LTC4261 local VIN effective HOLD',n('VIN'),vee)
        c(BYPASS,n('INTVCC'),vee)
        ic('LTC4261IGN#PBF','Package_SO:SSOP-28_3.9x9.9mm_P0.635mm',
           {1:('PGI',vee),2:('ON',n('CONTROLLER_ON')),3:('ALERT',vee),4:('SDAO',None),5:('SDAI',n('INTVCC')),6:('SCL',n('INTVCC')),7:('INTVCC',n('INTVCC')),8:('UVL',n('INTVCC')),9:('UVH',n('INTVCC')),10:('ADIN2',vee),11:('OV',vee),12:('NC',None),13:('VEE',vee),14:('SENSE',n('PASS_SOURCE')),15:('GATE',n('PASS_GATE')),16:('DRAIN',n('DRAIN_SENSE')),17:('NC',None),18:('RAMP',n('RAMP')),19:('SS',n('SS')),20:('TMR',n('TMR')),21:('VIN',n('VIN')),22:('FLTIN',n('INTVCC')),23:('ADIN',vee),24:('ADR0',vee),25:('ADR1',vee),26:('EN',vee),27:('PG',vee),28:('PGIO',None)},ADI+'42612fd.pdf',power=(13,21),out=(7,15),nc=(4,12,17,28))
        next(p for p in parts[-1]['pins'] if p['number']=='7')['kind']='power_out'
        ic('ISO7721FDR','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
           {1:('VCC1',n('INTVCC')),2:('OUTA',n('CONTROLLER_ON')),3:('INB',n('BIAS_RESET_N')),4:('GND1',vee),5:('GND2','AGND'),6:('OUTB',n('BIAS_HOST5')),7:('INA',n('RUN_HOST5')),8:('VCC2','DIG5_FORCE')},TI+'iso7721.pdf',power=(1,4,5,8),out=(2,6))
        # Absolute nativeINTVCC validity; never substitute the hot-swap PG latch.
        ic('TPS389001DSET','Package_SON:WSON-6_1.5x1.5mm_P0.5mm',
           {1:('SENSE',n('BIAS_SENSE')),2:('GND',vee),3:('MR_N',n('INTVCC')),4:('VDD',n('INTVCC')),5:('CT',n('BIAS_CT')),6:('RESET_N',n('BIAS_RESET_N'))},TI+'tps3890.pdf',power=(2,4),oc=(6,))
        r('30.4k COMPLETE0.1% RECEIVING',n('INTVCC'),n('BIAS_SENSE'))
        r('10k COMPLETE0.1% RECEIVING',n('BIAS_SENSE'),vee)
        # A second independent sense input checks VIN before its nativeUVLO;
        # INT-only validation cannot detectVIN collapse whileINTcap stays up.
        ic('TPS389001DSET','Package_SON:WSON-6_1.5x1.5mm_P0.5mm',
           {1:('SENSE',n('VIN_VALID_SENSE')),2:('GND',vee),3:('MR_N',n('INTVCC')),4:('VDD',n('INTVCC')),5:('CT',n('VIN_VALID_CT')),6:('RESET_N',n('BIAS_RESET_N'))},TI+'tps3890.pdf',power=(2,4),oc=(6,))
        r('78.7k COMPLETE0.1% RECEIVING',n('VIN'),n('VIN_VALID_SENSE'))
        r('10k COMPLETE0.1% RECEIVING',n('VIN_VALID_SENSE'),vee)
        c('10nF 50V C0G COMPLETE10% TIMING RECEIVING',n('VIN_VALID_CT'),vee)
        c(BYPASS,n('INTVCC'),vee)
        r('47k COMPLETE3% RECEIVING',n('INTVCC'),n('BIAS_RESET_N'))
        c('10nF 50V C0G COMPLETE10% TIMING RECEIVING',n('BIAS_CT'),vee)
        c(BYPASS,n('INTVCC'),vee)
        r('47k COMPLETE3% RECEIVING',n('BIAS_HOST5'),'AGND')
        r('47k COMPLETE3% RECEIVING',n('BIAS_VALID'),'AGND')
        c(BYPASS,'DIG5_FORCE','AGND')
        c(BYPASS,n('INTVCC'),vee)
        r(f'{shunt}ohm COMPLETE5% SHUNT RECEIVING',vee,n('PASS_SOURCE'),'Resistor_SMD:R_2512_6332Metric')
        add('Q','CSD19536KTT','Package_TO_SOT_SMD:TO-263-2',[(1,'G',n('PASS_GATE'),'input'),(2,'D',n('E28_SRC'),'passive'),(3,'S',n('PASS_SOURCE'),'passive')],TI+'csd19536ktt.pdf','Linear hot-SOA/board cooling/gate-charge not qualified; no typicalRDS extrapolation.')
        r('10ohm COMPLETE3% RECEIVING',n('PASS_GATE'),n('CG_SERIES'))
        r('1M',n('E28_SRC'),n('DRAIN_SENSE'))
        for _ in range(arrays):c('100nF 50V C0G C1210C104J5GACTU - COMPLETE10% RAMP RECEIVING',n('CR_TOP'),n('E28_SRC'),'Capacitor_SMD:C_1210_3225Metric')
        r(f'{rf}ohm COMPLETE3% RECEIVING',n('RAMP'),n('CR_TOP'))
        
        for _ in range(2):
            c('2.2uF 63V PET5% MKS2C042201K00JSSD - COMPLETE10% EFFECTIVE CF RECEIVING',n('RAMP'),vee,'Capacitor_THT:C_Rect_L7.2mm_W7.2mm_P5.00mm_FKS2_FKP2_MKS2_MKP2',note='Current WIMA2026p35 nominalW7.2 H13 L7.2 PCM5; suffixJSSD per p35completion. Body max/hot C/leak/life and lead forming unaccepted. CF total4.4uF directRAMP-toVEE.')
        c('47nF 50V C0G C1206C473J5GACTU',n('CG_SERIES'),vee,note='Actual primary seriesRG+CG branch GATE-toVEE, not series driver-toMOS gate.')
        c('100nF 50V C0G C1210C104J5GACTU',n('SS'),vee,'Capacitor_SMD:C_1210_3225Metric')
        c('47nF 50V C0G C1206C473J5GACTU',n('TMR'),vee)
    # Native5V returned status becomes AUX-domain only through an Ioff
    # translator; do not drive a2.6V AUP/HCS input with5V ISO output.
    ic('SN74LVC2T45DCUR','Package_SO:VSSOP-8_2.3x2mm_P0.5mm',
       {1:('VCCA','DIG5_FORCE'),2:('A1','N19_BIAS_HOST5'),3:('A2','N12_BIAS_HOST5'),4:('GND','AGND'),5:('DIR','DIG5_FORCE'),6:('B2','N12_BIAS_VALID'),7:('B1','N19_BIAS_VALID'),8:('VCCB','AUX2V6')},TI+'sn74lvc2t45.pdf',power=(1,4,8),out=(6,7))
    c(BYPASS,'DIG5_FORCE','AGND')
    # Reuse the actual E28 global fault latch. New OR is on this module;
    # E28 U23.11 old request goes OUT to this input, combined return replaces
    # only U25.10. Do not tie two actively driven outputs together.
    aliases={}
    for rail in ('N19','N12'):
        aliases[rail+'_NOT_FAULT']='NF_NO_FAULT'
        aliases[rail+'_FAULT_CONDITION']=rail+'_FAULT_REQUEST'
    for func,items in gates.items():
        updated=[]
        for a,b,y in items:
            # Completion stays latched until ARM/OFF; a post-complete output
            # fault cannot self-erase by immediately clearing PERMIT.
            if y and y.endswith('_COMPLETE_CLR_N'):
                a=y.split('_')[0]+'_ARM'; b='GLOBAL_VALID'
            updated.append((aliases.get(a,a),aliases.get(b,b),aliases.get(y,y)))
        gates[func]=updated
    for part in parts:
        for pin in part['pins']:
            pin['net']=aliases.get(pin['net'],pin['net'])
    gate('OR','N19_FAULT_REQUEST','N12_FAULT_REQUEST','NF_FAULT_REQUEST')
    gate('OR','E28_NATIVE_FAULT_REQUEST','NF_FAULT_REQUEST','E28_COMBINED_FAULT_REQUEST')
    gate('INV','NF_FAULT_REQUEST',None,'NOT_NF_FAULT_REQUEST')
    gate('AND','E28_NOT_FAULT','NOT_NF_FAULT_REQUEST','NF_NO_FAULT')
    # Ordinary AUP08/32 still publish200ns/V input limits. Use actual HCS
    # Schmitt gates for raw comparator/watchdog edges, not marketing-only
    # assumptions. All HCS inputs are local AUX-domain. External MCU ARM/START
    # first pass through3.3V-tolerant AUP14 double-inversion cells.
    input_pairs=[]
    for rail in ('N19','N12'):
        for kind in ('ARM','START'):
            raw=rail+'_'+kind;fast=raw+'_CONDITIONED'
            for func,items in gates.items():
                gates[func]=[(fast if x==raw else x,fast if y==raw else y,z) for x,y,z in items]
            for part in parts:
                if part['part'].startswith('SN74AUP1G74'):
                    for pin in part['pins']:
                        if pin['net']==raw:pin['net']=fast
            input_pairs.append((raw,fast))
    # AUP output buffers meet the real47k driver pulldown load; HCS20uA VOH
    # is NOT misapplied to a~60uA loaded output. The combined E28 return is
    # likewise buffered instead of assuming an ideal unloaded wire.
    for raw in ('N19_CLAMPS_RELEASE','N12_CLAMPS_RELEASE','E28_COMBINED_FAULT_REQUEST'):
        hcs=raw+'_HCS'
        for func,items in gates.items():
            gates[func]=[(x,y,hcs if z==raw else z) for x,y,z in items]
        input_pairs.append((hcs,raw))
    for raw,fast in input_pairs:
        middle=fast+'_BUFFER_MID'
        ic('SN74AUP2G14DCKR','Package_TO_SOT_SMD:SOT-363_SC-70-6',
           {1:('1A',raw),2:('GND','AGND'),3:('2A',middle),4:('2Y',fast),5:('VCC','AUX2V6'),6:('1Y',middle)},TI+'sn74aup2g14.pdf',power=(2,5),out=(4,6))
    for func,items in gates.items():
        count=6 if func=='INV' else 4
        for i in range(0,len(items),count):
            selected=items[i:i+count]
            selected += [('AGND','AGND',None)]*(count-len(selected))
            pmap={7:('GND','AGND'),14:('VCC','AUX2V6')};outputs=[];unused=[]
            maps=[(1,2),(3,4),(5,6),(9,8),(11,10),(13,12)] if func=='INV' else[(1,2,3),(4,5,6),(9,10,8),(12,13,11)]
            for j,(entry,indices) in enumerate(zip(selected,maps),1):
                if func=='INV':
                    pin,ypin=indices;pmap[pin]=(str(j)+'A',entry[0])
                else:
                    pa,pb,ypin=indices;pmap[pa]=(str(j)+'A',entry[0]);pmap[pb]=(str(j)+'B',entry[1])
                pmap[ypin]=(str(j)+'Y',entry[2]);outputs.append(ypin)
                if entry[2] is None:unused.append(ypin)
            code={'INV':'14','AND':'08','OR':'32'}[func]
            ic('SN74HCS'+code+'PWR','Package_SO:TSSOP-14_4.4x5mm_P0.65mm',pmap,TI+'sn74hcs'+code+'.pdf',power=(7,14),out=tuple(outputs),nc=tuple(unused))
    # One bypass per actual AUX-powered IC, not per packed gate function.
    for part in list(parts):
        if part['ref'].startswith('U') and any(p['kind']=='power_in' and p['net']=='AUX2V6' for p in part['pins']):
            c(BYPASS,'AUX2V6','AGND',note='Actual local front bypass required in PCB implementation.')
    for i,part in enumerate(parts):
        part['x']=round(round((80+(i%7)*145)/2.54)*2.54,4)
        part['y']=round(round((90+(i//7)*100)/2.54)*2.54,4)
    return parts
