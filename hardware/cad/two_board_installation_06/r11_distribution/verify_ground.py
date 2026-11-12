"""Validate control-return ownership against independent sealed switch contracts."""
from pathlib import Path
from collections import Counter,defaultdict
import copy,json,hashlib,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent

def audit(g,c):
 nodes={n['id'] for n in g['nodes']};assert len(nodes)==26
 expected={}
 for r in c['front_inputs']:
  if r['receiver_kind']=='B3F-1000 momentary':expected['button_'+r['id']+':3']=r['signal']['reference']
 for s in c['selectors']:
  w=[x for x in s['wires'] if x['main']['net']=='LINK_AGND'];assert len(w)==1
  expected[s['id']+':'+w[0]['pad']]=w[0]['main']['reference']
 assert len(expected)==31
 counts=Counter(p for e in g['edges'] for p in [e['from'],e['to']]);assert set(counts.values())=={1}
 outgoing=defaultdict(list);incoming=Counter()
 for e in g['edges']:
  f,t=e['from'],e['to'];a=f.rsplit(':',1)[0];b=t.rsplit(':',1)[0]
  if a in nodes:assert f.rsplit(':',1)[1] in ['OUT_A','OUT_B']
  else:a=f
  if b in nodes:assert t.rsplit(':',1)[1]=='IN'
  else:b=t
  outgoing[a].append(b);incoming[b]+=1
 for n in nodes:assert incoming[n]==1 and len(outgoing[n])==2
 assert set(incoming)-nodes==set(expected)
 visited=set();actual={}
 def visit(n,root,path):
  assert n not in path,'cycle'
  visited.add(n)
  if n in expected:
   assert incoming[n]==1 and not outgoing[n];actual[n]=root;return
  for child in outgoing[n]:visit(child,root,path+(n,))
 roots=['D_J2001:15','D_J2001:16','D_J2002:15','D_J2002:16','D_J2003:1']
 for root in roots:assert not incoming[root] and len(outgoing[root])==1;visit(root,root,())
 assert visited==nodes|set(expected)|set(roots)
 assert {r:root.split(':')[0]for r,root in actual.items()}==expected
 return actual

g=json.loads((HERE/'ground-topology.json').read_text());c=json.loads((HERE/'reference/panel-contract.json').read_text());actual=audit(g,c)
r=ET.parse(HERE/'reference/signal-netlist.xml');ground={(p.get('ref'),p.get('pin'))for n in r.findall('./nets/net')if n.get('name')=='LINK_AGND'for p in n.findall('node')}
assert all(tuple(v.split(':'))in ground for v in actual.values())
bad=copy.deepcopy(g);root_edges=[e for e in bad['edges']if e['from'].startswith('D_J')];root_edges[0]['from'],root_edges[-1]['from']=root_edges[-1]['from'],root_edges[0]['from']
try:audit(bad,c)
except AssertionError:mutation='rejected'
else:raise AssertionError('Swapped source accepted')
files=[Path(__file__),HERE/'ground-topology.json',HERE/'reference/panel-contract.json',HERE/'reference/signal-netlist.xml']
report={'source_sha256':{str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files},'endpoint_to_ground_root':actual,'root_population':dict(Counter(actual.values())),'swapped_root_mutation':mutation,'complete_electrical_graph':True,'physically_routed':False,'fabrication_released':False}
(HERE/'ground-verification.json').write_text(json.dumps(report,indent=2)+'\n');print('31ground receivers verified; swapped root mutation rejected')
