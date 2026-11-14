"""Reconcile TBP66 AUX distribution, including the reviewed TBP51 feedback revision.

Preserves the historical inventory generator and refuses unreviewed part drift.
"""
import argparse,json
from collections import Counter
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.assess_two_board_aux_load import circuit,numeric,AUX,GND


def run():
 ap=argparse.ArgumentParser()
 for k in ['source','capture','output']:ap.add_argument('--'+k,required=True)
 args=ap.parse_args();assert all(all(c.isalnum() or c in '-_' for c in n) for n in [args.source,args.capture,args.output])
 native=STAGING/args.source;cp=STAGING/args.capture/'capture.json';out=STAGING/args.output;assert not out.exists()
 c=json.loads(cp.read_text());review=json.loads((native/'review.json').read_text())
 assert c['native_uncapped_opens']==review['opens']
 for n,h in c['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
 for n,h in review['artifact_sha256'].items():assert sha(native/n)==h,n
 baseline=STAGING/'two-board-power-aux-ground-native-02/netlist.xml'
 parts,nets,pins=circuit(native/'netlist.xml');old,on,op=circuit(baseline)
 pads={(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD' and o.get('pin')}
 source_group=pads['P_U102','1']['group'];main=pads['P_C103','2']['group']
 terminals=[];caps=[]
 for n in nets[AUX]:
  ref,pin=n['ref'],n['pin'];o=pads[ref,pin];assert o['net']==AUX
  category={'power_in':'IC_supply','power_out':'source','input':'tied_IC_input'}.get(n['pintype'])
  if category is None:category={'C':'capacitor','R':'resistor','J':'connector','D':'diode'}[ref.split('_')[1][0]]
  terminals.append(dict(**n,value=parts[ref].findtext('value'),category=category,native_group=o['group'],source_connected=o['group']==source_group,position_mm=o['position_mm']))
  if category=='capacitor':
   peerpin,peernet=next((p,v) for p,v in pins[ref].items() if p!=pin);assert peernet==GND
   caps.append(dict(ref=ref,value=parts[ref].findtext('value'),nominal_F=numeric(parts[ref].findtext('value')),source_connected=o['group']==source_group,ground_to_main=pads[ref,peerpin]['group']==main))
 counts=dict(Counter(x['category'] for x in terminals));assert counts['IC_supply']==81 and len(terminals)==230 and len(caps)==87
 added={(n['ref'],n['pin']) for n in nets[AUX]}-{(n['ref'],n['pin']) for n in on[AUX]}
 removed={(n['ref'],n['pin']) for n in on[AUX]}-{(n['ref'],n['pin']) for n in nets[AUX]}
 assert added=={('P_C114','1')} and not removed
 changes=[]
 for ref in {x['ref'] for x in terminals}&old.keys():
  for field in ['value','footprint','datasheet']:
   a,b=old[ref].findtext(field),parts[ref].findtext(field)
   if a!=b:changes.append(dict(ref=ref,field=field,before=a,after=b))
 feedback=STAGING/'two-board-power-aux-feedback-native-01/netlist.xml'
 reviewed,_,_=circuit(feedback)
 expected_changes={('E_U42','datasheet'),('P_R108','value'),('P_R108','footprint'),('P_R108','datasheet')}
 assert {(x['ref'],x['field']) for x in changes}==expected_changes
 for row in changes:
  assert row['after']==reviewed[row['ref']].findtext(row['field']),row
 feedback_audit=STAGING/'two-board-power-aux-feedback-native-01/aux-feedback-review.json'
 audit=json.loads(feedback_audit.read_text())
 for key in ['source_sha256','artifact_sha256']:
  for name,digest in audit.get(key,{}).items():
   path=Path(name)
   if not path.is_absolute():path=(REPO if name.startswith(('hardware/','tests/')) else feedback_audit.parent)/path
   assert sha(path)==digest,name
 nominal=sum(x['nominal_F'] for x in caps);assert abs(nominal-28.5e-6)<1e-12
 required=[
  'Reconcile IC and resistor/output loads by startup/run/fault state, including input-transition current and overlap; avoid double-counting NF interface loads.',
  'Resolve exact capacitor tolerance, DC-bias/temperature/aging derating and actual AUX startup ramp with simultaneous load.',
  'Establish an applicable regulator current bound and installed thermal path before accepting the LDO and source/distribution routing.',
  'Complete missing source, ground and load connections, then verify startup/fault, current-sharing, noise and thermal behavior.'
 ]
 paths=[Path(__file__),feedback,feedback_audit,cp,native/'netlist.xml',native/'review.json',baseline,STAGING/'two-board-aux-load-review-01/review.json',REPO/'hardware/fabrication/assess_two_board_aux_load.py']
 result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},native_board_opens=review['opens'],terminal_counts=counts,terminals=terminals,capacitors=caps,nominal_capacitance_F=nominal,added_AUX_terminals_since_load_review=sorted(added),removed_AUX_terminals_since_load_review=sorted(removed),metadata_changes_since_load_review=changes,
  source_connected_IC_supply_pins=sum(x['category']=='IC_supply' and x['source_connected'] for x in terminals),unconnected_IC_supply_pins=sum(x['category']=='IC_supply' and not x['source_connected'] for x in terminals),
  source_connected_capacitors=sum(x['source_connected'] for x in caps),capacitors_with_main_ground_return=sum(x['ground_to_main'] for x in caps),
  nominal_charge_screens=[dict(ramp_s=t,voltage_V=2.7,nominal_capacitor_average_A=nominal*2.7/t) for t in [.001,.01]],
  charge_screen_scope='Nominal total capacitor charge divided by an assumed ramp duration, excluding simultaneous circuit load and derating; not a startup prediction.',required_design_work=required,
  prior_load_review_limits_resolved=False,actual_current_bound_established=False,installed_thermal_path_qualified=False,source_distribution_complete=False,fabrication_released=False)
 out.mkdir();(out/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['terminal_counts','nominal_capacitance_F','source_connected_IC_supply_pins','unconnected_IC_supply_pins','source_connected_capacitors','capacitors_with_main_ground_return']}))


if __name__=='__main__':run()
