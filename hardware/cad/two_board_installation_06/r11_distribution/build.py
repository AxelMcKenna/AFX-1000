"""Explicit LED anode branch graph; no implicit multiple wires per contact."""
from pathlib import Path
import csv,json,hashlib,math
HERE=Path(__file__).resolve().parent
SRC=HERE/'reference'
files=['display-wiring.csv','led_follow_on/wiring.csv','ring_follow_on/wiring.csv','button_follow_on/wiring.csv']
groups={};source_hash={}
for f in files:
 p=SRC/f;source_hash[f]=hashlib.sha256(p.read_bytes()).hexdigest()
 for r in csv.DictReader(p.open()):
  if r['net']!='D__5V_DIG':continue
  header=r.get('main_connector') or r['connector'];assert r['main_pin']=='25'
  if 'display' in r: name=r['display'];pad=r['manufacturer_pin']
  elif 'board' in r:name=r['board'];pad=r['pad']+'.'+r['pin']
  elif 'ring_pad' in r:name='touch_ring';pad=r['ring_pad']+'.'+r['pin']
  else:name='button_'+r['button'];pad=r['pad']+'.'+r['pin']
  groups.setdefault(header,[]).append({'id':name+':'+pad,'receiver':name,'terminal':pad,'source_file':f})
nodes=[];edges=[];counts={}
for header,leaves in sorted(groups.items()):
 counter=[0]
 def tree(ls,up):
  if len(ls)==1:edges.append({'from':up,'to':ls[0]['id'],'wire':'Alpha5853 26AWG7/34'});return
  counter[0]+=1;name='ANODE_'+header+'_'+str(counter[0]).zfill(2)
  nodes.append({'id':name,'net':'D__5V_DIG','hardware':'TE34130','ports':['IN','OUT_A','OUT_B'],'wire_count':3,'insulation':'TE505872P034 VERSAFIT-3/16-0-0.9375IN; receiving/coverage verification required'})
  edges.append({'from':up,'to':name+':IN','wire':'Alpha5853 26AWG7/34'})
  mid=(len(ls)+1)//2;tree(ls[:mid],name+':OUT_A');tree(ls[mid:],name+':OUT_B')
 tree(sorted(leaves,key=lambda r:r['id']),header+':25');counts[header]={'receivers':len(leaves),'splices':counter[0]}
assert len(nodes)==34 and sum(len(g)for g in groups.values())==38 and len(edges)==72
cma_per=7*(5*92**((36-34)/39))**2
assert 509 < 3*cma_per < 3260
out={'scope':'Explicit electrical branch topology candidate, not physically routed/insulated or fabrication released. Header25 receives one wire only. Every splice contains three same-gauge conductors, each port one wire.','wire':'Alpha5853 silver-plated stranded copper26AWG7/34','sources':source_hash,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'counts':counts,'splice_cma':{'method':'7strands×AWG34 diameter squared in circular mils; three conductors per splice','per_conductor':cma_per,'combined_three':3*cma_per,'manufacturer_combined_range':[509,3260]},'nodes':nodes,'edges':edges,'receivers':groups,'fabrication_released':False}
(HERE/'anode-topology.json').write_text(json.dumps(out,indent=2)+'\n')
print('38 receivers /34explicit3wire splices /72single-conductor segments')
