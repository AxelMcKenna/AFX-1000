"""Source-copper-only F.Cu connectivity path from bypass return tie to LDO EP."""
import json,math,heapq
from pathlib import Path
from shapely.geometry import box
from ..routed.plan import shape,sha
H=Path(__file__).resolve().parent

def run():
 c=json.loads((H/'capture-01/capture.json').read_text());os=[o for o in c['objects'] if o['net']=='PWR_AGND' and 'F.Cu' in o['layers'] and shape(o['layers']['F.Cu']).intersects(box(181,120,198,137))];geo=[shape(o['layers']['F.Cu']) for o in os];by={o.get('ref','')+'.'+o.get('pin',''):i for i,o in enumerate(os)};start,end=by['P_C113.2'],by['P_U102.9'];edges={i:[] for i in range(len(os))}
 for i in range(len(os)):
  for j in range(i):
   if geo[i].distance(geo[j])<=.000001:edges[i].append(j);edges[j].append(i)
 def weight(i):
  o=os[i]
  if o['kind']=='PCB_TRACK':return math.dist(o['position_mm'],o['end_mm'])
  # Pad/via motion is not assigned a precise electrical length by this graph.
  return 0
 q=[(0,start)];dist={start:0};parent={start:None}
 while q:
  d,i=heapq.heappop(q)
  if d!=dist[i]:continue
  if i==end:break
  for j in edges[i]:
   v=d+weight(j)
   if v<dist.get(j,1e100):dist[j]=v;parent[j]=i;heapq.heappush(q,(v,j))
 assert end in dist;path=[];v=end
 while v is not None:path.append(v);v=parent[v]
 path=path[::-1];report={'capture_sha256':sha(H/'capture-01/capture.json'),'script_sha256':sha(Path(__file__)),'source':'P_C113.2','target':'P_U102.9','layer':'F.Cu','objects':[{'uuid':os[i]['uuid'],'kind':os[i]['kind'],'ref':os[i].get('ref'),'pin':os[i].get('pin'),'position_mm':os[i]['position_mm'],'end_mm':os[i].get('end_mm')} for i in path],'sum_existing_track_centerline_lengths_mm':dist[end],'interpretation':'Proves a same-face geometric contact chain only; sum excludes distances traversed inside pads/vias and is not a loop-inductance bound.','qualified':False};(H/'return-path.json').write_text(json.dumps(report,indent=2)+'\n');print('objects',len(path),'track length',dist[end])
if __name__=='__main__':run()
