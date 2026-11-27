"""Fail-closed anode distribution ownership and native-source validation."""
from collections import Counter

def validate_anodes(topology,nets,pads):
 roots={ref+':25' for ref in topology['receivers']}
 expected={ref+':25':{r['id'] for r in rows} for ref,rows in topology['receivers'].items()}
 assert len(set.union(*expected.values()))==sum(map(len,expected.values())), 'duplicate receiver ownership'
 receivers=set.union(*expected.values());nodes={n['id'] for n in topology['nodes']}
 assert len(nodes)==len(topology['nodes']) and not nodes & receivers
 for root in roots:
  ref,pin=root.split(':');assert nets[ref,pin]=='D__5V_DIG',('wrong native anode root',root)
  assert pads[ref,pin]['net']==nets[ref,pin],('capture/native mismatch',root)
 outgoing={};parents=Counter()
 for edge in topology['edges']:
  source,target=edge['from'],edge['to']
  assert source in roots or source.rsplit(':',1)[0] in nodes and source.rsplit(':',1)[1] in ['OUT_A','OUT_B'],('unknown source',source)
  assert target in receivers or target.rsplit(':',1)[0] in nodes and target.endswith(':IN'),('unknown target',target)
  assert source not in outgoing,('multiple wires in source port',source)
  outgoing[source]=target;parents[target]+=1
 assert set(outgoing)==roots|{n+':'+p for n in nodes for p in ['OUT_A','OUT_B']},'unused or missing source port'
 assert set(parents)==receivers|{n+':IN' for n in nodes},'disconnected or extra receiver/node'
 assert all(count==1 for count in parents.values()),'multiple parents'
 visited=set()
 def walk(target,active):
  if target in receivers:return {target}
  node=target[:-3];assert node not in active,('cycle',node);visited.add(node)
  return walk(outgoing[node+':OUT_A'],active|{node})|walk(outgoing[node+':OUT_B'],active|{node})
 for root in roots:assert walk(outgoing[root],set())==expected[root],('wrong root receiver ownership',root)
 assert visited==nodes,'unreachable splice cycle'
 return dict(roots=len(roots),receivers=len(receivers),splices=len(nodes),segments=len(topology['edges']),all_native_and_captured_root_nets_verified=True,unique_parent_and_port_ownership=True,acyclic_and_fully_reachable=True)
