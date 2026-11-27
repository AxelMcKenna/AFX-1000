"""Independent circuit contracts for the twelve unchanged passive PCB layouts."""
from pathlib import Path
R=Path(__file__).resolve().parent;CONTROLS=R.parent;REPO=CONTROLS.parents[2]
LED_SOURCE='https://www.kingbright.com/attachments/file/psearch/000/00/00/KPT-1608CGCK%28Ver.29B%29.pdf'
RGB_SOURCE='https://www.kingbrightusa.com/images/catalog/SPEC/APTF1616LSEEZGKQBKC.pdf'
SW_SOURCE='https://www.littelfuse.com/assetdocs/littelfuse-c-k-slide-js-series-datasheet?assetguid=aba42b08-0d2c-423b-813d-a2faa5a3bb14'
DESIGNS={'settings':('settings.kicad_pcb','TBH04'),'release':('release.kicad_pcb','TBH04'),'meter_input':('led_follow_on/meter_input.kicad_pcb','TBH05'),'meter_output':('led_follow_on/meter_output.kicad_pcb','TBH05'),'bank':('led_follow_on/bank.kicad_pcb','TBH05'),'ring':('ring_follow_on/ring.kicad_pcb','TBH06')}
DESIGNS.update({n:(f'button_follow_on/{n}.kicad_pcb','TBH07') for n in ['vertical','horizontal','scene','pad','pad1','vertical_top']})
def contract(name):
 path,lib=DESIGNS[name];cs=[];ports={}
 def add(ref,part,fp,pins,source='',note=''):
  cs.append(dict(ref=ref,part=part,footprint=f'{lib}:{fp}',source=source,note=note,pins=[dict(number=str(i),name=label,kind='passive',side='L' if j%2==0 else 'R',net=net) for j,(i,label,net) in enumerate(pins)]))
 def wire(ref,net):
  fp='WirePad' if lib in ['TBH04','TBH05'] else 'Wire'
  # Values describe physical pads exactly as the existing PCB files.
  value=net
  if name=='bank':fp='BankWirePad'
  add(ref,value,fp,[(1,'WIRE',net)],note='Direct-solder external wire pad; mating/routing contract separate');ports[ref]=net
 def green(ref,k,a):add(ref,'KPT-1608CGCK','KPT1608',[(1,'K',k),(2,'A',a)],LED_SOURCE)
 if name in ['settings','release']:
  n=6 if name=='settings' else 8;part='JS202011CQN' if n==6 else 'JS203011SCQN'
  add('SW1',part,part,[(i,f'TERMINAL_{i}',f'SW_PIN_{i}') for i in range(1,n+1)],SW_SOURCE,'Contact function is a separate manufacturer/firmware-bound state contract')
  for i in range(1,n+1):wire(f'W{i}',f'SW_PIN_{i}')
 elif name.startswith('meter_'):
  for i in range(20):green(f'D{i+1}',f'{name}_{i}','LED_ANODE_5V');wire(f'W{i+1}',f'{name}_{i}')
  wire('WA','LED_ANODE_5V')
 elif name=='bank':green('D1','BANK_CATHODE','LED_ANODE_5V');wire('W1','BANK_CATHODE');wire('W2','LED_ANODE_5V')
 elif name=='ring':
  for i in range(8):
   add(f'D{i+1}','APTF1616LSEEZGKQBKC','RGB1616',[(1,'A','ANODE_5V'),(2,'R_K',f'BRANCH_{i}_0'),(3,'G_K',f'BRANCH_{i}_1'),(4,'B_K',f'BRANCH_{i}_2')],RGB_SOURCE)
   for j,color in enumerate(['RED_93','GREEN_94','BLUE_95']):
    branch=f'BRANCH_{i}_{j}';bus='RING_'+color;pins=[(1,'1',branch if j==0 else bus),(2,'2',bus if j==0 else branch)]
    add(f'R{i*3+j+1}','RC0603FR-071KP','R0603',pins,'https://www.yageogroup.com/component-documentation/download/specsheet/RC0603FR-071KP','1000ohm1%; individual RGB current-sharing branch')
  for i,net in enumerate(['ANODE_5V','RING_RED_93','RING_GREEN_94','RING_BLUE_95'],1):wire(f'W{i}',net)
 else:green('D1','LED_K','LED_A');wire('W1','LED_K');wire('W2','LED_A')
 for i in range(1,4 if name=='ring' else 3):add(f'H{i}','Existing holder mount' if lib=='TBH07' else 'M2','M2',[],note='Mechanical NPTH mount; no electrical pin')
 return dict(name=name,pcb=path,components=cs,ports=ports,thickness=.6 if lib=='TBH07' else 1.6)
def groups(components):
 nets={}
 for c in components:
  for p in c['pins']:
   if p['net'] is not None:nets.setdefault(p['net'],[]).append(c['ref']+'.'+p['number'])
 return {k:sorted(v) for k,v in sorted(nets.items())}
