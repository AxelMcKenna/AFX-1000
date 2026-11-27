"""Source-bound review inventory; deliberately not a fabrication release."""
import csv,json,hashlib,collections,trimesh
from pathlib import Path
R=Path(__file__).resolve().parent
rows=[]
for f,key in [('display-wiring.csv','logical_channel'),('led_follow_on/wiring.csv','channel'),('ring_follow_on/wiring.csv','logical_channel'),('button_follow_on/wiring.csv','channel')]:
 for row in csv.DictReader((R/f).open()):
  if row[key]!='':rows.append(dict(channel=int(row[key]),source=f))
assert sorted(r['channel'] for r in rows)==list(range(96))
(R/'lighting-coverage.json').write_text(json.dumps(dict(channels=96,unique=True,rows=sorted(rows,key=lambda r:r['channel']),source_sha256={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in sorted({r['source'] for r in rows})}),indent=2)+'\n')
prints=[('generated-r7/tray/tray.stl',1),('generated-r7/bezel/bezel.stl',1),('selectors-r6/settings_bracket/settings_bracket.stl',2),('led_follow_on/meters-r4/meter_frame/meter_frame.stl',1),('led_follow_on/meters-r4/meter_frame_lower/meter_frame_lower.stl',1),('led_follow_on/banks-r4/bank_frame/bank_frame.stl',4),('ring_follow_on/native-r6/ring_frame/ring_frame.stl',1),('ring_follow_on/native-r6/ring_lens/ring_lens.stl',1)]+[(f'pot_follow_on/native-r3/knob{d}/knob{d}.stl',n) for d,n in [(16,3),(17,3),(29,3),(32,1)]]
prints +=[(f'ring_follow_on/native-r6/{n}/{n}.stl',1) for n in ['ring_lid','ring_lid_left','ring_lid_right']]
prints +=[(f'connected-guide-r1/{n}/{n}.stl',1) for n in ['buttons_guide_final','buttons_guide_left_final','buttons_guide_right_final']]
parts=[]
for path,qty in prints:
 p=R/path;m=trimesh.load_mesh(p);components=len(m.split());assert components==1,(path,components)
 parts.append(dict(path=path,quantity=qty,connected_components=components,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),choice='full or split alternative' if 'lid' in Path(path).stem or 'guide' in Path(path).stem else 'required'))
boards=[('settings.kicad_pcb',1,1.6),('release.kicad_pcb',1,1.6),('led_follow_on/meter_input.kicad_pcb',1,1.6),('led_follow_on/meter_output.kicad_pcb',1,1.6),('led_follow_on/bank.kicad_pcb',4,1.6),('ring_follow_on/ring.kicad_pcb',1,1.6)]
c=json.loads((R/'button_follow_on/contract.json').read_text());counts=collections.Counter(i['design'] for i in c['instances']);boards +=[(f'button_follow_on/{name}.kicad_pcb',qty,.6) for name,qty in sorted(counts.items())]
assert sum(q for _,q,_ in boards)==34
report=dict(scope='Active modeled control receiving inventory; no fabrication release',fabrication_released=False,physical_passive_control_pcbs=34,distinct_control_pcb_designs=len(boards),main_pcbs_not_included=2,light_sink_channels=96,prints=parts,boards=[dict(path=f,quantity=q,thickness_mm=t,sha256=hashlib.sha256((R/f).read_bytes()).hexdigest()) for f,q,t in boards],superseded_guides=['ring_follow_on/native-r6/ring_guide*','button_follow_on/native-r5/buttons_guide*'],current_guide_api='connected_guide.scad:tbh07_connected_guide_variant()',purchased=dict(KPT_1608CGCK=69,APTF1616LSEEZGKQBKC=8,RC0603FR_071KP=24,SA36_11YWA=3,JS202011CQN=1,JS203011SCQN=1),notes=['Choose either full or split lid/guide, not both.','Use25 retained translucent key shapes; those meshes and remaining baseline hardware are not duplicated here.','All34 boards are additional passive control PCBs, not the two functional main PCBs; sensor PCB is separately owned.','Pot25mm no-detent configuration is available-to-order; exact center-detent part requires supplier quote/confirmation.'])
(R/'active-controls.json').write_text(json.dumps(report,indent=2)+'\n');print('96 unique lighting channels;34 physical passive boards;18 active print variants each1 component')
