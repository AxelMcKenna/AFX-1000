"""Extract full bus inventory and calculate conditional limits; never infer measured C."""
from pathlib import Path
import hashlib,json,math
from collections import defaultdict
from hardware.electronics.common.sexpr import read_sexpr,children,first
R=Path(__file__).resolve().parent;REPO=R.parents[3]
PATHS={'signal':'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb','power':'hardware/fabrication/staging/two-board-power-western-logic-returns-native-02/power_protection.kicad_pcb','sensor':'hardware/cad/two_board_sensor_05/pcb/native-r3/sensor.kicad_pcb'}
def extract(p,bus):
 t=read_sexpr(p.read_text());names={v[1]:v[-1]for v in children(t,'net')}
 def net(v):
  n=children(v,'net');return names.get(n[0][1],n[0][-1])if n else ''
 parts=[];segments=[];vias=[]
 for fp in children(t,'footprint'):
  props={v[1]:v[2]for v in children(fp,'property')};props.update({v[1].capitalize():v[2]for v in children(fp,'fp_text')})
  pads={v[1]:net(v)for v in children(fp,'pad')}
  if any(v in bus for v in pads.values()):parts.append({'ref':props.get('Reference'),'value':props.get('Value'),'at':first(fp,'at')[1:],'pads':pads})
 for seg in children(t,'segment'):
  n=net(seg)
  if n in bus:segments.append({'net':n,'layer':first(seg,'layer')[1],'width_mm':float(first(seg,'width')[1]),'length_mm':math.dist([float(x)for x in first(seg,'start')[1:]],[float(x)for x in first(seg,'end')[1:]])})
 for v in children(t,'via'):
  if net(v)in bus:vias.append({'net':net(v),'diameter_mm':float(first(v,'size')[1]),'drill_mm':float(first(v,'drill')[1])})
 assert not any(net(v)in bus for v in children(t,'arc')),'Add arc length extraction before audit'
 return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'parts':parts,'segments':segments,'vias':vias,'total_track_mm':{n:sum(v['length_mm']for v in segments if v['net']==n)for n in bus},'via_count':{n:sum(v['net']==n for v in vias)for n in bus},'dielectric_stackup_specified':bool(children(first(t,'setup'),'stackup'))}
b={k:extract(REPO/p,['SCL','SDA']if k=='sensor'else['LINK_SCL','LINK_SDA'])for k,p in PATHS.items()}
parts={v['ref']:v for v in b['signal']['parts']}
for ref,net in [('A_R201','LINK_SCL'),('A_R202','LINK_SDA')]:assert parts[ref]['value']=='2k 1%' and set(parts[ref]['pads'].values())=={net,'LINK_V3V3_IO'}
assert not b['power']['parts']
addresses={}
for ref in ['D_U2001','D_U2002','D_U2003']:
 p=parts[ref]['pads'];assert p['12']=='LINK_SCL' and p['13']=='LINK_SDA';addresses[ref]=hex(0x20+sum((1<<i)if p[str(15+i)]=='LINK_V3V3_IO'else 0 for i in range(3)))
assert len(set(addresses.values()))==3
trill_path=R/'sources/trill-craft-c3.kicad_pcb'
trill=extract(trill_path,['/I2C_SCL','/I2C_SDA','Net-(U1-(PR{slash}SCL)P1[1])','Net-(U1-(PR{slash}SDA)P1[0])'])
assert trill['sha256']==json.loads((R/'trill-source.json').read_text())['sha256']
assert not any(v['ref'].startswith('R') and 'VCC'in v['pads'].values() for v in trill['parts'])
assert {v['ref']:v['value']for v in trill['parts']if v['ref'].startswith('R')}=={'R1':'100','R2':'100'}
# Requirements, not measured values: complete per-line C allocation sums150pF.
alloc={'signal_board_including_Seed_and_three_MCP23017_pF':80,'missing_codec_and_future_local_routes_pF':10,'sensor_board_including_AS5600_pF':15,'Trill_C3_board_pF':15,'all_external_wiring_and_mates_pF':30}
rmax=2020;rmin=1980;vmax=3.465
limits={'pullup_ohm_range':[rmin,rmax],'supply_design_range_V':[3.135,vmax],'supply_range_is_acceptance_requirement_not_measurement':True,'400kHz_C_ceiling_pF':300e-9/(.8473*rmax)*1e12,'100kHz_C_RC_ceiling_pF':1000e-9/(.8473*rmax)*1e12,'100kHz_C_protocol_ceiling_pF':400,'design_allocation_pF':alloc,'design_total_pF':sum(alloc.values()),'rise_30_70_ns_at_allocation':.8473*rmax*sum(alloc.values())*.001,'max_pullup_current_to_zero_mA':vmax/rmin*1000,'Trill_100ohm_series_drop_upper_bound_V':vmax/rmin*100,'C_is_measured':False,'400kHz_electrical_qualification_pass':False}
# Current shared BoardIO and full_engine schedule; successful transactions only.
clocks={'MCP_buttons_two_plus_two_plus_one_byte_reads':126,'AS5600_status_plus_angle_three_bytes':54,'external_rear_one_byte_read':36,'Trill_eight_channels_sixteen_bytes':171,'external_codec_four_status_plus_up_to_two_audit_registers':216}
schedule={'source':'hardware/firmware/full_engine/main.cpp + shared BoardIO.h/ControlExpanders.h/Es9292.h','control_target_Hz':1000,'touch_target_Hz':250,'external_codec_target_Hz':250,'onboard_mean_utilization_400kHz':(180*1000+171*250)/400000,'external_mean_utilization_400kHz':(216*1000+(171+216)*250)/400000,'external_mean_utilization_100kHz':(216*1000+(171+216)*250)/100000,'external_max_successful_batch_clocks':603,'external_max_batch_wire_ms_400kHz':603/400,'external_max_batch_wire_ms_100kHz':603/100,'excludes':'start/stop/bus-free/software/clock-stretch/retries, SPI LEDs and sensor conversion time; loop gates1ms but is not a hard realtime1kHz guarantee','clock_counts':clocks}
firm_files=['hardware/firmware/BoardIO.h','hardware/firmware/ControlExpanders.h','hardware/firmware/Es9292.h','hardware/firmware/full_engine/main.cpp','hardware/firmware/full_engine/Makefile','hardware/firmware/full_engine/README.md','hardware/firmware/Calibration.h']
txt=(REPO/firm_files[0]).read_text();assert 'I2C_400KHZ'in txt and 'read(0x36, 0x0b, data, 3)'in txt and 'read(0x30, 4, bytes, 16)'in txt
import xml.etree.ElementTree as ET
netfile=REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/netlist.xml';nets=ET.parse(netfile)
netlist={n.attrib['name']:[x.attrib for x in n.findall('node')]for n in nets.findall('./nets/net')if n.attrib['name']in ['LINK_SCL','LINK_SDA']}
assert all(any(v['ref']=='A_U201' for v in nodes)for nodes in netlist.values())
drcfile=REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/drc.json';drc=json.loads(drcfile.read_text());opens=[v for v in drc['unconnected_items']if any(n in json.dumps(v)for n in ['LINK_SCL','LINK_SDA'])];assert len(opens)==4
report={'status':'Source-bound bus review and proposed acceptance limits; current bus has4native opens and missing codec footprint; not an electrical qualification pass','files':PATHS,'boards':b,'trill_manufacturer_reference':trill,'native_netlist':netlist,'native_bus_opens':opens,'addresses':{**addresses,'AS5600':'0x36','Trill_Craft_default':'0x30','ES9292_external_profile':'0x18'},'limits':limits,'timing':schedule,'source_sha256':{f:hashlib.sha256((REPO/f).read_bytes()).hexdigest()for f in [*firm_files,str(netfile.relative_to(REPO)),str(drcfile.relative_to(REPO))]},'firmware_scope':'Current full_engine uses shared BoardIO with all intended endpoints; legacy firmware/daisy is not used for this audit','audit_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(R/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'native_bus_opens':len(opens),'track_mm':b['signal']['total_track_mm'],'limits':limits,'timing':schedule},indent=2))
